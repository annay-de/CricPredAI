from __future__ import annotations

import numpy as np
import pandas as pd

from simulator import (
    apply_batting_position,
    apply_player_matchup,
    apply_simulation_calibration,
    available_profiles,
    choose_bowler,
    choose_next_batter,
    load_artifacts,
    outcome_to_runs,
    representative_seed,
    resolve_bowling_options,
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


def test_submitted_batting_order_is_followed_exactly():
    order = ["Opener", "Anchor", "Finisher", "Bowler"]

    assert choose_next_batter(order, ["Opener"], {}, "powerplay", 1) == "Anchor"
    assert (
        choose_next_batter(
            order,
            ["Opener", "Anchor"],
            {"roles": {"Finisher": {"batting_score": -10}}},
            "death",
            2,
        )
        == "Finisher"
    )


def test_batter_is_more_effective_near_learned_position():
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
        "batting_position_adjustment_strength": 1.0,
        "roles": {
            "Anchor": {
                "batting_position": {
                    "preferred": 3.0,
                    "spread": 1.0,
                    "effective_innings": 80.0,
                    "effectiveness": {
                        "3": {
                            "run_multiplier": 1.05,
                            "wicket_multiplier": 0.95,
                        }
                    },
                }
            }
        },
    }

    proper = apply_batting_position(base, "Anchor", 3, meta)
    misplaced = apply_batting_position(base, "Anchor", 9, meta)
    proper_runs = sum(proper[str(run)] * run for run in [1, 2, 3, 4, 6])
    misplaced_runs = sum(misplaced[str(run)] * run for run in [1, 2, 3, 4, 6])

    assert proper_runs > misplaced_runs
    assert proper["W"] < misplaced["W"]


def test_bowling_selection_uses_learned_phase_role():
    meta = {
        "bowling_phase_selection_strength": 1.0,
        "roles": {
            "New-ball specialist": {
                "role": "bowler",
                "bowling_score": 0.0,
                "effective_bowl_balls": 600,
                "bowling_phases": {
                    "powerplay": {"selection_score": 1.2, "balls": 360},
                    "death": {"selection_score": -0.8, "balls": 30},
                },
            },
            "Death specialist": {
                "role": "bowler",
                "bowling_score": 0.0,
                "effective_bowl_balls": 600,
                "bowling_phases": {
                    "powerplay": {"selection_score": -0.8, "balls": 30},
                    "death": {"selection_score": 1.2, "balls": 360},
                },
            },
        },
    }
    bowlers = ["New-ball specialist", "Death specialist"]

    powerplay, _ = choose_bowler(bowlers, meta, 0, {}, None)
    death, _ = choose_bowler(bowlers, meta, 18, {}, None)

    assert powerplay == "New-ball specialist"
    assert death == "Death specialist"


def test_allocator_reserves_capacity_for_a_death_specialist():
    meta = {
        "bowling_phase_selection_strength": 1.0,
        "roles": {
            "Death specialist": {
                "role": "bowler",
                "effective_bowl_balls": 500,
                "bowling_phases": {
                    "middle": {
                        "selection_score": 0.9,
                        "usage_share": 0.30,
                    },
                    "death": {
                        "selection_score": 1.2,
                        "usage_share": 0.60,
                    },
                },
            },
            "Middle specialist": {
                "role": "bowler",
                "effective_bowl_balls": 500,
                "bowling_phases": {
                    "middle": {
                        "selection_score": 0.6,
                        "usage_share": 0.80,
                    },
                    "death": {
                        "selection_score": -0.5,
                        "usage_share": 0.05,
                    },
                },
            },
        },
    }

    chosen, _ = choose_bowler(
        ["Death specialist", "Middle specialist"],
        meta,
        over=12,
        bowler_overs={"Death specialist": 1, "Middle specialist": 0},
        prev_bowler=None,
    )

    assert chosen == "Middle specialist"


def test_explicit_bowling_options_are_honored_and_require_five():
    xi = [f"Player {index}" for index in range(1, 12)]
    selected = xi[3:8]

    assert resolve_bowling_options(xi, selected, {}) == selected

    try:
        resolve_bowling_options(xi, xi[:4], {})
    except ValueError as exc:
        assert "At least five" in str(exc)
    else:
        raise AssertionError("Four explicit bowling options should be rejected.")
