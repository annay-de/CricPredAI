from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from data_pipeline import OUTCOMES


def normalize_array(values) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    array = np.clip(array, 1e-12, None)
    return array / array.sum(axis=-1, keepdims=True)


def normalize_dict(values: Mapping[str, float]) -> dict[str, float]:
    array = normalize_array([values.get(outcome, 0.0) for outcome in OUTCOMES])
    return {outcome: float(array[index]) for index, outcome in enumerate(OUTCOMES)}


def _entry(entry, fallback: np.ndarray) -> tuple[np.ndarray, int]:
    if not isinstance(entry, Mapping):
        return fallback, 0
    probabilities = entry.get("p", entry)
    if not isinstance(probabilities, Mapping):
        return fallback, 0
    array = normalize_array([probabilities.get(outcome, 0.0) for outcome in OUTCOMES])
    return array, int(entry.get("n", 0))


def empirical_array(
    priors: Mapping,
    *,
    batter: str,
    bowler: str,
    phase: str,
    innings: int = 1,
    venue: str = "Unknown",
    batting_team: str = "Unknown",
    bowling_team: str = "Unknown",
) -> np.ndarray:
    global_array, _ = _entry(priors.get("global", {}), np.ones(len(OUTCOMES)))
    result = global_array
    contexts = [
        ("phase", phase, 400),
        ("innings_phase", f"{innings}||{phase}", 500),
        ("venue_phase", f"{venue}||{phase}", 350),
        ("batting_team_phase", f"{batting_team}||{phase}", 450),
        ("bowling_team_phase", f"{bowling_team}||{phase}", 450),
        ("batter_phase", f"{batter}||{phase}", 100),
        ("bowler_phase", f"{bowler}||{phase}", 120),
    ]
    for group_name, key, shrinkage in contexts:
        context_array, sample_size = _entry(priors.get(group_name, {}).get(key), result)
        if sample_size <= 0:
            continue
        weight = sample_size / (sample_size + shrinkage)
        result = (1.0 - weight) * result + weight * context_array
    return normalize_array(result)


def empirical_matrix(priors: Mapping, frame: pd.DataFrame) -> np.ndarray:
    rows = []
    for row in frame.itertuples(index=False):
        rows.append(
            empirical_array(
                priors,
                batter=str(getattr(row, "batter", "Unknown")),
                bowler=str(getattr(row, "bowler", "Unknown")),
                phase=str(getattr(row, "phase", "middle")),
                innings=int(getattr(row, "innings", 1)),
                venue=str(getattr(row, "venue", "Unknown")),
                batting_team=str(getattr(row, "batting_team", "Unknown")),
                bowling_team=str(getattr(row, "bowling_team", "Unknown")),
            )
        )
    return np.vstack(rows)


def calibrated_blend(
    model_probabilities: np.ndarray,
    empirical_probabilities: np.ndarray,
    *,
    model_weight: float,
    temperature: float,
) -> np.ndarray:
    model_probabilities = normalize_array(model_probabilities)
    empirical_probabilities = normalize_array(empirical_probabilities)
    blended = (
        float(model_weight) * model_probabilities
        + (1.0 - float(model_weight)) * empirical_probabilities
    )
    logits = np.log(np.clip(blended, 1e-12, 1.0)) / max(float(temperature), 1e-3)
    logits -= logits.max(axis=1, keepdims=True)
    return normalize_array(np.exp(logits))
