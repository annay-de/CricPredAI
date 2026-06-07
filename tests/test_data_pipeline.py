from __future__ import annotations

import pandas as pd

from data_pipeline import canonicalize_venue, prepare_deliveries
from train_models import recency_weights


def test_venue_aliases_collapse_to_one_ground():
    aliases = [
        "Eden Gardens",
        "eden gardens",
        "Eden Gardens, Kolkata",
    ]
    assert {canonicalize_venue(value) for value in aliases} == {"Eden Gardens"}


def test_training_features_are_pre_delivery_state():
    raw = pd.DataFrame(
        [
            {
                "match_id": 1,
                "date": "2026-01-01",
                "match_type": "T20",
                "innings": 1,
                "batting_team": "A",
                "bowling_team": "B",
                "over": 0,
                "ball": 1,
                "batter": "Batter",
                "bowler": "Bowler",
                "runs_batter": 4,
                "runs_total": 4,
                "runs_extras": 0,
                "runs_bowler": 4,
                "valid_ball": 1,
                "venue": "Eden Gardens, Kolkata",
            },
            {
                "match_id": 1,
                "date": "2026-01-01",
                "match_type": "T20",
                "innings": 1,
                "batting_team": "A",
                "bowling_team": "B",
                "over": 0,
                "ball": 2,
                "batter": "Batter",
                "bowler": "Bowler",
                "runs_batter": 1,
                "runs_total": 1,
                "runs_extras": 0,
                "runs_bowler": 1,
                "valid_ball": 1,
                "venue": "Eden Gardens",
            },
        ]
    )

    prepared = prepare_deliveries(raw)
    first = prepared.iloc[0]
    second = prepared.iloc[1]
    assert first["team_runs"] == 0
    assert first["batter_runs"] == 0
    assert first["batter_balls"] == 0
    assert first["balls_bowled"] == 0
    assert second["team_runs"] == 4
    assert second["batter_runs"] == 4
    assert second["batter_balls"] == 1
    assert second["balls_bowled"] == 1
    assert prepared["venue"].nunique() == 1


def test_recency_weights_favor_new_seasons():
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2008-01-01", "2021-01-01", "2026-01-01"])}
    )
    weights = recency_weights(frame, pd.Timestamp("2026-01-01"))
    assert weights[0] < weights[1] < weights[2]
    assert weights[2] == 1.0


def test_batting_position_uses_first_appearance_including_non_striker():
    base = {
        "match_id": 1,
        "date": "2026-01-01",
        "match_type": "T20",
        "innings": 1,
        "batting_team": "A",
        "bowling_team": "B",
        "over": 0,
        "bowler": "Bowler",
        "runs_batter": 0,
        "runs_total": 0,
        "runs_extras": 0,
        "runs_bowler": 0,
        "valid_ball": 1,
        "venue": "Eden Gardens",
    }
    raw = pd.DataFrame(
        [
            {
                **base,
                "ball": 1,
                "batter": "Opening striker",
                "non_striker": "Opening partner",
            },
            {
                **base,
                "ball": 2,
                "batter": "Number three",
                "non_striker": "Opening partner",
            },
        ]
    )

    prepared = prepare_deliveries(raw)

    assert prepared.iloc[0]["bat_pos"] == 1
    assert prepared.iloc[1]["bat_pos"] == 3
