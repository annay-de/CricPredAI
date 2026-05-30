"""
CricPredAI V3.0 training pipeline.
Run locally with IPL.csv present only when you want to retrain artefacts
The deployed Streamlit app loads artefacts from artifacts/ and does not need IPL.csv
"""
from __future__ import annotations
import json
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from model_wrappers import XGBOutcomeWrapper
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import log_loss, accuracy_score, f1_score, balanced_accuracy_score
from sklearn.linear_model import SGDClassifier, LogisticRegression
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    HAS_XGB = False

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "IPL.csv"
ART = ROOT / "artifacts"
MODELS = ART / "models"
ART.mkdir(exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)

OUTCOMES = ["0", "1", "2", "3", "4", "6", "W", "WD", "NB", "LB", "B"]
NUM_FEATURES = ["innings", "over", "legal_ball", "team_runs", "team_wicket", "batter_runs", "batter_balls"]
CAT_FEATURES = ["phase", "batting_team", "bowling_team", "batter", "bowler", "venue", "toss_decision"]
FEATURES = NUM_FEATURES + CAT_FEATURES

def phase_from_over(over: float) -> str:
    if over < 6:
        return "powerplay"
    if over < 16:
        return "middle"
    return "death"


def outcome_from_row(r: pd.Series) -> str:
    extra_type = str(r.get("extra_type", "") or "").lower()
    valid = int(r.get("valid_ball", 1) or 0)
    wicket = pd.notna(r.get("player_out")) or pd.notna(r.get("wicket_kind"))
    if valid == 0:
        if "wide" in extra_type:
            return "WD"
        if "no" in extra_type:
            return "NB"
    if "legbye" in extra_type:
        return "LB"
    if extra_type == "byes" or extra_type == "bye":
        return "B"
    if wicket:
        return "W"
    rb = int(r.get("runs_batter", 0) or 0)
    if rb >= 6:
        return "6"
    if rb == 5:
        return "4"
    if rb in [0, 1, 2, 3, 4]:
        return str(rb)
    return "0"


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["phase"] = df["over"].fillna(0).astype(float).map(phase_from_over)
    df["legal_ball"] = df["ball"].fillna(1).astype(int).clip(1, 6)
    for col in ["team_runs", "team_wicket", "batter_runs", "batter_balls"]:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)
    df["outcome"] = df.apply(outcome_from_row, axis=1)
    for col in CAT_FEATURES:
        if col not in df:
            df[col] = "Unknown"
        df[col] = df[col].fillna("Unknown").astype(str)
    return df.dropna(subset=["date", "batter", "bowler"])


def make_preprocessor():
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), NUM_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=100), CAT_FEATURES),
    ])


def evaluate(name, model, X_test, y_test):
    proba = model.predict_proba(X_test)
    classes = list(model.classes_)
    aligned = np.zeros((len(X_test), len(OUTCOMES))) + 1e-9
    for j, c in enumerate(classes):
        if c in OUTCOMES:
            aligned[:, OUTCOMES.index(c)] = proba[:, j]
    aligned = aligned / aligned.sum(axis=1, keepdims=True)
    pred = np.array(OUTCOMES)[aligned.argmax(axis=1)]
    return {
        "model": name,
        "log_loss": float(log_loss(y_test, aligned, labels=OUTCOMES)),
        "accuracy": float(accuracy_score(y_test, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, pred)),
        "macro_f1": float(f1_score(y_test, pred, average="macro", zero_division=0)),
    }


def empirical_distributions(df: pd.DataFrame) -> dict:
    def dist(group):
        counts = group["outcome"].value_counts().reindex(OUTCOMES, fill_value=0).astype(float) + 1.0
        p = counts / counts.sum()
        return p.to_dict()
    global_prior = dist(df)
    phase = {k: dist(v) for k, v in df.groupby("phase")}
    batter_phase = {f"{b}||{ph}": dist(v) for (b, ph), v in df.groupby(["batter", "phase"]) if len(v) >= 25}
    bowler_phase = {f"{b}||{ph}": dist(v) for (b, ph), v in df.groupby(["bowler", "phase"]) if len(v) >= 25}
    extra_runs = {}
    for out in ["WD", "NB", "LB", "B"]:
        g = df[df["outcome"].eq(out)]
        vals = g["runs_total"].fillna(1).astype(int).clip(0, 7).tolist() if len(g) else [1]
        extra_runs[out] = vals[:5000]
    return {"outcomes": OUTCOMES, "global": global_prior, "phase": phase,
            "batter_phase": batter_phase, "bowler_phase": bowler_phase, "extra_runs": extra_runs}


def player_metadata(df: pd.DataFrame) -> dict:
    players = sorted(set(df["batter"].dropna().astype(str)) | set(df["bowler"].dropna().astype(str)))
    bat = df.groupby("batter").agg(bat_balls=("valid_ball", "sum"), bat_runs=("runs_batter", "sum"), dismissals=("player_out", lambda s: s.notna().sum())).reset_index()
    bowl = df.groupby("bowler").agg(bowl_balls=("valid_ball", "sum"), bowl_runs=("runs_bowler", "sum"), bowl_wkts=("bowler_wicket", "sum")).reset_index()
    stats = pd.merge(bat, bowl, left_on="batter", right_on="bowler", how="outer")
    stats["player"] = stats["batter"].fillna(stats["bowler"])
    stats = stats.fillna(0)
    roles = {}
    for _, r in stats.iterrows():
        player = str(r["player"])
        bat_balls = float(r.get("bat_balls", 0))
        bowl_balls = float(r.get("bowl_balls", 0))
        if bowl_balls >= 120 and bat_balls >= 120:
            role = "all-rounder"
        elif bowl_balls >= max(60, bat_balls * 0.7):
            role = "bowler"
        else:
            role = "batter"
        roles[player] = {
            "role": role,
            "batting_score": float((r.get("bat_runs",0) / max(1, bat_balls)) + 0.15*np.log1p(bat_balls)),
            "bowling_score": float((r.get("bowl_wkts",0) / max(1, bowl_balls))*25 - (r.get("bowl_runs",0)/max(1,bowl_balls))*0.2 + 0.1*np.log1p(bowl_balls)),
            "bat_balls": int(bat_balls), "bowl_balls": int(bowl_balls)
        }
    venues = sorted(df["venue"].dropna().astype(str).unique().tolist())
    return {"players": players, "roles": roles, "venues": venues}


def baseline_eval(test, prior):
    p = np.array([prior[o] for o in OUTCOMES], dtype=float)
    P = np.repeat((p/p.sum()).reshape(1,-1), len(test), axis=0)
    pred = np.array(OUTCOMES)[P.argmax(axis=1)]
    y = test["outcome"].values
    return {"model":"baseline_prior", "log_loss":float(log_loss(y,P,labels=OUTCOMES)), "accuracy":float(accuracy_score(y,pred)), "balanced_accuracy":float(balanced_accuracy_score(y,pred)), "macro_f1":float(f1_score(y,pred,average="macro",zero_division=0))}


def main():
    if not DATA.exists():
        raise FileNotFoundError("Place IPL.csv next to train_models.py before retraining.")
    print("Reading IPL.csv...", flush=True)
    df = prepare(pd.read_csv(DATA, low_memory=False))
    df = df[df["match_type"].fillna("T20").astype(str).str.contains("T20", na=False)]
    df = df.sort_values("date")
    print("Rows:", len(df), "Dates:", df["date"].min(), df["date"].max(), flush=True)

    # time split: last 20% chronologically as test
    cutoff = df["date"].quantile(0.8)
    train = df[df["date"] <= cutoff]
    test = df[df["date"] > cutoff]
    # cap for fast reproducible deployment training, but preserve all data for empirical priors/player metadata
    train_ml = train.sample(min(len(train), 25000), random_state=17) if len(train) > 60000 else train
    X_train, y_train = train_ml[FEATURES], train_ml["outcome"]
    test_eval = test.sample(min(len(test), 15000), random_state=17) if len(test) > 35000 else test
    X_test, y_test = test_eval[FEATURES], test_eval["outcome"]

    priors = empirical_distributions(train)
    meta = player_metadata(df)

    report = [baseline_eval(test, priors["global"])]
    models = {}

    candidates = {
        "random_forest": RandomForestClassifier(n_estimators=70, min_samples_leaf=45, max_features="sqrt", n_jobs=-1, random_state=17, class_weight="balanced_subsample"),
    }

    for name, clf in candidates.items():
        print("Training", name, flush=True)
        pipe = Pipeline([("pre", make_preprocessor()), ("clf", clf)])
        try:
            pipe.fit(X_train, y_train)
            rep = evaluate(name, pipe, X_test, y_test)
            report.append(rep)
            models[name] = pipe
            joblib.dump(pipe, MODELS / f"{name}.joblib")
            print(rep, flush=True)
        except Exception as e:
            print("Skipped", name, e, flush=True)

    if HAS_XGB:
        print("Training xgboost", flush=True)
        try:
            phase_map={"powerplay":0,"middle":1,"death":2}
            xgb_cols=["innings","over","legal_ball","team_runs","team_wicket","batter_runs","batter_balls"]
            xgb_idx = X_train.sample(min(len(X_train), 7000), random_state=23).index
            X_train_xgb = X_train.loc[xgb_idx]
            y_train_xgb = y_train.loc[xgb_idx]
            Xtr = X_train_xgb[xgb_cols].apply(pd.to_numeric, errors="coerce").fillna(0).copy()
            Xtr["phase_code"] = X_train_xgb["phase"].map(phase_map).fillna(1).astype(float)
            Xte = X_test[xgb_cols].apply(pd.to_numeric, errors="coerce").fillna(0).copy()
            Xte["phase_code"] = X_test["phase"].map(phase_map).fillna(1).astype(float)
            y_map = {c:i for i,c in enumerate(OUTCOMES)}
            xgb = XGBClassifier(n_estimators=15, max_depth=3, learning_rate=0.12, subsample=0.85, colsample_bytree=0.85, objective="multi:softprob", eval_metric="mlogloss", tree_method="hist", random_state=17, n_jobs=1)
            xgb.fit(Xtr.values, pd.Series(y_train_xgb).map(y_map).values)
            model = XGBOutcomeWrapper(xgb, OUTCOMES)
            rep = evaluate("xgboost", model, X_test, y_test)
            report.append(rep)
            models["xgboost"] = model
            joblib.dump(model, MODELS / "xgboost.joblib")
            print(rep, flush=True)
        except Exception as e:
            print("Skipped xgboost", e, flush=True)

    # Save empirical/blend artefacts
    joblib.dump(priors, MODELS / "baseline_prior.joblib")
    pd.DataFrame(report).sort_values("log_loss").to_csv(ART / "model_report.csv", index=False)
    best = pd.DataFrame(report).sort_values("log_loss").iloc[0]["model"]
    metadata = {
        "version": "3.0",
        "features": FEATURES,
        "numeric_features": NUM_FEATURES,
        "categorical_features": CAT_FEATURES,
        "outcomes": OUTCOMES,
        "best_model_by_log_loss": best,
        "cutoff_date": str(cutoff.date()),
        "n_rows": int(len(df)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        **meta,
    }
    with open(ART / "metadata.json", "w") as f:
        json.dump(metadata, f)
    print("Best:", best)

if __name__ == "__main__":
    main()
