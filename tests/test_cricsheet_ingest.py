import pandas as pd

from cricsheet_ingest import CSV_COLUMNS, parse_match
from data_pipeline import prepare_deliveries


def _t20_match() -> dict:
    return {
        "info": {
            "gender": "male",
            "match_type": "T20",
            "balls_per_over": 6,
            "overs": 20,
            "teams": ["Karachi Kings", "Lahore Qalandars"],
            "dates": ["2024-02-19"],
            "venue": "National Stadium",
            "city": "Karachi",
            "toss": {"winner": "Karachi Kings", "decision": "bat"},
            "event": {"name": "Pakistan Super League"},
        },
        "innings": [
            {
                "team": "Karachi Kings",
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            {"batter": "A One", "bowler": "B One", "non_striker": "A Two",
                             "runs": {"batter": 1, "extras": 0, "total": 1}},
                            {"batter": "A Two", "bowler": "B One", "non_striker": "A One",
                             "runs": {"batter": 4, "extras": 0, "total": 4}},
                            {"batter": "A Two", "bowler": "B One", "non_striker": "A One",
                             "extras": {"wides": 1},
                             "runs": {"batter": 0, "extras": 1, "total": 1}},
                            {"batter": "A Two", "bowler": "B One", "non_striker": "A One",
                             "extras": {"legbyes": 2},
                             "runs": {"batter": 0, "extras": 2, "total": 2}},
                            {"batter": "A Two", "bowler": "B One", "non_striker": "A One",
                             "runs": {"batter": 0, "extras": 0, "total": 0},
                             "wickets": [{"kind": "caught", "player_out": "A Two",
                                          "fielders": [{"name": "C Fielder"}]}]},
                            {"batter": "A Three", "bowler": "B One", "non_striker": "A One",
                             "extras": {"noballs": 1},
                             "runs": {"batter": 2, "extras": 1, "total": 3}},
                            {"batter": "A Three", "bowler": "B One", "non_striker": "A One",
                             "runs": {"batter": 6, "extras": 0, "total": 6}},
                        ],
                    }
                ],
            },
            {
                "team": "Lahore Qalandars",
                "target": {"overs": 20, "runs": 18},
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            {"batter": "L One", "bowler": "K One", "non_striker": "L Two",
                             "runs": {"batter": 0, "extras": 0, "total": 0}},
                            {"batter": "L One", "bowler": "K One", "non_striker": "L Two",
                             "runs": {"batter": 2, "extras": 0, "total": 2}},
                        ],
                    }
                ],
            },
            {"team": "Karachi Kings", "super_over": True, "overs": []},
        ],
    }


def test_parse_match_rows_and_semantics():
    rows = parse_match(_t20_match(), "psl_test1")
    assert len(rows) == 9  # super over skipped
    frame = pd.DataFrame(rows, columns=CSV_COLUMNS)

    first = frame[frame["innings"] == 1]
    assert list(first["valid_ball"]) == [1, 1, 0, 1, 1, 0, 1]
    assert list(first["extra_type"]) == ["", "", "wides", "legbyes", "", "noballs", ""]
    # bowler concedes total minus byes/legbyes/penalty
    assert list(first["runs_bowler"]) == [1, 4, 1, 0, 0, 3, 6]
    wicket_row = first.iloc[4]
    assert wicket_row["wicket_kind"] == "caught"
    assert wicket_row["player_out"] == "A Two"
    assert wicket_row["fielders_involved"] == "['C Fielder']"
    assert first["runs_target"].isna().all()

    second = frame[frame["innings"] == 2]
    assert (second["runs_target"] == 18).all()
    assert (second["bowling_team"] == "Karachi Kings").all()
    assert (frame["match_type"] == "T20").all()


def test_parse_match_filters_out_of_scope():
    match = _t20_match()
    match["info"]["gender"] = "female"
    assert parse_match(match, "x") == []
    assert len(parse_match(match, "x", gender="all")) == 9

    hundred = _t20_match()
    hundred["info"]["balls_per_over"] = 5
    assert parse_match(hundred, "x") == []

    odi = _t20_match()
    odi["info"]["match_type"] = "ODI"
    assert parse_match(odi, "x") == []


def test_ingested_rows_flow_through_the_real_pipeline():
    """The critical contract: ingested rows must be accepted verbatim by
    data_pipeline.prepare_deliveries and produce correct outcome labels."""
    rows = parse_match(_t20_match(), "psl_test1")
    prepared = prepare_deliveries(pd.DataFrame(rows, columns=CSV_COLUMNS))

    first = prepared[prepared["innings"] == 1].sort_values("_row_order")
    assert list(first["outcome"]) == ["1", "4", "WD", "LB", "W", "NB", "6"]
    assert int(first["_wicket"].sum()) == 1
    assert int(first["_bowler_wicket"].sum()) == 1
    # batting positions assigned from appearance order (batter + non-striker)
    positions = first.groupby("batter")["bat_pos"].first()
    assert positions["A One"] == 1 and positions["A Two"] == 2 and positions["A Three"] == 3
    # chase features see the target
    second = prepared[prepared["innings"] == 2]
    assert (pd.to_numeric(second["runs_target"]) == 18).all()
