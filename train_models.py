"""
CricPredAI model training pipeline.

The raw delivery CSV is needed only for retraining. Simulations load the compact
artifacts produced here and never scan the full dataset.
"""
from __future__ import annotations

import argparse
import json
import shutil
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from data_pipeline import (
    CAT_FEATURES,
    FEATURES,
    NUM_FEATURES,
    OUTCOMES,
    data_fingerprint,
    load_dataset_source,
    parse_fielders,
    prepare_deliveries,
)
from model_wrappers import EncodedOutcomeClassifier, FastPipelineOutcomeModel
from probability import calibrated_blend, empirical_matrix, normalize_array

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBClassifier

    HAS_XGB = True
except Exception:
    HAS_XGB = False

ROOT = Path(__file__).resolve().parent
PREPARED_CACHE_SCHEMA = 2
DEFAULT_DATA_CANDIDATES = [
    ROOT / "Data" / "ipl_dataset",
    ROOT / "Data" / "IPL.csv",
    ROOT / "IPL.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train leakage-safe CricPredAI artifacts.")
    parser.add_argument(
        "--data",
        type=Path,
        help="Path to a delivery CSV or normalized Kaggle dataset directory.",
    )
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts")
    parser.add_argument(
        "--max-training-rows",
        type=int,
        default=None,
        help="Optional development cap. Omit for the production full-data run.",
    )
    parser.add_argument("--no-cache", action="store_true", help="Rebuild prepared data.")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--profiles",
        nargs="+",
        choices=["modern", "lifetime", "world"],
        default=["modern", "lifetime"],
        help=(
            "Artifact profiles to train. Modern uses recency weighting; "
            "lifetime uses equal weights; world is an equal-weight profile "
            "intended for a multi-league Cricsheet corpus "
            "(see cricsheet_ingest.py)."
        ),
    )
    return parser.parse_args()


def resolve_data_path(explicit: Path | None) -> Path:
    candidates = [explicit] if explicit else DEFAULT_DATA_CANDIDATES
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate.resolve()
    locations = ", ".join(str(path) for path in DEFAULT_DATA_CANDIDATES)
    raise FileNotFoundError(f"No IPL CSV found. Supply --data PATH or place it at: {locations}")


def load_prepared(path: Path, cache_dir: Path, use_cache: bool) -> tuple[pd.DataFrame, str]:
    fingerprint = data_fingerprint(path)
    cache_path = cache_dir / f"prepared_v{PREPARED_CACHE_SCHEMA}_{fingerprint}.pkl"
    if use_cache and cache_path.exists():
        print(f"Loading prepared delivery cache: {cache_path}", flush=True)
        return pd.read_pickle(cache_path), fingerprint

    print(f"Reading and preparing {path}...", flush=True)
    prepared = prepare_deliveries(load_dataset_source(path))
    if use_cache:
        cache_dir.mkdir(parents=True, exist_ok=True)
        prepared.to_pickle(cache_path)
    return prepared, fingerprint


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                NUM_FEATURES,
            ),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", min_frequency=8),
                CAT_FEATURES,
            ),
        ],
        sparse_threshold=0.2,
    )


def _distribution(group: pd.DataFrame, base: np.ndarray | None = None, strength: float = 0.0) -> dict:
    counts = (
        group.groupby("outcome", sort=False)["_profile_weight"]
        .sum()
        .reindex(OUTCOMES, fill_value=0)
        .to_numpy(dtype=float, copy=True)
    )
    if base is None:
        counts += 1.0
    else:
        counts += strength * base
    probabilities = counts / counts.sum()
    return {
        "n": int(len(group)),
        "p": {outcome: float(probabilities[index]) for index, outcome in enumerate(OUTCOMES)},
    }


def empirical_distributions(df: pd.DataFrame, weights: np.ndarray | None = None) -> dict:
    weighted = df.copy()
    weighted["_profile_weight"] = 1.0 if weights is None else np.asarray(weights, dtype=float)
    global_entry = _distribution(weighted)
    global_array = np.array([global_entry["p"][outcome] for outcome in OUTCOMES])

    def grouped(columns: list[str], minimum: int, strength: float) -> dict:
        result = {}
        grouper = columns[0] if len(columns) == 1 else columns
        for key, group in weighted.groupby(grouper, sort=False):
            if len(group) < minimum:
                continue
            key_tuple = key if isinstance(key, tuple) else (key,)
            result["||".join(map(str, key_tuple))] = _distribution(group, global_array, strength)
        return result

    extra_runs = {}
    for outcome in ["WD", "NB", "LB", "B"]:
        outcome_rows = weighted[weighted["outcome"].eq(outcome)].copy()
        outcome_rows["_extra_runs"] = (
            pd.to_numeric(outcome_rows["runs_total"], errors="coerce")
            .fillna(1)
            .astype(int)
            .clip(1, 7)
        )
        counts = outcome_rows.groupby("_extra_runs")["_profile_weight"].sum().sort_index()
        if counts.empty:
            counts = pd.Series({1: 1})
        probabilities = counts / counts.sum()
        extra_runs[outcome] = {str(int(run)): float(probability) for run, probability in probabilities.items()}

    return {
        "schema_version": 2,
        "outcomes": OUTCOMES,
        "global": global_entry,
        "phase": grouped(["phase"], 1, 200),
        "innings_phase": grouped(["innings", "phase"], 1, 250),
        "venue_phase": grouped(["venue", "phase"], 80, 250),
        "batting_team_phase": grouped(["batting_team", "phase"], 100, 300),
        "bowling_team_phase": grouped(["bowling_team", "phase"], 100, 300),
        "batter_phase": grouped(["batter", "phase"], 24, 80),
        "bowler_phase": grouped(["bowler", "phase"], 30, 100),
        "extra_runs": extra_runs,
    }


def player_metadata(df: pd.DataFrame, weights: np.ndarray | None = None) -> dict:
    weighted = df.copy()
    weighted["_profile_weight"] = 1.0 if weights is None else np.asarray(weights, dtype=float)
    weighted["_weighted_bat_ball"] = weighted["_ball_faced"] * weighted["_profile_weight"]
    weighted["_weighted_bat_run"] = weighted["runs_batter"] * weighted["_profile_weight"]
    weighted["_batter_dismissal"] = (
        weighted["_wicket"].eq(1)
        & weighted["player_out"].fillna("").astype(str).eq(
            weighted["batter"].astype(str)
        )
    ).astype(int)
    weighted["_weighted_dismissal"] = (
        weighted["_batter_dismissal"] * weighted["_profile_weight"]
    )
    weighted["_weighted_bowl_ball"] = weighted["valid_ball"] * weighted["_profile_weight"]
    weighted["_weighted_bowl_run"] = weighted["runs_bowler"] * weighted["_profile_weight"]
    weighted["_weighted_bowl_wicket"] = weighted["_bowler_wicket"] * weighted["_profile_weight"]

    players = sorted(set(df["batter"].astype(str)) | set(df["bowler"].astype(str)))
    global_bat_rate = float(
        weighted["_weighted_bat_run"].sum() / max(1, weighted["_weighted_bat_ball"].sum())
    )
    global_wicket_rate = float(
        weighted["_weighted_dismissal"].sum() / max(1, weighted["_weighted_bat_ball"].sum())
    )
    global_bowl_rate = float(
        weighted["_weighted_bowl_run"].sum() / max(1, weighted["_weighted_bowl_ball"].sum())
    )
    global_bowler_wicket_rate = float(
        weighted["_weighted_bowl_wicket"].sum()
        / max(1, weighted["_weighted_bowl_ball"].sum())
    )
    position_baselines = {}
    for position, group in weighted.groupby("bat_pos", sort=True):
        effective_balls = float(group["_weighted_bat_ball"].sum())
        position_baselines[int(position)] = {
            "run_rate": float(
                (group["_weighted_bat_run"].sum() + 180 * global_bat_rate)
                / (effective_balls + 180)
            ),
            "dismissal_rate": float(
                (group["_weighted_dismissal"].sum() + 180 * global_wicket_rate)
                / (effective_balls + 180)
            ),
        }

    phase_baselines = {}
    total_phase_balls = max(1.0, float(weighted["_weighted_bowl_ball"].sum()))
    for phase in ["powerplay", "middle", "death"]:
        group = weighted[weighted["phase"].eq(phase)]
        effective_balls = float(group["_weighted_bowl_ball"].sum())
        phase_baselines[phase] = {
            "run_rate": float(
                (group["_weighted_bowl_run"].sum() + 240 * global_bowl_rate)
                / (effective_balls + 240)
            ),
            "wicket_rate": float(
                (
                    group["_weighted_bowl_wicket"].sum()
                    + 240 * global_bowler_wicket_rate
                )
                / (effective_balls + 240)
            ),
            "ball_share": effective_balls / total_phase_balls,
        }

    bat = (
        weighted.groupby("batter")
        .agg(
            bat_balls=("_ball_faced", "sum"),
            weighted_bat_balls=("_weighted_bat_ball", "sum"),
            weighted_bat_runs=("_weighted_bat_run", "sum"),
            weighted_dismissals=("_weighted_dismissal", "sum"),
            avg_position=("bat_pos", "mean") if "bat_pos" in df else ("innings", "size"),
        )
        .reset_index()
    )
    bowl = (
        weighted.groupby("bowler")
        .agg(
            bowl_balls=("valid_ball", "sum"),
            weighted_bowl_balls=("_weighted_bowl_ball", "sum"),
            weighted_bowl_runs=("_weighted_bowl_run", "sum"),
            weighted_bowl_wkts=("_weighted_bowl_wicket", "sum"),
        )
        .reset_index()
    )
    stats = pd.merge(bat, bowl, left_on="batter", right_on="bowler", how="outer")
    stats["player"] = stats["batter"].fillna(stats["bowler"])
    stats = stats.fillna(0)

    position_appearances = (
        weighted[
            ["match_id", "innings", "batter", "bat_pos", "_profile_weight"]
        ]
        .drop_duplicates(["match_id", "innings", "batter"])
        .groupby(["batter", "bat_pos"], sort=False)
        .agg(
            innings=("match_id", "size"),
            effective_innings=("_profile_weight", "sum"),
        )
        .reset_index()
    )
    position_performance = (
        weighted.groupby(["batter", "bat_pos"], sort=False)
        .agg(
            balls=("_ball_faced", "sum"),
            effective_balls=("_weighted_bat_ball", "sum"),
            weighted_runs=("_weighted_bat_run", "sum"),
            weighted_dismissals=("_weighted_dismissal", "sum"),
        )
        .reset_index()
    )
    bowling_phase_performance = (
        weighted.groupby(["bowler", "phase"], sort=False)
        .agg(
            balls=("valid_ball", "sum"),
            effective_balls=("_weighted_bowl_ball", "sum"),
            weighted_runs=("_weighted_bowl_run", "sum"),
            weighted_wickets=("_weighted_bowl_wicket", "sum"),
        )
        .reset_index()
    )

    roles = {}
    for row in stats.itertuples(index=False):
        player = str(row.player)
        bat_balls = float(row.bat_balls)
        bowl_balls = float(row.bowl_balls)
        effective_bat_balls = float(row.weighted_bat_balls)
        effective_bowl_balls = float(row.weighted_bowl_balls)
        bat_rate = (
            float(row.weighted_bat_runs) + 120 * global_bat_rate
        ) / (effective_bat_balls + 120)
        dismissal_rate = (
            float(row.weighted_dismissals) + 120 * global_wicket_rate
        ) / (effective_bat_balls + 120)
        bowl_rate = (
            float(row.weighted_bowl_runs) + 180 * global_bowl_rate
        ) / (effective_bowl_balls + 180)
        wicket_rate = (
            float(row.weighted_bowl_wkts) + 180 * global_bowler_wicket_rate
        ) / (effective_bowl_balls + 180)

        if bowl_balls >= 120 and bat_balls >= 180:
            role = "all-rounder"
        elif bowl_balls >= max(60, bat_balls * 0.65):
            role = "bowler"
        else:
            role = "batter"
        player_positions = position_appearances[
            position_appearances["batter"].eq(player)
        ]
        effective_innings = float(player_positions["effective_innings"].sum())
        if effective_innings > 0:
            preferred_position = float(
                (
                    player_positions["bat_pos"]
                    * player_positions["effective_innings"]
                ).sum()
                / effective_innings
            )
            position_variance = float(
                (
                    (player_positions["bat_pos"] - preferred_position) ** 2
                    * player_positions["effective_innings"]
                ).sum()
                / effective_innings
            )
            position_spread = max(0.85, float(np.sqrt(position_variance)))
        else:
            preferred_position = float(row.avg_position or 6.0)
            position_spread = 2.5

        position_effectiveness = {}
        player_position_performance = position_performance[
            position_performance["batter"].eq(player)
        ]
        for position_row in player_position_performance.itertuples(index=False):
            position = int(position_row.bat_pos)
            effective_position_balls = float(position_row.effective_balls)
            baseline = position_baselines.get(
                position,
                {
                    "run_rate": global_bat_rate,
                    "dismissal_rate": global_wicket_rate,
                },
            )
            prior_run_rate = 0.70 * bat_rate + 0.30 * baseline["run_rate"]
            prior_dismissal_rate = (
                0.70 * dismissal_rate + 0.30 * baseline["dismissal_rate"]
            )
            posterior_run_rate = float(
                (float(position_row.weighted_runs) + 120 * prior_run_rate)
                / (effective_position_balls + 120)
            )
            posterior_dismissal_rate = float(
                (
                    float(position_row.weighted_dismissals)
                    + 120 * prior_dismissal_rate
                )
                / (effective_position_balls + 120)
            )
            position_effectiveness[str(position)] = {
                "balls": int(position_row.balls),
                "effective_balls": round(effective_position_balls, 2),
                "run_multiplier": round(
                    float(np.clip(posterior_run_rate / max(0.1, bat_rate), 0.88, 1.12)),
                    5,
                ),
                "wicket_multiplier": round(
                    float(
                        np.clip(
                            posterior_dismissal_rate
                            / max(0.005, dismissal_rate),
                            0.85,
                            1.18,
                        )
                    ),
                    5,
                ),
            }

        position_counts = {
            str(int(position_row.bat_pos)): {
                "innings": int(position_row.innings),
                "effective_innings": round(
                    float(position_row.effective_innings),
                    2,
                ),
            }
            for position_row in player_positions.itertuples(index=False)
        }

        player_phase_performance = bowling_phase_performance[
            bowling_phase_performance["bowler"].eq(player)
        ].set_index("phase")
        bowling_phases = {}
        for phase in ["powerplay", "middle", "death"]:
            if phase in player_phase_performance.index:
                phase_row = player_phase_performance.loc[phase]
                phase_balls = int(phase_row["balls"])
                effective_phase_balls = float(phase_row["effective_balls"])
                weighted_phase_runs = float(phase_row["weighted_runs"])
                weighted_phase_wickets = float(phase_row["weighted_wickets"])
            else:
                phase_balls = 0
                effective_phase_balls = 0.0
                weighted_phase_runs = 0.0
                weighted_phase_wickets = 0.0
            baseline = phase_baselines[phase]
            prior_run_rate = 0.65 * bowl_rate + 0.35 * baseline["run_rate"]
            prior_wicket_rate = (
                0.65 * wicket_rate + 0.35 * baseline["wicket_rate"]
            )
            posterior_run_rate = float(
                (weighted_phase_runs + 120 * prior_run_rate)
                / (effective_phase_balls + 120)
            )
            posterior_wicket_rate = float(
                (weighted_phase_wickets + 120 * prior_wicket_rate)
                / (effective_phase_balls + 120)
            )
            expected_share = max(0.02, float(baseline["ball_share"]))
            posterior_usage_share = float(
                (effective_phase_balls + 36 * expected_share)
                / (max(0.0, effective_bowl_balls) + 36)
            )
            usage_ratio = max(0.20, posterior_usage_share / expected_share)
            selection_score = float(
                1.30
                * np.log(
                    max(0.25, baseline["run_rate"] / max(0.1, posterior_run_rate))
                )
                + 0.80
                * np.log(
                    max(
                        0.25,
                        posterior_wicket_rate
                        / max(0.005, baseline["wicket_rate"]),
                    )
                )
                + 0.28 * np.log(usage_ratio)
            )
            bowling_phases[phase] = {
                "balls": phase_balls,
                "effective_balls": round(effective_phase_balls, 2),
                "runs_per_ball": round(posterior_run_rate, 5),
                "wicket_rate": round(posterior_wicket_rate, 5),
                "usage_share": round(posterior_usage_share, 5),
                "selection_score": round(selection_score, 5),
            }

        roles[player] = {
            "role": role,
            "batting_score": float(bat_rate - 2.2 * dismissal_rate + 0.025 * np.log1p(bat_balls)),
            "bowling_score": float(-bowl_rate + 5.0 * wicket_rate + 0.02 * np.log1p(bowl_balls)),
            "bat_runs_per_ball": float(bat_rate),
            "dismissal_rate": float(dismissal_rate),
            "bowl_runs_per_ball": float(bowl_rate),
            "wicket_rate": float(wicket_rate),
            "bat_balls": int(bat_balls),
            "bowl_balls": int(bowl_balls),
            "effective_bat_balls": round(effective_bat_balls, 2),
            "effective_bowl_balls": round(effective_bowl_balls, 2),
            "batting_position": {
                "preferred": round(preferred_position, 3),
                "spread": round(position_spread, 3),
                "innings": int(player_positions["innings"].sum()),
                "effective_innings": round(effective_innings, 2),
                "positions": position_counts,
                "effectiveness": position_effectiveness,
            },
            "bowling_phases": bowling_phases,
        }

    dismissal_aliases = {
        "caught": "caught",
        "caught and bowled": "caught_and_bowled",
        "bowled": "bowled",
        "lbw": "lbw",
        "stumped": "stumped",
        "run out": "run_out",
        "hit wicket": "hit_wicket",
    }
    dismissal_rows = weighted[weighted["_wicket"].eq(1)].copy()
    dismissal_rows["_dismissal_kind"] = (
        dismissal_rows["wicket_kind"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace("&", " and ", regex=False)
        .str.replace(r"[^a-z0-9]+", " ", regex=True)
        .str.strip()
        .map(dismissal_aliases)
    )
    dismissal_counts = (
        dismissal_rows.dropna(subset=["_dismissal_kind"])
        .groupby("_dismissal_kind")["_profile_weight"]
        .sum()
    )
    if dismissal_counts.empty:
        dismissal_probabilities = {}
    else:
        dismissal_probabilities = {
            str(kind): float(value / dismissal_counts.sum())
            for kind, value in dismissal_counts.items()
        }

    fielding = {}
    for _, row in dismissal_rows.iterrows():
        kind = row["_dismissal_kind"]
        if kind not in {"caught", "stumped", "run_out"}:
            continue
        fielders = parse_fielders(row.get("fielders_involved"))
        if not fielders:
            continue
        weight = float(row["_profile_weight"]) / len(fielders)
        metric = {
            "caught": "catches",
            "stumped": "stumpings",
            "run_out": "run_outs",
        }[kind]
        for fielder in fielders:
            stats = fielding.setdefault(
                fielder,
                {"catches": 0.0, "stumpings": 0.0, "run_outs": 0.0},
            )
            stats[metric] += weight
    fielding = {
        player: {metric: round(value, 4) for metric, value in stats.items()}
        for player, stats in fielding.items()
    }
    return {
        "players": players,
        "roles": roles,
        "venues": sorted(df["venue"].dropna().astype(str).unique()),
        "dismissal_probabilities": dismissal_probabilities,
        "fielding": fielding,
        "player_rate_baselines": {
            "bat_runs_per_ball": global_bat_rate,
            "dismissal_rate": global_wicket_rate,
            "bowl_runs_per_ball": global_bowl_rate,
            "wicket_rate": global_bowler_wicket_rate,
        },
        "batting_position_baselines": {
            str(position): {
                metric: round(value, 6)
                for metric, value in values.items()
            }
            for position, values in position_baselines.items()
        },
        "bowling_phase_baselines": {
            phase: {
                metric: round(value, 6)
                for metric, value in values.items()
            }
            for phase, values in phase_baselines.items()
        },
    }


def chronological_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matches = (
        df[["match_id", "date"]]
        .drop_duplicates("match_id")
        .sort_values(["date", "match_id"])
        .reset_index(drop=True)
    )
    if len(matches) < 10:
        raise ValueError("At least 10 matches are required for train/calibration/test splitting.")
    train_end = max(1, int(len(matches) * 0.70))
    calibration_end = max(train_end + 1, int(len(matches) * 0.85))
    train_ids = set(matches.iloc[:train_end]["match_id"])
    calibration_ids = set(matches.iloc[train_end:calibration_end]["match_id"])
    test_ids = set(matches.iloc[calibration_end:]["match_id"])
    return (
        df[df["match_id"].isin(train_ids)].copy(),
        df[df["match_id"].isin(calibration_ids)].copy(),
        df[df["match_id"].isin(test_ids)].copy(),
    )


def recency_weights(frame: pd.DataFrame, reference_date: pd.Timestamp) -> np.ndarray:
    age_years = (reference_date - frame["date"]).dt.days.clip(lower=0) / 365.25
    weights = np.power(0.5, age_years / 5.0)
    return np.clip(weights.to_numpy(dtype=float), 0.15, 1.0)


def align_probabilities(model, frame: pd.DataFrame) -> np.ndarray:
    probabilities = np.asarray(model.predict_proba(frame[FEATURES]), dtype=float)
    aligned = np.full((len(frame), len(OUTCOMES)), 1e-12)
    for source_index, outcome in enumerate(map(str, model.classes_)):
        if outcome in OUTCOMES:
            aligned[:, OUTCOMES.index(outcome)] = probabilities[:, source_index]
    return normalize_array(aligned)


def tune_calibration(
    raw: np.ndarray,
    empirical: np.ndarray,
    truth: pd.Series,
) -> dict[str, float]:
    best = {"model_weight": 1.0, "temperature": 1.0, "log_loss": float("inf")}
    for model_weight in np.linspace(0.35, 1.0, 14):
        for temperature in np.linspace(0.70, 1.45, 16):
            probabilities = calibrated_blend(
                raw,
                empirical,
                model_weight=float(model_weight),
                temperature=float(temperature),
            )
            score = log_loss(truth, probabilities, labels=OUTCOMES)
            if score < best["log_loss"]:
                best = {
                    "model_weight": float(model_weight),
                    "temperature": float(temperature),
                    "log_loss": float(score),
                }
    return best


def metrics(name: str, truth: pd.Series, probabilities: np.ndarray) -> dict:
    predictions = np.asarray(OUTCOMES)[probabilities.argmax(axis=1)]
    return {
        "model": name,
        "log_loss": float(log_loss(truth, probabilities, labels=OUTCOMES)),
        "accuracy": float(accuracy_score(truth, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, predictions)),
        "macro_f1": float(f1_score(truth, predictions, average="macro", zero_division=0)),
    }


def train_candidates(seed: int) -> dict[str, Pipeline]:
    candidates = {
        "sgd_logistic": Pipeline(
            [
                ("pre", make_preprocessor()),
                (
                    "classifier",
                    SGDClassifier(
                        loss="log_loss",
                        alpha=2e-5,
                        max_iter=80,
                        early_stopping=True,
                        validation_fraction=0.1,
                        n_iter_no_change=6,
                        random_state=seed,
                    ),
                ),
            ]
        )
    }
    if HAS_XGB:
        candidates["xgboost"] = Pipeline(
            [
                ("pre", make_preprocessor()),
                (
                    "classifier",
                    EncodedOutcomeClassifier(
                        XGBClassifier(
                            n_estimators=320,
                            max_depth=6,
                            learning_rate=0.055,
                            min_child_weight=8,
                            subsample=0.85,
                            colsample_bytree=0.80,
                            reg_alpha=0.08,
                            reg_lambda=1.2,
                            objective="multi:softprob",
                            eval_metric="mlogloss",
                            tree_method="hist",
                            random_state=seed,
                            n_jobs=-1,
                        ),
                        OUTCOMES,
                    ),
                ),
            ]
        )
    return candidates


def profile_weights(
    frame: pd.DataFrame,
    profile: str,
    reference_date: pd.Timestamp,
) -> np.ndarray:
    if profile == "modern":
        return recency_weights(frame, reference_date)
    return np.ones(len(frame), dtype=float)


def train_profile(
    profile: str,
    *,
    df: pd.DataFrame,
    train: pd.DataFrame,
    calibration: pd.DataFrame,
    test: pd.DataFrame,
    artifact_dir: Path,
    data_path: Path,
    fingerprint: str,
    seed: int,
    max_training_rows: int | None,
) -> None:
    print(f"\n=== Training {profile} profile ===", flush=True)
    profile_root = artifact_dir / "profiles"
    profile_dir = profile_root / profile
    staging_dir = profile_root / f".{profile}_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_models_dir = staging_dir / "models"
    staging_models_dir.mkdir(parents=True)

    reference_date = df["date"].max()
    train_weights = profile_weights(train, profile, reference_date)
    calibration_weights = profile_weights(calibration, profile, reference_date)
    test_weights = profile_weights(test, profile, reference_date)
    full_weights = profile_weights(df, profile, reference_date)

    priors = empirical_distributions(train, train_weights)
    metadata = player_metadata(df, full_weights)
    empirical_calibration = empirical_matrix(priors, calibration[FEATURES])
    empirical_test = empirical_matrix(priors, test[FEATURES])
    report = [metrics("baseline_prior", test["outcome"], empirical_test)]
    calibrations = {}
    test_predictions = {}
    calibration_predictions = {}

    for name, model in train_candidates(seed).items():
        print(f"Training {profile}/{name}...", flush=True)
        fit_kwargs = {}
        if profile == "modern":
            fit_kwargs["classifier__sample_weight"] = train_weights
        model.fit(train[FEATURES], train["outcome"], **fit_kwargs)
        raw_calibration = align_probabilities(model, calibration)
        calibration_config = tune_calibration(
            raw_calibration,
            empirical_calibration,
            calibration["outcome"],
        )
        raw_test = align_probabilities(model, test)
        calibrated_test = calibrated_blend(
            raw_test,
            empirical_test,
            model_weight=calibration_config["model_weight"],
            temperature=calibration_config["temperature"],
        )
        report.append(metrics(name, test["outcome"], calibrated_test))
        calibrations[name] = calibration_config
        test_predictions[name] = raw_test
        calibration_predictions[name] = raw_calibration
        print(report[-1], calibration_config, flush=True)

    if test_predictions:
        ensemble_names = sorted(
            calibrations,
            key=lambda name: calibrations[name]["log_loss"],
        )[: min(2, len(calibrations))]
        inverse_losses = np.array([1.0 / calibrations[name]["log_loss"] for name in ensemble_names])
        ensemble_weights = inverse_losses / inverse_losses.sum()
        raw_ensemble_calibration = sum(
            weight * calibration_predictions[name]
            for weight, name in zip(ensemble_weights, ensemble_names, strict=True)
        )
        raw_ensemble_test = sum(
            weight * test_predictions[name]
            for weight, name in zip(ensemble_weights, ensemble_names, strict=True)
        )
        ensemble_calibration = tune_calibration(
            raw_ensemble_calibration,
            empirical_calibration,
            calibration["outcome"],
        )
        ensemble_test = calibrated_blend(
            raw_ensemble_test,
            empirical_test,
            model_weight=ensemble_calibration["model_weight"],
            temperature=ensemble_calibration["temperature"],
        )
        report.append(metrics("calibrated_blend", test["outcome"], ensemble_test))
        calibrations["calibrated_blend"] = {
            **ensemble_calibration,
            "members": ensemble_names,
            "member_weights": [float(value) for value in ensemble_weights],
        }

    production_frame = df
    production_weights = full_weights
    if max_training_rows and len(production_frame) > max_training_rows:
        production_frame = production_frame.sample(max_training_rows, random_state=seed).sort_index()
        production_weights = profile_weights(production_frame, profile, reference_date)
    for name, model in train_candidates(seed).items():
        print(
            f"Refitting deployment {profile}/{name} on {len(production_frame):,} rows...",
            flush=True,
        )
        fit_kwargs = {}
        if profile == "modern":
            fit_kwargs["classifier__sample_weight"] = production_weights
        model.fit(production_frame[FEATURES], production_frame["outcome"], **fit_kwargs)
        classifier = model.named_steps["classifier"]
        if hasattr(classifier, "estimator") and hasattr(classifier.estimator, "set_params"):
            classifier.estimator.set_params(n_jobs=1)
        joblib.dump(
            FastPipelineOutcomeModel(model, NUM_FEATURES, CAT_FEATURES),
            staging_models_dir / f"{name}.joblib",
            compress=3,
        )

    production_priors = empirical_distributions(df, full_weights)
    joblib.dump(production_priors, staging_models_dir / "baseline_prior.joblib", compress=3)
    report_frame = pd.DataFrame(report).sort_values("log_loss")
    report_frame.to_csv(staging_dir / "model_report.csv", index=False)

    metadata.update(
        {
            "version": "7.0",
            "artifact_schema": 7,
            "profile": profile,
            "profile_description": (
                "Recency-weighted modern IPL form with a five-year half-life."
                if profile == "modern"
                else "Equal-weight multi-league world evidence across every ingested competition."
                if profile == "world"
                else "Equal-weight lifetime IPL history for legends and cross-era simulations."
            ),
            "features": FEATURES,
            "numeric_features": NUM_FEATURES,
            "categorical_features": CAT_FEATURES,
            "outcomes": OUTCOMES,
            "best_model_by_log_loss": str(report_frame.iloc[0]["model"]),
            "model_calibration": calibrations,
            "data_fingerprint": fingerprint,
            "data_source": (
                "maratheabhishek/ipl-dataset-2008-to-2025"
                if data_path.is_dir()
                else data_path.name
            ),
            "data_start_date": str(df["date"].min().date()),
            "data_end_date": str(df["date"].max().date()),
            "n_rows": int(len(df)),
            "n_matches": int(df["match_id"].nunique()),
            "train_rows": int(len(train)),
            "calibration_rows": int(len(calibration)),
            "test_rows": int(len(test)),
            "leakage_safe_pre_delivery_features": True,
            "recency_weight_half_life_years": 5.0 if profile == "modern" else None,
            "equal_weight_lifetime_data": profile in ("lifetime", "world"),
            "matchup_adjustment_strength": 1.0,
            "batting_position_adjustment_strength": 1.0,
            "bowling_phase_selection_strength": 1.0,
            "simulation_calibration": {
                "target_chase_win_rate": 0.5454,
                "chase_scoring_multiplier": 0.976,
                "chase_wicket_multiplier": 1.05,
            },
        }
    )
    (staging_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    backup_dir = profile_root / f".{profile}_backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    if profile_dir.exists():
        profile_dir.rename(backup_dir)
    staging_dir.rename(profile_dir)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    if profile == "modern":
        top_models = artifact_dir / "models"
        top_models_staging = artifact_dir / "models_staging"
        if top_models_staging.exists():
            shutil.rmtree(top_models_staging)
        shutil.copytree(profile_dir / "models", top_models_staging)
        top_models_backup = artifact_dir / "models_backup"
        if top_models_backup.exists():
            shutil.rmtree(top_models_backup)
        if top_models.exists():
            top_models.rename(top_models_backup)
        top_models_staging.rename(top_models)
        if top_models_backup.exists():
            shutil.rmtree(top_models_backup)
        shutil.copy2(profile_dir / "metadata.json", artifact_dir / "metadata.json")
        shutil.copy2(profile_dir / "model_report.csv", artifact_dir / "model_report.csv")

    print(
        f"Best {profile} test model: {metadata['best_model_by_log_loss']}",
        flush=True,
    )


def main() -> None:
    args = parse_args()
    data_path = resolve_data_path(args.data)
    artifact_dir = args.artifacts.resolve()
    cache_dir = artifact_dir / "cache"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    df, fingerprint = load_prepared(data_path, cache_dir, not args.no_cache)
    df = df.sort_values(["date", "match_id", "innings", "over", "ball", "_row_order"])
    train, calibration, test = chronological_split(df)
    if args.max_training_rows and len(train) > args.max_training_rows:
        train = train.sample(args.max_training_rows, random_state=args.seed).sort_index()

    print(
        f"Prepared {len(df):,} deliveries across {df['match_id'].nunique():,} matches "
        f"({df['date'].min().date()} to {df['date'].max().date()}).",
        flush=True,
    )
    print(
        f"Split rows: train={len(train):,}, calibration={len(calibration):,}, test={len(test):,}",
        flush=True,
    )

    for profile in args.profiles:
        train_profile(
            profile,
            df=df,
            train=train,
            calibration=calibration,
            test=test,
            artifact_dir=artifact_dir,
            data_path=data_path,
            fingerprint=fingerprint,
            seed=args.seed,
            max_training_rows=args.max_training_rows,
        )


if __name__ == "__main__":
    main()
