from __future__ import annotations

import numpy as np

from simulator import available_profiles, load_artifacts, outcome_to_runs, vector_input


def test_chase_features_are_visible_to_the_model():
    frame = vector_input(
        {
            "innings": 2,
            "over": 10,
            "legal_ball": 1,
            "balls_bowled": 60,
            "runs": 80,
            "wickets": 3,
            "target": 181,
            "bat_runs": {"Batter": 30},
            "bat_balls": {"Batter": 22},
        },
        "Batter",
        "Bowler",
        "Team A",
        "Team B",
        "Eden Gardens, Kolkata",
        "field",
    ).iloc[0]

    assert frame["balls_remaining"] == 60
    assert frame["runs_required"] == 101
    assert frame["required_run_rate"] == 10.1
    assert frame["current_run_rate"] == 8.0
    assert round(frame["rate_pressure"], 1) == 2.1
    assert frame["venue"] == "Eden Gardens"


def test_free_hit_suppresses_a_wicket():
    runs, batter_runs, wicket, extra_type, legal = outcome_to_runs(
        "W",
        {},
        np.random.default_rng(1),
        free_hit=True,
    )
    assert wicket is False
    assert legal is True
    assert runs in {0, 1}
    assert batter_runs == runs
    assert extra_type == ""


def test_modern_and_lifetime_profiles_are_independent():
    assert set(available_profiles()) >= {"modern", "lifetime"}
    modern_meta, _, modern_models = load_artifacts("modern")
    lifetime_meta, _, lifetime_models = load_artifacts("lifetime")

    assert modern_meta["profile"] == "modern"
    assert modern_meta["recency_weight_half_life_years"] == 5.0
    assert lifetime_meta["profile"] == "lifetime"
    assert lifetime_meta["equal_weight_lifetime_data"] is True
    assert {"baseline_prior", "sgd_logistic", "xgboost"} <= set(modern_models)
    assert {"baseline_prior", "sgd_logistic", "xgboost"} <= set(lifetime_models)
    assert (
        modern_meta["roles"]["SR Tendulkar"]["effective_bat_balls"]
        < lifetime_meta["roles"]["SR Tendulkar"]["effective_bat_balls"]
    )
