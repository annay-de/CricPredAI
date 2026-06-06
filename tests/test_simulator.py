from __future__ import annotations

import numpy as np
import pandas as pd

from simulator import (
    apply_player_matchup,
    apply_simulation_calibration,
    available_profiles,
    load_artifacts,
    outcome_to_runs,
    representative_seed,
    sample_dismissal,
    vector_input,
)


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


def test_ordinary_catch_uses_a_non_bowler_fielder():
    dismissal = sample_dismissal(
        ["Bowler", "Fielder"],
        "Bowler",
        {
            "dismissal_probabilities": {"caught": 1.0},
            "fielding": {"Fielder": {"catches": 20}},
        },
        np.random.default_rng(2),
    )

    assert dismissal["kind"] == "caught"
    assert dismissal["fielder"] == "Fielder"
    assert dismissal["text"] == "c Fielder b Bowler"
    assert dismissal["bowler_credit"] is True


def test_run_out_does_not_credit_the_bowler():
    dismissal = sample_dismissal(
        ["Bowler", "Fielder"],
        "Bowler",
        {"dismissal_probabilities": {"run_out": 1.0}},
        np.random.default_rng(3),
    )

    assert dismissal["kind"] == "run_out"
    assert dismissal["text"] == "run out (Fielder)"
    assert dismissal["bowler_credit"] is False


def test_player_matchup_separates_strong_and_weak_players():
    base = {
        "0": 0.30,
        "1": 0.36,
        "2": 0.06,
        "3": 0.01,
        "4": 0.12,
        "6": 0.06,
        "W": 0.05,
        "WD": 0.02,
        "NB": 0.005,
        "LB": 0.01,
        "B": 0.005,
    }
    meta = {
        "matchup_adjustment_strength": 1.0,
        "player_rate_baselines": {
            "bat_runs_per_ball": 1.35,
            "dismissal_rate": 0.05,
            "bowl_runs_per_ball": 1.40,
            "wicket_rate": 0.05,
        },
        "roles": {
            "Strong batter": {
                "bat_runs_per_ball": 1.65,
                "dismissal_rate": 0.045,
            },
            "Weak batter": {
                "bat_runs_per_ball": 1.10,
                "dismissal_rate": 0.075,
            },
            "Strong bowler": {
                "bowl_runs_per_ball": 1.15,
                "wicket_rate": 0.065,
            },
            "Weak bowler": {
                "bowl_runs_per_ball": 1.65,
                "wicket_rate": 0.035,
            },
        },
    }

    favorable = apply_player_matchup(base, "Strong batter", "Weak bowler", meta)
    unfavorable = apply_player_matchup(base, "Weak batter", "Strong bowler", meta)
    favorable_runs = sum(favorable[str(run)] * run for run in [1, 2, 3, 4, 6])
    unfavorable_runs = sum(unfavorable[str(run)] * run for run in [1, 2, 3, 4, 6])

    assert favorable_runs > unfavorable_runs
    assert favorable["W"] < unfavorable["W"]


def test_chase_calibration_adds_failure_cost_without_team_bias():
    base = {
        "0": 0.30,
        "1": 0.36,
        "2": 0.06,
        "3": 0.01,
        "4": 0.12,
        "6": 0.06,
        "W": 0.05,
        "WD": 0.02,
        "NB": 0.005,
        "LB": 0.01,
        "B": 0.005,
    }
    meta = {
        "simulation_calibration": {
            "chase_scoring_multiplier": 0.976,
            "chase_wicket_multiplier": 1.05,
        }
    }

    first = apply_simulation_calibration(base, 1, meta)
    chase = apply_simulation_calibration(base, 2, meta)

    assert first == base
    assert chase["W"] > base["W"]
    assert sum(chase[str(run)] * run for run in [1, 2, 3, 4, 6]) < sum(
        base[str(run)] * run for run in [1, 2, 3, 4, 6]
    )


def test_representative_scorecard_seed_comes_from_modal_outcome():
    distribution = pd.DataFrame(
        [
            {"sim": 1, "seed": 1001, "winner": "Strong", "first_runs": 190, "second_runs": 150},
            {"sim": 2, "seed": 1002, "winner": "Strong", "first_runs": 180, "second_runs": 160},
            {"sim": 3, "seed": 1003, "winner": "Strong", "first_runs": 200, "second_runs": 140},
            {"sim": 4, "seed": 1004, "winner": "Weak", "first_runs": 150, "second_runs": 151},
        ]
    )

    assert representative_seed(distribution) == 1001
