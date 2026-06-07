from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
import joblib

from data_pipeline import FEATURES, OUTCOMES, canonicalize_team, canonicalize_venue, phase_from_over
from probability import calibrated_blend, empirical_array, normalize_array, normalize_dict

LEGAL_OUTCOMES = {"0","1","2","3","4","6","W","LB","B"}
EXTRA_OUTCOMES = {"WD","NB"}
DEFAULT_DISMISSAL_PROBABILITIES = {
    "caught": 0.6325,
    "caught_and_bowled": 0.0279,
    "bowled": 0.1681,
    "lbw": 0.0610,
    "stumped": 0.0267,
    "run_out": 0.0825,
    "hit_wicket": 0.0013,
}

ART = Path(__file__).resolve().parent / "artifacts"


def available_profiles() -> list[str]:
    profile_root = ART / "profiles"
    if profile_root.exists():
        profiles = sorted(
            (
                path.name
                for path in profile_root.iterdir()
                if path.is_dir() and (path / "metadata.json").exists()
            ),
            key=lambda name: (name != "modern", name),
        )
        if profiles:
            return profiles
    return ["modern"]


def load_artifacts(profile: str = "modern"):
    profile_dir = ART / "profiles" / profile
    if profile_dir.exists():
        metadata_path = profile_dir / "metadata.json"
        report_path = profile_dir / "model_report.csv"
        models_dir = profile_dir / "models"
    elif profile == "modern":
        metadata_path = ART / "metadata.json"
        report_path = ART / "model_report.csv"
        models_dir = ART / "models"
    else:
        raise ValueError(
            f"Unknown artifact profile {profile!r}. Available profiles: {available_profiles()}"
        )

    with open(metadata_path, encoding="utf-8") as f:
        meta = json.load(f)
    report = pd.read_csv(report_path) if report_path.exists() else pd.DataFrame()
    models = {}
    load_errors = {}
    for p in models_dir.glob("*.joblib"):
        try:
            models[p.stem] = joblib.load(p)
        except Exception as exc:
            load_errors[p.stem] = str(exc)
    warnings = []
    if int(meta.get("artifact_schema", 0)) < 4:
        warnings.append(
            "Legacy v3 artifacts detected. Retrain with train_models.py to use "
            "leakage-safe state, chase context, and learned calibration."
        )
    elif int(meta.get("artifact_schema", 0)) < 7:
        warnings.append(
            "These artifacts predate learned batting-position and bowling-phase "
            "roles. Retrain with train_models.py for role-aware simulations."
        )
    if load_errors:
        warnings.append(f"Could not load model artifacts: {sorted(load_errors)}")
    meta.setdefault("profile", profile)
    meta["_available_profiles"] = available_profiles()
    meta["_artifact_warnings"] = warnings
    return meta, report, models


def vector_input(state: dict, batter: str, bowler: str, batting_team: str, bowling_team: str, venue: str, toss_decision: str) -> pd.DataFrame:
    balls_bowled = int(state.get("balls_bowled", 0))
    balls_remaining = max(0, 120 - balls_bowled)
    runs = int(state.get("runs", 0))
    wickets = int(state.get("wickets", 0))
    batter_runs = int(state.get("bat_runs", {}).get(batter, 0))
    batter_balls = int(state.get("bat_balls", {}).get(batter, 0))
    target = int(state.get("target") or 0)
    innings = int(state.get("innings", 1))
    runs_required = max(0, target - runs) if innings == 2 else 0
    current_run_rate = 6.0 * runs / balls_bowled if balls_bowled else 0.0
    required_run_rate = (
        6.0 * runs_required / balls_remaining
        if innings == 2 and balls_remaining
        else 0.0
    )
    row = {
        "innings": innings,
        "over": int(state.get("over", 0)),
        "legal_ball": max(1, int(state.get("legal_ball", 1))),
        "balls_bowled": balls_bowled,
        "balls_remaining": balls_remaining,
        "team_runs": runs,
        "team_wicket": wickets,
        "wickets_remaining": max(0, 10 - wickets),
        "current_run_rate": current_run_rate,
        "batter_runs": batter_runs,
        "batter_balls": batter_balls,
        "batter_strike_rate": 100.0 * batter_runs / batter_balls if batter_balls else 0.0,
        "target": target,
        "runs_required": runs_required,
        "required_run_rate": required_run_rate,
        "rate_pressure": required_run_rate - current_run_rate if innings == 2 else 0.0,
        "phase": phase_from_over(int(state.get("over", 0))),
        "batting_team": canonicalize_team(batting_team),
        "bowling_team": canonicalize_team(bowling_team),
        "batter": batter,
        "bowler": bowler,
        "venue": canonicalize_venue(venue),
        "toss_decision": toss_decision,
    }
    return pd.DataFrame([row], columns=FEATURES)


def normalise(d: Dict[str,float]) -> Dict[str,float]:
    return normalize_dict(d)


def get_empirical(
    priors: dict,
    batter: str,
    bowler: str,
    phase: str,
    innings: int = 1,
    venue: str = "Unknown",
    batting_team: str = "Unknown",
    bowling_team: str = "Unknown",
) -> Dict[str,float]:
    values = empirical_array(
        priors,
        batter=batter,
        bowler=bowler,
        phase=phase,
        innings=innings,
        venue=venue,
        batting_team=batting_team,
        bowling_team=bowling_team,
    )
    return {outcome: float(values[index]) for index, outcome in enumerate(OUTCOMES)}


def _aligned_model_probabilities(model, x: pd.DataFrame) -> np.ndarray:
    raw = np.asarray(model.predict_proba(x), dtype=float)[0]
    classes = [str(value) for value in getattr(model, "classes_", OUTCOMES)]
    aligned = np.full(len(OUTCOMES), 1e-12)
    for index, outcome in enumerate(classes):
        if outcome in OUTCOMES:
            aligned[OUTCOMES.index(outcome)] = raw[index]
    return normalize_array(aligned)


def model_probs(
    model_name: str,
    models: dict,
    priors: dict,
    x: pd.DataFrame,
    batter: str,
    bowler: str,
    phase: str,
    meta: Optional[dict] = None,
) -> Dict[str,float]:
    meta = meta or {}
    row = x.iloc[0]
    empirical = empirical_array(
        priors,
        batter=batter,
        bowler=bowler,
        phase=phase,
        innings=int(row.get("innings", 1)),
        venue=str(row.get("venue", "Unknown")),
        batting_team=str(row.get("batting_team", "Unknown")),
        bowling_team=str(row.get("bowling_team", "Unknown")),
    )
    if model_name == "baseline_prior":
        result = empirical
    else:
        calibration = meta.get("model_calibration", {}).get(model_name, {})
        if model_name == "calibrated_blend":
            members = calibration.get("members", [])
            weights = calibration.get("member_weights", [])
            available = [(name, float(weight)) for name, weight in zip(members, weights) if name in models]
            if not available:
                preferred = [name for name in ("xgboost", "sgd_logistic", "random_forest") if name in models]
                available = [(name, 1.0 / len(preferred)) for name in preferred] if preferred else []
            if available:
                total_weight = sum(weight for _, weight in available)
                model_probability = sum(
                    (weight / total_weight) * _aligned_model_probabilities(models[name], x)
                    for name, weight in available
                )
            else:
                model_probability = empirical
        elif model_name in models:
            model_x = x
            if int(meta.get("artifact_schema", 0)) < 4 and int(row.get("innings", 1)) == 2:
                # V3 learned from leaked post-ball state and an unconditioned innings flag.
                # Neutralising innings prevents the historical chase artifact until retraining.
                model_x = x.copy()
                model_x["innings"] = 1
            model_probability = _aligned_model_probabilities(models[model_name], model_x)
        else:
            model_probability = empirical

        legacy_weights = {"xgboost": 0.75, "random_forest": 0.60, "sgd_logistic": 0.70}
        model_weight = float(calibration.get("model_weight", legacy_weights.get(model_name, 0.70)))
        temperature = float(calibration.get("temperature", 1.0))
        result = calibrated_blend(
            model_probability.reshape(1, -1),
            empirical.reshape(1, -1),
            model_weight=model_weight,
            temperature=temperature,
        )[0]
    return {outcome: float(result[index]) for index, outcome in enumerate(OUTCOMES)}


def choose_next_batter(available: List[str], used: List[str], meta: dict, phase: str, wickets: int) -> Optional[str]:
    remaining = [p for p in available if p not in used]
    return remaining[0] if remaining else None


def choose_bowler(bowlers: List[str], meta: dict, over: int, bowler_overs: Dict[str,int], prev_bowler: Optional[str]) -> Tuple[str,str]:
    phase = phase_from_over(over)
    roles = meta.get("roles", {})
    candidates = [b for b in bowlers if bowler_overs.get(b,0) < 4 and b != prev_bowler]
    if not candidates:
        candidates = [b for b in bowlers if bowler_overs.get(b,0) < 4] or bowlers
    phase_order = ["powerplay", "middle", "death"]
    current_phase_index = phase_order.index(phase)

    def future_reserve(bowler: str) -> int:
        if phase == "death":
            return 0
        phase_records = roles.get(bowler, {}).get("bowling_phases", {})
        future_phases = phase_order[current_phase_index + 1 :]
        future_share = sum(
            max(
                0.0,
                float(phase_records.get(future_phase, {}).get("usage_share", 0.0)),
            )
            for future_phase in future_phases
        )
        current_score = float(
            phase_records.get(phase, {}).get("selection_score", 0.0)
        )
        best_future_score = max(
            (
                float(
                    phase_records.get(future_phase, {}).get(
                        "selection_score",
                        0.0,
                    )
                )
                for future_phase in future_phases
            ),
            default=current_score,
        )
        raw_reserve = 4.0 * future_share
        reserve = (
            int(np.ceil(raw_reserve))
            if best_future_score > current_score + 0.08
            else int(np.rint(raw_reserve))
        )
        return int(np.clip(reserve, 0, 3))

    schedule_safe = [
        bowler
        for bowler in candidates
        if bowler_overs.get(bowler, 0) < 4 - future_reserve(bowler)
    ]
    if schedule_safe:
        candidates = schedule_safe
    total_usage = sum(
        np.sqrt(max(0.0, float(roles.get(b, {}).get("effective_bowl_balls", 0.0))) + 60.0)
        for b in bowlers
    )
    phase_strength = max(
        0.0,
        float(meta.get("bowling_phase_selection_strength", 1.0)),
    )

    def score(b):
        r = roles.get(b,{})
        phase_record = r.get("bowling_phases", {}).get(phase, {})
        base = phase_strength * float(phase_record.get("selection_score", 0.0))
        balls = float(r.get("bowl_balls",0))
        base += 0.10 * float(r.get("bowling_score", 0.0))
        if r.get("role") in ["bowler","all-rounder"]:
            base += 0.16
        usage_weight = np.sqrt(
            max(0.0, float(r.get("effective_bowl_balls", balls))) + 60.0
        )
        expected_overs = min(
            4.0,
            20.0 * usage_weight / max(1.0, total_usage),
        )
        base -= 0.18 * max(
            0.0,
            bowler_overs.get(b, 0) + 1 - expected_overs,
        )
        return base
    chosen = max(candidates, key=score)
    phase_record = roles.get(chosen, {}).get("bowling_phases", {}).get(phase, {})
    sample = int(phase_record.get("balls", 0))
    reason = (
        f"selected for {phase} from the user-approved bowling options using "
        f"Bayesian-smoothed phase record ({sample} historical balls), workload, "
        "and the four-over limit"
    )
    return chosen, reason


def resolve_bowling_options(
    bowling_xi: List[str],
    selected_bowlers: Optional[List[str]],
    meta: dict,
) -> List[str]:
    xi = list(dict.fromkeys(bowling_xi))
    if selected_bowlers is not None:
        selected = [
            player
            for player in dict.fromkeys(selected_bowlers)
            if player in xi
        ]
        if len(selected) < 5:
            raise ValueError("At least five selected bowlers must belong to the playing XI.")
        return selected

    roles = meta.get("roles", {})
    ranked = sorted(
        xi,
        key=lambda player: (
            roles.get(player, {}).get("role") in {"bowler", "all-rounder"},
            float(roles.get(player, {}).get("effective_bowl_balls", 0.0)),
            float(roles.get(player, {}).get("bowling_score", 0.0)),
        ),
        reverse=True,
    )
    primary = [
        player
        for player in ranked
        if roles.get(player, {}).get("role") in {"bowler", "all-rounder"}
        and float(roles.get(player, {}).get("bowl_balls", 0.0)) >= 30
    ]
    target_count = min(7, max(5, len(primary)))
    selected = primary[:target_count]
    for player in ranked:
        if player not in selected:
            selected.append(player)
        if len(selected) >= target_count:
            break
    return selected


def rotate_strike(striker, non_striker):
    return non_striker, striker


def _choose_fielder(
    bowling_xi: List[str],
    bowler: str,
    meta: dict,
    metric: str,
    rng: np.random.Generator,
) -> Optional[str]:
    candidates = [player for player in bowling_xi if player != bowler]
    if not candidates:
        return None
    fielding = meta.get("fielding", {})
    weights = np.array(
        [max(0.0, float(fielding.get(player, {}).get(metric, 0.0))) for player in candidates],
        dtype=float,
    )
    if weights.sum() <= 0:
        weights = np.ones(len(candidates), dtype=float)
    else:
        weights += max(0.25, float(np.median(weights[weights > 0])) * 0.10)
    return str(rng.choice(candidates, p=weights / weights.sum()))


def sample_dismissal(
    bowling_xi: List[str],
    bowler: str,
    meta: dict,
    rng: np.random.Generator,
) -> dict:
    configured = meta.get("dismissal_probabilities", {})
    probabilities = {
        kind: max(
            0.0,
            float(configured.get(kind, 0.0) if configured else fallback),
        )
        for kind, fallback in DEFAULT_DISMISSAL_PROBABILITIES.items()
    }
    kinds = list(probabilities)
    weights = normalize_array([probabilities[kind] for kind in kinds])
    kind = str(rng.choice(kinds, p=weights))
    fielder = ""
    bowler_credit = kind != "run_out"

    if kind == "caught":
        fielder = _choose_fielder(bowling_xi, bowler, meta, "catches", rng) or ""
        if fielder:
            text = f"c {fielder} b {bowler}"
        else:
            kind = "caught_and_bowled"
            text = f"c & b {bowler}"
    elif kind == "caught_and_bowled":
        fielder = bowler
        text = f"c & b {bowler}"
    elif kind == "bowled":
        text = f"b {bowler}"
    elif kind == "lbw":
        text = f"lbw b {bowler}"
    elif kind == "stumped":
        fielder = _choose_fielder(bowling_xi, bowler, meta, "stumpings", rng) or ""
        text = f"st {fielder} b {bowler}" if fielder else f"st b {bowler}"
    elif kind == "run_out":
        fielder = _choose_fielder(bowling_xi, bowler, meta, "run_outs", rng) or ""
        text = f"run out ({fielder})" if fielder else "run out"
    else:
        text = f"hit wicket b {bowler}"

    return {
        "kind": kind,
        "text": text,
        "fielder": fielder,
        "bowler_credit": bowler_credit,
    }


def _sample_extra_runs(priors: dict, outcome: str, rng: np.random.Generator) -> int:
    values = priors.get("extra_runs", {}).get(outcome, [1])
    if isinstance(values, dict):
        runs = np.array([int(value) for value in values], dtype=int)
        probabilities = normalize_array([values[str(value)] for value in runs])
        return int(rng.choice(runs, p=probabilities))
    if not values:
        return 1
    return int(rng.choice(values))


def outcome_to_runs(out: str, priors: dict, rng: np.random.Generator, free_hit: bool=False) -> Tuple[int,int,bool,str,bool]:
    """returns runs_total, batter_runs, wicket, extra_type, legal_ball"""
    if out == "W" and free_hit:
        out = "1" if rng.random() < 0.45 else "0"
    if out in ["0","1","2","3","4","6"]:
        br = int(out); return br, br, False, "", True
    if out == "W": return 0, 0, True, "", True
    if out in ["WD","NB"]:
        extra = _sample_extra_runs(priors, out, rng)
        extra = max(1, min(extra, 7))
        return extra, max(0, extra-1 if out == "NB" else 0), False, "wides" if out=="WD" else "noballs", False
    if out in ["LB","B"]:
        extra = _sample_extra_runs(priors, out, rng)
        extra = max(1, min(extra, 4))
        return extra, 0, False, "legbyes" if out=="LB" else "byes", True
    return 0,0,False,"",True


def apply_match_context(
    probabilities: Dict[str, float],
    *,
    innings: int,
    runs: int,
    balls_bowled: int,
    target: Optional[int],
    learned_chase_context: bool = True,
) -> Dict[str, float]:
    adjusted = dict(probabilities)
    # V4+ models learn chase pressure directly. This fallback exists only for
    # legacy artifacts that lack target and required-rate features.
    if innings == 2 and target and not learned_chase_context:
        balls_remaining = max(1, 120 - balls_bowled)
        runs_required = max(0, target - runs)
        required_rate = 6.0 * runs_required / balls_remaining
        expected_runs = sum(
            adjusted[outcome] * int(outcome)
            for outcome in ["1", "2", "3", "4", "6"]
        )
        expected_rate = 6.0 * expected_runs
        pressure = required_rate - expected_rate
        if pressure > 0:
            aggression = min(1.35, 1.0 + 0.035 * pressure)
            adjusted["4"] *= aggression
            adjusted["6"] *= aggression
            adjusted["2"] *= min(1.15, 1.0 + 0.012 * pressure)
            adjusted["W"] *= min(1.25, 1.0 + 0.022 * pressure)
            adjusted["0"] *= max(0.78, 1.0 - 0.018 * pressure)
        elif pressure < -1.5:
            control = min(0.16, 0.025 * abs(pressure))
            adjusted["W"] *= 1.0 - control
            adjusted["6"] *= 1.0 - control / 2
            adjusted["1"] *= 1.0 + control / 2
    return normalise(adjusted)


def apply_player_matchup(
    probabilities: Dict[str, float],
    batter: str,
    bowler: str,
    meta: dict,
) -> Dict[str, float]:
    roles = meta.get("roles", {})
    baselines = meta.get("player_rate_baselines", {})
    batter_stats = roles.get(batter, {})
    bowler_stats = roles.get(bowler, {})
    baseline_bat_rate = max(0.1, float(baselines.get("bat_runs_per_ball", 1.35)))
    baseline_dismissal = max(0.005, float(baselines.get("dismissal_rate", 0.05)))
    baseline_bowl_rate = max(0.1, float(baselines.get("bowl_runs_per_ball", 1.40)))
    baseline_wicket_rate = max(0.005, float(baselines.get("wicket_rate", 0.05)))

    batter_run_ratio = float(
        np.clip(
            float(batter_stats.get("bat_runs_per_ball", baseline_bat_rate))
            / baseline_bat_rate,
            0.72,
            1.35,
        )
    )
    bowler_run_ratio = float(
        np.clip(
            baseline_bowl_rate
            / float(bowler_stats.get("bowl_runs_per_ball", baseline_bowl_rate)),
            0.72,
            1.35,
        )
    )
    dismissal_ratio = float(
        np.clip(
            float(batter_stats.get("dismissal_rate", baseline_dismissal))
            / baseline_dismissal,
            0.70,
            1.45,
        )
    )
    bowler_wicket_ratio = float(
        np.clip(
            float(bowler_stats.get("wicket_rate", baseline_wicket_rate))
            / baseline_wicket_rate,
            0.70,
            1.45,
        )
    )
    strength = max(0.0, float(meta.get("matchup_adjustment_strength", 1.0)))
    run_ratio = (batter_run_ratio * bowler_run_ratio) ** strength
    wicket_ratio = (dismissal_ratio * bowler_wicket_ratio) ** strength

    adjusted = dict(probabilities)
    adjusted["0"] *= run_ratio ** -0.65
    adjusted["1"] *= run_ratio ** 0.35
    adjusted["2"] *= run_ratio ** 0.75
    adjusted["3"] *= run_ratio ** 0.75
    adjusted["4"] *= run_ratio ** 1.15
    adjusted["6"] *= run_ratio ** 1.40
    adjusted["W"] *= wicket_ratio
    return normalise(adjusted)


def apply_batting_position(
    probabilities: Dict[str, float],
    batter: str,
    batting_position: int,
    meta: dict,
) -> Dict[str, float]:
    position_record = (
        meta.get("roles", {})
        .get(batter, {})
        .get("batting_position", {})
    )
    if not position_record:
        return dict(probabilities)

    preferred = float(position_record.get("preferred", batting_position))
    spread = max(0.85, float(position_record.get("spread", 2.5)))
    effective_innings = max(
        0.0,
        float(position_record.get("effective_innings", 0.0)),
    )
    confidence = effective_innings / (effective_innings + 12.0)
    distance = abs(float(batting_position) - preferred)
    familiarity = float(np.exp(-0.5 * (distance / spread) ** 2))
    effectiveness = position_record.get("effectiveness", {}).get(
        str(int(batting_position)),
        {},
    )
    learned_run_multiplier = float(effectiveness.get("run_multiplier", 1.0))
    learned_wicket_multiplier = float(
        effectiveness.get("wicket_multiplier", 1.0)
    )
    strength = max(
        0.0,
        float(meta.get("batting_position_adjustment_strength", 1.0)),
    )
    run_multiplier = (
        learned_run_multiplier
        * (1.0 - 0.12 * confidence * (1.0 - familiarity))
    ) ** strength
    wicket_multiplier = (
        learned_wicket_multiplier
        * (1.0 + 0.15 * confidence * (1.0 - familiarity))
    ) ** strength

    adjusted = dict(probabilities)
    adjusted["0"] *= run_multiplier ** -0.55
    adjusted["1"] *= run_multiplier ** 0.30
    adjusted["2"] *= run_multiplier ** 0.70
    adjusted["3"] *= run_multiplier ** 0.70
    adjusted["4"] *= run_multiplier ** 1.05
    adjusted["6"] *= run_multiplier ** 1.25
    adjusted["W"] *= wicket_multiplier
    return normalise(adjusted)


def apply_simulation_calibration(
    probabilities: Dict[str, float],
    innings: int,
    meta: dict,
) -> Dict[str, float]:
    if innings != 2:
        return dict(probabilities)
    calibration = meta.get("simulation_calibration", {})
    scoring_multiplier = max(
        0.1,
        float(calibration.get("chase_scoring_multiplier", 1.0)),
    )
    wicket_multiplier = max(
        0.1,
        float(calibration.get("chase_wicket_multiplier", 1.0)),
    )
    adjusted = dict(probabilities)
    for outcome in ["1", "2", "3", "4", "6"]:
        adjusted[outcome] *= scoring_multiplier
    adjusted["W"] *= wicket_multiplier
    return normalise(adjusted)


def simulate_innings(team_name: str, opponent: str, batting_xi: List[str], bowling_xi: List[str], models:dict, meta:dict, model_name:str,
                     venue="Unknown", pitch="balanced", weather="clear", toss_decision="bat", innings=1, target:Optional[int]=None,
                     seed:Optional[int]=None, commentary=False, probability_cache: Optional[dict] = None,
                     selected_bowlers: Optional[List[str]] = None) -> dict:
    rng = np.random.default_rng(seed)
    priors = models.get("baseline_prior", {})
    batters = batting_xi[:]
    bowlers = resolve_bowling_options(bowling_xi, selected_bowlers, meta)
    batting_positions = {
        player: position
        for position, player in enumerate(batters, start=1)
    }

    striker, non_striker = batters[0], batters[1]
    used_batters = [striker, non_striker]
    bat = {p:{"R":0,"B":0,"4s":0,"6s":0,"out":"not out"} for p in batters}
    bowl = {p:{"O_balls":0,"R":0,"W":0,"WD":0,"NB":0} for p in bowlers}
    rows=[]; fow=[]; over_summary=[]
    state = {
        "innings": innings,
        "over": 0,
        "legal_ball": 1,
        "balls_bowled": 0,
        "runs": 0,
        "wickets": 0,
        "target": target or 0,
        "bat_runs": {},
        "bat_balls": {},
    }
    over = 0; prev_bowler=None; current_bowler=None; legal_in_over=0; free_hit=False
    over_runs=0; over_wkts=0; extra_seq=0

    while over < 20 and state["wickets"] < 10:
        if legal_in_over == 0:
            current_bowler, reason = choose_bowler(bowlers, meta, over, {k:v["O_balls"]//6 for k,v in bowl.items()}, prev_bowler)
            if current_bowler not in bowl: bowl[current_bowler] = {"O_balls":0,"R":0,"W":0,"WD":0,"NB":0}
            over_runs=0; over_wkts=0; extra_seq=0
        phase = phase_from_over(over)
        state.update({"over":over,"legal_ball":legal_in_over+1})
        delivery_batter = striker
        x = vector_input(state, delivery_batter, current_bowler, team_name, opponent, venue, toss_decision)
        cache_key = None
        if probability_cache is not None:
            row = x.iloc[0]
            cache_key = (
                model_name,
                innings,
                over,
                int(row["legal_ball"]),
                int(row["balls_bowled"]),
                int(row["balls_remaining"]),
                int(row["team_runs"]),
                int(row["team_wicket"]),
                int(row["target"]),
                int(row["runs_required"]),
                round(float(row["current_run_rate"]), 4),
                round(float(row["required_run_rate"]), 4),
                round(float(row["rate_pressure"]), 4),
                int(row["batter_runs"]),
                int(row["batter_balls"]),
                delivery_batter,
                current_bowler,
                str(row["venue"]),
                str(row["batting_team"]),
                str(row["bowling_team"]),
            )
        if cache_key is not None and cache_key in probability_cache:
            p = probability_cache[cache_key]
        else:
            p = model_probs(model_name, models, priors, x, delivery_batter, current_bowler, phase, meta)
            if cache_key is not None:
                probability_cache[cache_key] = p
        p = apply_match_context(
            p,
            innings=innings,
            runs=state["runs"],
            balls_bowled=state["balls_bowled"],
            target=target,
            learned_chase_context=int(meta.get("artifact_schema", 0)) >= 4,
        )
        p = apply_player_matchup(
            p,
            delivery_batter,
            current_bowler,
            meta,
        )
        p = apply_batting_position(
            p,
            delivery_batter,
            batting_positions.get(delivery_batter, 11),
            meta,
        )
        p = apply_simulation_calibration(p, innings, meta)
        out = rng.choice(OUTCOMES, p=[p[o] for o in OUTCOMES])
        if out == "W" and free_hit:
            out = "1" if rng.random() < 0.45 else "0"
        runs, bruns, wicket, extra_type, legal = outcome_to_runs(out, priors, rng)
        if free_hit and legal: free_hit=False
        if out == "NB": free_hit=True

        state["runs"] += runs; over_runs += runs
        if current_bowler in bowl:
            bowl[current_bowler]["R"] += runs if extra_type not in ["legbyes","byes"] else 0
            if out == "WD": bowl[current_bowler]["WD"] += 1
            if out == "NB": bowl[current_bowler]["NB"] += 1
        if bruns:
            bat[delivery_batter]["R"] += bruns
            if bruns == 4: bat[delivery_batter]["4s"] += 1
            if bruns == 6: bat[delivery_batter]["6s"] += 1
        if legal:
            bat[delivery_batter]["B"] += 1
            bowl[current_bowler]["O_balls"] += 1
            state["balls_bowled"] += 1
            state["bat_balls"][delivery_batter] = bat[delivery_batter]["B"]
            legal_in_over += 1
        state["bat_runs"][delivery_batter] = bat[delivery_batter]["R"]

        dismissed = ""
        dismissal = {"kind": "", "text": "", "fielder": "", "bowler_credit": False}
        if wicket:
            state["wickets"] += 1; over_wkts += 1
            dismissed = delivery_batter
            dismissal = sample_dismissal(bowling_xi, current_bowler, meta, rng)
            if dismissal["bowler_credit"]:
                bowl[current_bowler]["W"] += 1
            bat[delivery_batter]["out"] = dismissal["text"]
            fow.append({"wicket":state["wickets"], "score":state["runs"], "over":f"{over}.{legal_in_over}", "player":delivery_batter})
            nb = choose_next_batter(batters, used_batters, meta, phase, state["wickets"])
            if nb is None or state["wickets"] >= 10:
                pass
            else:
                striker = nb; used_batters.append(nb)

        if legal:
            label = f"{over}.{legal_in_over}"
        else:
            extra_seq += 1
            suffix = "wd" if out == "WD" else "nb"
            label = f"{over}.{legal_in_over+1}{suffix}{extra_seq}"
        comm = ""
        if commentary:
            if out == "W": comm = f"{current_bowler} strikes, {dismissed} is gone at a crucial stage."
            elif out == "6": comm = f"{delivery_batter} launches it for six."
            elif out == "4": comm = f"{delivery_batter} finds the boundary."
            elif out in ["WD","NB"]: comm = f"Extra conceded by {current_bowler}; the legal ball count stays unchanged."
            else: comm = f"{current_bowler} to {delivery_batter}, {runs} run{'s' if runs!=1 else ''}."
        rows.append({"ball":label,"over":over,"legal_ball_in_over":legal_in_over,"phase":phase,"bowler":current_bowler,"batter":delivery_batter,
                     "outcome":out,"runs":runs,"batter_runs":bruns,"extras":max(0,runs-bruns),"extra_type":extra_type,"wicket":wicket,
                     "dismissal_kind":dismissal["kind"],"dismissal":dismissal["text"],"fielder":dismissal["fielder"],
                     "score":state["runs"],"wickets":state["wickets"],"p_wicket":round(p["W"],4),"p_boundary":round(p["4"]+p["6"],4),
                     "p_extra":round(p["WD"]+p["NB"]+p["LB"]+p["B"],4),"bowler_reason": reason if legal_in_over<=1 else "", "commentary":comm})

        strike_runs = max(0, runs - 1) if out == "WD" else (bruns if out == "NB" else runs)
        if strike_runs % 2 == 1:
            striker, non_striker = rotate_strike(striker, non_striker)
        if legal_in_over == 6:
            over_summary.append({"over":over+1,"bowler":current_bowler,"runs":over_runs,"wickets":over_wkts,"score":f"{state['runs']}/{state['wickets']}"})
            striker, non_striker = rotate_strike(striker, non_striker)
            prev_bowler=current_bowler; current_bowler=None; legal_in_over=0; over += 1
        if target is not None and state["runs"] >= target:
            break

    def overs_str(balls): return f"{balls//6}.{balls%6}"
    batting_card = []
    for p in batters:
        r=bat[p]
        if r["B"] or r["R"] or p in used_batters:
            sr = 100*r["R"]/r["B"] if r["B"] else 0
            batting_card.append({"Batter":p,"Dismissal":r["out"],"R":r["R"],"B":r["B"],"4s":r["4s"],"6s":r["6s"],"SR":round(sr,1)})
    bowling_card = []
    for p,r in bowl.items():
        if r["O_balls"] or r["R"]:
            eco = 6*r["R"]/r["O_balls"] if r["O_balls"] else 0
            bowling_card.append({"Bowler":p,"O":overs_str(r["O_balls"]),"R":r["R"],"W":r["W"],"WD":r["WD"],"NB":r["NB"],"Econ":round(eco,2)})
    end_reason = "target reached" if target is not None and state["runs"] >= target else ("all out" if state["wickets"]>=10 else "20 overs completed")
    rules = {"no_bowler_over_4": all(v["O_balls"]<=24 for v in bowl.values()), "legal_balls_max_120": sum(v["O_balls"] for v in bowl.values())<=120, "wickets_max_10": state["wickets"]<=10}
    return {"team":team_name,"runs":state["runs"],"wickets":state["wickets"],"overs":overs_str(sum(v["O_balls"] for v in bowl.values())),"end_reason":end_reason,
            "batting_card":pd.DataFrame(batting_card),"bowling_card":pd.DataFrame(bowling_card),"fall_of_wickets":pd.DataFrame(fow),
            "ball_by_ball":pd.DataFrame(rows),"over_summary":pd.DataFrame(over_summary),"rules":rules,
            "bowling_options": bowlers}


def simulate_match(team1, team2, xi1, xi2, models, meta, model_name, venue, pitch, weather, toss_winner, toss_decision, seed=None, commentary=False, probability_cache=None,
                   bowlers1: Optional[List[str]] = None, bowlers2: Optional[List[str]] = None):
    # toss decides batting order
    if toss_decision == "bat":
        bat_first = toss_winner
    else:
        bat_first = team2 if toss_winner == team1 else team1
    if bat_first == team1:
        first = simulate_innings(team1, team2, xi1, xi2, models, meta, model_name, venue,pitch,weather,toss_decision,1,None,seed,commentary,probability_cache,bowlers2)
        second = simulate_innings(team2, team1, xi2, xi1, models, meta, model_name, venue,pitch,weather,toss_decision,2,first["runs"]+1,None if seed is None else seed+1,commentary,probability_cache,bowlers1)
    else:
        first = simulate_innings(team2, team1, xi2, xi1, models, meta, model_name, venue,pitch,weather,toss_decision,1,None,seed,commentary,probability_cache,bowlers1)
        second = simulate_innings(team1, team2, xi1, xi2, models, meta, model_name, venue,pitch,weather,toss_decision,2,first["runs"]+1,None if seed is None else seed+1,commentary,probability_cache,bowlers2)
    if second["runs"] >= first["runs"]+1:
        winner = second["team"]; margin = f"by {10-second['wickets']} wickets"
    elif first["runs"] > second["runs"]:
        winner = first["team"]; margin = f"by {first['runs']-second['runs']} runs"
    else:
        winner = "Tie"; margin = "scores level"
    return {"first":first,"second":second,"winner":winner,"margin":margin}


def simulate_distribution(n, *args, **kwargs):
    rows=[]
    base_seed = kwargs.pop("seed", None)
    probability_cache = {}
    for i in range(n):
        simulation_seed = None if base_seed is None else base_seed+i
        res = simulate_match(
            *args,
            seed=simulation_seed,
            commentary=False,
            probability_cache=probability_cache,
            **kwargs,
        )
        rows.append({
            "sim": i + 1,
            "seed": simulation_seed,
            "winner": res["winner"],
            "first_team": res["first"]["team"],
            "second_team": res["second"]["team"],
            "first_runs": res["first"]["runs"],
            "second_runs": res["second"]["runs"],
            "first_wickets": res["first"]["wickets"],
            "second_wickets": res["second"]["wickets"],
        })
    return pd.DataFrame(rows)


def representative_seed(distribution: pd.DataFrame) -> Optional[int]:
    if distribution.empty or "seed" not in distribution or distribution["seed"].isna().all():
        return None
    winner_counts = distribution["winner"].value_counts()
    modal_winner = str(winner_counts.index[0])
    candidates = distribution[distribution["winner"].eq(modal_winner)].copy()
    centers = candidates[["first_runs", "second_runs"]].median()
    scales = candidates[["first_runs", "second_runs"]].std().replace(0, 1).fillna(1)
    candidates["_representative_distance"] = (
        ((candidates[["first_runs", "second_runs"]] - centers) / scales) ** 2
    ).sum(axis=1)
    return int(
        candidates.sort_values(
            ["_representative_distance", "sim"],
            kind="stable",
        ).iloc[0]["seed"]
    )
    
