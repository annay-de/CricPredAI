import json
from pathlib import Path

import pytest

from scout import (
    _career_row,
    career_summary,
    merge_into_meta,
    profile_from_career,
    profile_from_statsguru,
)

META_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "profiles" / "modern" / "metadata.json"


@pytest.fixture(scope="module")
def meta():
    with META_PATH.open() as fh:
        return json.load(fh)


STATSGURU_BATTING = """
<table class="engineTable">
<tr><th>Mat</th><th>Inns</th><th>NO</th><th>Runs</th><th>HS</th><th>Ave</th><th>BF</th><th>SR</th></tr>
<tr class="data1"><td>415</td><td>399</td><td>69</td><td>12993</td><td>122*</td><td>39.37</td><td>9603</td><td>135.30</td></tr>
</table>
"""

STATSGURU_BOWLING = """
<table class="engineTable">
<tr><th>Mat</th><th>Inns</th><th>Balls</th><th>Runs</th><th>Wkts</th><th>BBI</th><th>Ave</th><th>Econ</th></tr>
<tr class="data1"><td>415</td><td>13</td><td>152</td><td>198</td><td>4</td><td>2/25</td><td>49.50</td><td>7.81</td></tr>
</table>
"""


def test_statsguru_parser_batting():
    row = _career_row(
        STATSGURU_BATTING,
        {"matches": "mat", "innings": "inns", "not_outs": "no", "runs": "runs", "balls": "bf", "strike_rate": "sr"},
    )
    assert row == {
        "matches": 415.0,
        "innings": 399.0,
        "not_outs": 69.0,
        "runs": 12993.0,
        "balls": 9603.0,
        "strike_rate": 135.30,
    }


def test_statsguru_parser_bowling_and_summary():
    row = _career_row(
        STATSGURU_BOWLING,
        {"matches": "mat", "balls": "balls", "runs": "runs", "wickets": "wkts", "economy": "econ"},
    )
    assert row["wickets"] == 4.0 and row["balls"] == 152.0
    summary = career_summary({"batting": None, "bowling": row})
    assert "4 wkts" in summary


def test_profile_shrinks_toward_baseline_at_low_trust(meta):
    hot = dict(
        name="Hot Batter",
        meta=meta,
        bat_innings=300,
        bat_runs=9000,
        bat_balls=5000,   # career 1.8 rpb, elite
        bat_outs=200,
    )
    low = profile_from_career(**hot, trust=0.1)
    high = profile_from_career(**hot, trust=1.0)
    baseline = meta["player_rate_baselines"]["bat_runs_per_ball"]
    assert baseline < low["bat_runs_per_ball"] < high["bat_runs_per_ball"] < 1.8
    # matchup clamp range in the engine is 0.72..1.35 of baseline; profile stays sane
    assert high["bat_runs_per_ball"] / baseline < 1.5


def test_role_classification(meta):
    bowler = profile_from_career(
        name="Pure Bowler", meta=meta, bowl_balls=2000, bowl_runs=2400, bowl_wickets=110,
        bat_innings=30, bat_runs=120, bat_balls=150, bat_outs=25, bowler_type="pace", trust=0.8,
    )
    assert bowler["role"] == "bowler"
    assert bowler["bowling_phases"]["death"]["usage_share"] > bowler["bowling_phases"]["middle"]["usage_share"] * 0.4
    batter = profile_from_career(
        name="Pure Batter", meta=meta, bat_innings=200, bat_runs=6000, bat_balls=4200, bat_outs=170,
    )
    assert batter["role"] == "batter"
    for phase in ["powerplay", "middle", "death"]:
        assert 0 < bowler["bowling_phases"][phase]["runs_per_ball"] < 3
        assert 0 < bowler["bowling_phases"][phase]["wicket_rate"] < 0.5


def test_profile_from_statsguru_estimates_missing_balls(meta):
    career = {
        "batting": {"matches": 100, "innings": 90, "not_outs": 10, "runs": 2700, "balls": None, "strike_rate": 150.0},
        "bowling": {},
    }
    profile = profile_from_statsguru(
        name="No BF", meta=meta, career=career, preferred_position=3, bowler_type="none", trust=0.5,
    )
    assert profile["bat_balls"] == 1800  # 2700 / 1.5
    assert profile["batting_position"]["preferred"] == 3.0


def test_merge_into_meta_does_not_mutate_ipl_meta(meta):
    profile = profile_from_career(name="Ghost", meta=meta, bat_innings=50, bat_runs=1500, bat_balls=1000, bat_outs=40)
    roster = {"Ghost Player": {"profile": profile}}
    before_players = len(meta["players"])
    before_roles = len(meta["roles"])
    merged = merge_into_meta(meta, roster)
    assert "Ghost Player" in merged["players"] and "Ghost Player" in merged["roles"]
    assert len(meta["players"]) == before_players and len(meta["roles"]) == before_roles
    assert merged is not meta


def test_scouted_player_simulates_end_to_end(meta):
    """The critical guarantee: an engine that has never seen a player can
    still simulate them through the merged-metadata view."""
    from simulator import load_artifacts, simulate_match

    meta_l, _, models = load_artifacts("modern")
    profile = profile_from_career(
        name="Scout Test Legend",
        meta=meta_l,
        bat_innings=250, bat_runs=8000, bat_balls=5200, bat_outs=210,
        bowl_balls=300, bowl_runs=380, bowl_wickets=12,
        preferred_position=3, bowler_type="none", trust=0.6,
    )
    merged = merge_into_meta(meta_l, {"Scout Test Legend": {"profile": profile}})
    players = meta_l["players"]
    xi_a = ["Scout Test Legend"] + players[:10]
    xi_b = players[10:21]
    result = simulate_match(
        "Scout XI", "Control XI", xi_a, xi_b, models, merged, "xgboost",
        "Eden Gardens", "data-driven", "data-driven", "Scout XI", "bat", seed=7,
    )
    assert result["first"]["runs"] > 0 and result["second"]["runs"] >= 0
    batted = set(result["first"]["batting_card"]["Batter"]) | set(result["second"]["batting_card"]["Batter"])
    assert "Scout Test Legend" in batted
