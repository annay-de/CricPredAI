from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

OUTCOMES = ["0", "1", "2", "3", "4", "6", "W", "WD", "NB", "LB", "B"]

NUM_FEATURES = [
    "innings",
    "over",
    "legal_ball",
    "balls_bowled",
    "balls_remaining",
    "team_runs",
    "team_wicket",
    "wickets_remaining",
    "current_run_rate",
    "batter_runs",
    "batter_balls",
    "batter_strike_rate",
    "target",
    "runs_required",
    "required_run_rate",
    "rate_pressure",
]
CAT_FEATURES = [
    "phase",
    "batting_team",
    "bowling_team",
    "batter",
    "bowler",
    "venue",
    "toss_decision",
]
FEATURES = NUM_FEATURES + CAT_FEATURES

_CITY_SUFFIXES = {
    "ahmedabad",
    "abu dhabi",
    "bengaluru",
    "bangalore",
    "chandigarh",
    "chennai",
    "delhi",
    "dharamsala",
    "guwahati",
    "hyderabad",
    "jaipur",
    "kolkata",
    "lucknow",
    "mohali",
    "mullanpur",
    "mumbai",
    "new chandigarh",
    "pune",
    "uppal",
    "visakhapatnam",
}

TEAM_ALIASES = {
    "delhi daredevils": "Delhi Capitals",
    "delhi capitals": "Delhi Capitals",
    "kings xi punjab": "Punjab Kings",
    "punjab kings": "Punjab Kings",
    "royal challengers bangalore": "Royal Challengers Bengaluru",
    "royal challengers bengaluru": "Royal Challengers Bengaluru",
}

VENUE_ALIASES = {
    "arun jaitley stadium": "Arun Jaitley Stadium",
    "feroz shah kotla": "Arun Jaitley Stadium",
    "barabati stadium": "Barabati Stadium",
    "barsapara cricket stadium": "Barsapara Cricket Stadium",
    "bharat ratna shri atal bihari vajpayee ekana cricket stadium": "Ekana Cricket Stadium",
    "ekana cricket stadium": "Ekana Cricket Stadium",
    "brabourne stadium": "Brabourne Stadium",
    "dr dy patil sports academy": "Dr DY Patil Sports Academy",
    "dr d y patil sports academy": "Dr DY Patil Sports Academy",
    "dr ys rajasekhara reddy aca vdca cricket stadium": "ACA-VDCA Cricket Stadium",
    "aca vdca cricket stadium": "ACA-VDCA Cricket Stadium",
    "dubai international cricket stadium": "Dubai International Cricket Stadium",
    "eden gardens": "Eden Gardens",
    "green park": "Green Park",
    "himachal pradesh cricket association stadium": "HPCA Stadium",
    "hpca stadium": "HPCA Stadium",
    "holkar cricket stadium": "Holkar Cricket Stadium",
    "jsca international stadium complex": "JSCA International Stadium Complex",
    "m chinnaswamy stadium": "M Chinnaswamy Stadium",
    "mchinnaswamy stadium": "M Chinnaswamy Stadium",
    "ma chidambaram stadium": "MA Chidambaram Stadium",
    "ma chidambaram stadium chepauk": "MA Chidambaram Stadium",
    "maharaja yadavindra singh international cricket stadium": "Mullanpur Cricket Stadium",
    "mullanpur cricket stadium": "Mullanpur Cricket Stadium",
    "maharashtra cricket association stadium": "Maharashtra Cricket Association Stadium",
    "narendra modi stadium": "Narendra Modi Stadium",
    "sardar patel stadium motera": "Narendra Modi Stadium",
    "nehru stadium": "Nehru Stadium",
    "punjab cricket association is bindra stadium": "PCA IS Bindra Stadium",
    "punjab cricket association stadium": "PCA IS Bindra Stadium",
    "pca is bindra stadium": "PCA IS Bindra Stadium",
    "rajiv gandhi international stadium": "Rajiv Gandhi International Stadium",
    "rajiv gandhi international stadium uppal": "Rajiv Gandhi International Stadium",
    "saurashtra cricket association stadium": "Saurashtra Cricket Association Stadium",
    "sawai mansingh stadium": "Sawai Mansingh Stadium",
    "shaheed veer narayan singh international stadium": "Shaheed Veer Narayan Singh International Stadium",
    "sharjah cricket stadium": "Sharjah Cricket Stadium",
    "sheikh zayed stadium": "Zayed Cricket Stadium",
    "zayed cricket stadium": "Zayed Cricket Stadium",
    "subrata roy sahara stadium": "Maharashtra Cricket Association Stadium",
    "vidarbha cricket association stadium jamtha": "VCA Stadium, Jamtha",
    "wankhede stadium": "Wankhede Stadium",
}

NON_DISMISSAL_WICKETS = {"retired hurt", "retired not out"}


def _key(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def canonicalize_team(value: object) -> str:
    key = _key(value)
    if not key:
        return "Unknown"
    return TEAM_ALIASES.get(key, re.sub(r"\s+", " ", str(value)).strip())


def parse_fielders(value: object) -> list[str]:
    if value is None or (not isinstance(value, (list, tuple, set)) and pd.isna(value)):
        return []
    parsed = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            parsed = [part.strip() for part in text.split(",")]
    if not isinstance(parsed, (list, tuple, set)):
        parsed = [parsed]
    fielders = []
    for player in parsed:
        if player is None or pd.isna(player):
            continue
        name = str(player).strip()
        if name and name.lower() not in {"none", "nan", "unknown"}:
            fielders.append(name)
    return fielders


def canonicalize_venue(value: object, city: object = None) -> str:
    key = _key(value)
    if not key:
        return "Unknown"
    if key in VENUE_ALIASES:
        return VENUE_ALIASES[key]

    city_key = _key(city)
    suffixes = set(_CITY_SUFFIXES)
    if city_key:
        suffixes.add(city_key)
    candidate = key
    changed = True
    while changed:
        changed = False
        for suffix in sorted(suffixes, key=len, reverse=True):
            if candidate.endswith(f" {suffix}"):
                candidate = candidate[: -(len(suffix) + 1)].strip()
                changed = True
                if candidate in VENUE_ALIASES:
                    return VENUE_ALIASES[candidate]
                break

    # Unknown future venues remain stable across punctuation/case variations.
    return " ".join(part.capitalize() for part in key.split())


def phase_from_over(over: float) -> str:
    if over < 6:
        return "powerplay"
    if over < 16:
        return "middle"
    return "death"


def outcome_from_row(row: pd.Series) -> str:
    extra_type = _key(row.get("extra_type", ""))
    valid_value = pd.to_numeric(row.get("valid_ball", 1), errors="coerce")
    valid = 1 if pd.isna(valid_value) else int(valid_value)
    wicket_kind = _key(row.get("wicket_kind", ""))
    player_out = row.get("player_out")
    wicket = (pd.notna(player_out) or bool(wicket_kind)) and wicket_kind not in NON_DISMISSAL_WICKETS

    if valid == 0:
        if "wide" in extra_type:
            return "WD"
        if "no ball" in extra_type or "noball" in extra_type:
            return "NB"
    if "legbye" in extra_type or "leg bye" in extra_type:
        return "LB"
    if extra_type in {"bye", "byes"}:
        return "B"
    if wicket:
        return "W"

    batter_runs = int(pd.to_numeric(row.get("runs_batter", 0), errors="coerce") or 0)
    if batter_runs >= 6:
        return "6"
    if batter_runs == 5:
        return "4"
    return str(batter_runs) if batter_runs in {0, 1, 2, 3, 4} else "0"


def _first_existing(df: pd.DataFrame, names: Iterable[str], default: object = 0) -> pd.Series:
    for name in names:
        if name in df.columns:
            return df[name]
    return pd.Series(default, index=df.index)


def load_dataset_source(path: Path) -> pd.DataFrame:
    path = path.resolve()
    if path.is_file():
        return pd.read_csv(path, low_memory=False)
    if not path.is_dir():
        raise FileNotFoundError(path)

    balls_path = path / "ball_by_ball_data.csv"
    matches_path = path / "ipl_matches_data.csv"
    teams_path = path / "teams_data.csv"
    missing = [candidate.name for candidate in (balls_path, matches_path, teams_path) if not candidate.exists()]
    if missing:
        raise FileNotFoundError(f"Dataset directory is missing required files: {missing}")

    balls = pd.read_csv(balls_path, low_memory=False)
    matches = pd.read_csv(matches_path, low_memory=False)
    teams = pd.read_csv(teams_path, low_memory=False)
    team_names = teams.set_index("team_id")["team_name"].to_dict()

    balls["batting_team"] = balls["team_batting"].map(team_names)
    balls["bowling_team"] = balls["team_bowling"].map(team_names)
    if balls["batting_team"].isna().any() or balls["bowling_team"].isna().any():
        raise ValueError("Some delivery team IDs are missing from teams_data.csv.")

    match_columns = [
        "match_id",
        "match_date",
        "match_type",
        "overs",
        "balls_per_over",
        "venue",
        "city",
        "toss_decision",
    ]
    balls = balls.merge(
        matches[[column for column in match_columns if column in matches]],
        on="match_id",
        how="left",
        validate="many_to_one",
    )
    if balls["match_date"].isna().any():
        raise ValueError("Some deliveries could not be joined to ipl_matches_data.csv.")

    balls["date"] = balls["match_date"]
    balls["over"] = balls["over_number"]
    balls["ball"] = balls["ball_number"]
    balls["runs_batter"] = balls["batter_runs"]
    balls["runs_total"] = balls["total_runs"]
    balls["runs_extras"] = balls["extras"]
    balls["valid_ball"] = (~(
        balls["is_wide_ball"].fillna(False).astype(bool)
        | balls["is_no_ball"].fillna(False).astype(bool)
    )).astype(int)
    balls["runs_bowler"] = (
        pd.to_numeric(balls["total_runs"], errors="coerce").fillna(0)
        - pd.to_numeric(balls["leg_bye_runs"], errors="coerce").fillna(0)
        - pd.to_numeric(balls["bye_runs"], errors="coerce").fillna(0)
        - pd.to_numeric(balls["penalty_runs"], errors="coerce").fillna(0)
    ).clip(lower=0)
    balls["extra_type"] = np.select(
        [
            balls["is_wide_ball"].fillna(False).astype(bool),
            balls["is_no_ball"].fillna(False).astype(bool),
            balls["is_leg_bye"].fillna(False).astype(bool),
            balls["is_bye"].fillna(False).astype(bool),
            balls["is_penalty"].fillna(False).astype(bool),
        ],
        ["wides", "noballs", "legbyes", "byes", "penalty"],
        default="",
    )
    if "is_super_over" in balls:
        balls = balls[~balls["is_super_over"].fillna(False).astype(bool)].copy()
    return balls


def _standardize_schema(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed:")]
    aliases = {
        "id": "match_id",
        "matchid": "match_id",
        "batsman": "batter",
        "striker": "batter",
        "team_batting": "batting_team",
        "team_bowling": "bowling_team",
        "over_number": "over",
        "ball_number": "ball",
        "batter_runs": "runs_batter",
        "total_runs": "runs_total",
        "extras": "runs_extras",
        "match_date": "date",
        "runs_off_bat": "runs_batter",
        "dismissed_player": "player_out",
    }
    for old, new in aliases.items():
        if new not in df and old in df:
            df[new] = df[old]

    required = {
        "match_id",
        "innings",
        "over",
        "batter",
        "bowler",
        "batting_team",
        "bowling_team",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    defaults = {
        "date": pd.NaT,
        "ball": 1,
        "valid_ball": 1,
        "runs_batter": 0,
        "runs_total": 0,
        "runs_extras": 0,
        "runs_bowler": 0,
        "extra_type": "",
        "wicket_kind": "",
        "player_out": np.nan,
        "fielders_involved": np.nan,
        "venue": "Unknown",
        "city": "",
        "toss_decision": "Unknown",
        "match_type": "T20",
        "balls_per_over": 6,
        "overs": 20,
        "runs_target": np.nan,
    }
    for col, value in defaults.items():
        if col not in df:
            df[col] = value
    return df


def prepare_deliveries(raw: pd.DataFrame) -> pd.DataFrame:
    """Return one row per delivery with strictly pre-delivery model features."""
    df = _standardize_schema(raw)
    df["_row_order"] = np.arange(len(df), dtype=np.int64)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().all() and {"year", "month", "day"}.issubset(df.columns):
        df["date"] = pd.to_datetime(df[["year", "month", "day"]], errors="coerce")

    for col in [
        "innings",
        "over",
        "ball",
        "valid_ball",
        "runs_batter",
        "runs_total",
        "runs_extras",
        "runs_bowler",
        "balls_per_over",
        "overs",
        "runs_target",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["innings"] = df["innings"].fillna(1).astype(int)
    df["over"] = df["over"].fillna(0).astype(int)
    df["valid_ball"] = df["valid_ball"].fillna(1).clip(0, 1).astype(int)
    for col in ["runs_batter", "runs_total", "runs_extras", "runs_bowler"]:
        df[col] = df[col].fillna(0).clip(lower=0)

    match_type = df["match_type"].fillna("T20").astype(str)
    df = df[match_type.str.contains("T20", case=False, na=False)].copy()
    df = df[df["innings"].isin([1, 2])].copy()
    df = df.sort_values(["date", "match_id", "innings", "over", "ball", "_row_order"])

    df["batting_team"] = df["batting_team"].map(canonicalize_team)
    df["bowling_team"] = df["bowling_team"].map(canonicalize_team)
    df["venue"] = [
        canonicalize_venue(venue, city)
        for venue, city in zip(df["venue"], df["city"], strict=False)
    ]
    for col in ["batter", "bowler", "toss_decision"]:
        df[col] = df[col].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    if "non_striker" in df:
        df["non_striker"] = (
            df["non_striker"]
            .fillna("Unknown")
            .astype(str)
            .str.strip()
            .replace("", "Unknown")
        )

    df["outcome"] = df.apply(outcome_from_row, axis=1)
    wicket_kind = df["wicket_kind"].map(_key)
    df["_wicket"] = (
        (df["player_out"].notna() | wicket_kind.ne(""))
        & ~wicket_kind.isin(NON_DISMISSAL_WICKETS)
    ).astype(int)
    non_bowler_wickets = {
        "run out",
        "retired hurt",
        "retired out",
        "obstructing the field",
    }
    df["_bowler_wicket"] = (df["_wicket"].eq(1) & ~wicket_kind.isin(non_bowler_wickets)).astype(int)
    if "balls_faced" in df:
        ball_faced = pd.to_numeric(df["balls_faced"], errors="coerce").fillna(0).clip(0, 1)
    else:
        ball_faced = (~df["extra_type"].map(_key).str.contains("wide")).astype(int)
    df["_ball_faced"] = ball_faced.astype(int)

    appearance_columns = ["match_id", "innings", "_row_order"]
    batter_appearances = df[appearance_columns + ["batter"]].rename(
        columns={"batter": "appearance_player"}
    )
    batter_appearances["_appearance_slot"] = 0
    if "non_striker" in df:
        non_striker_appearances = df[
            appearance_columns + ["non_striker"]
        ].rename(columns={"non_striker": "appearance_player"})
        non_striker_appearances["_appearance_slot"] = 1
        appearances = pd.concat(
            [batter_appearances, non_striker_appearances],
            ignore_index=True,
        )
    else:
        appearances = batter_appearances
    appearances = appearances[
        appearances["appearance_player"].notna()
        & appearances["appearance_player"].ne("Unknown")
    ].sort_values(
        ["match_id", "innings", "_row_order", "_appearance_slot"],
        kind="stable",
    )
    appearances = appearances.drop_duplicates(
        ["match_id", "innings", "appearance_player"],
        keep="first",
    )
    appearances["bat_pos"] = (
        appearances.groupby(["match_id", "innings"], sort=False).cumcount() + 1
    )
    df = df.merge(
        appearances[
            ["match_id", "innings", "appearance_player", "bat_pos"]
        ],
        left_on=["match_id", "innings", "batter"],
        right_on=["match_id", "innings", "appearance_player"],
        how="left",
        validate="many_to_one",
    ).drop(columns=["appearance_player"])
    df["bat_pos"] = df["bat_pos"].fillna(11).clip(1, 11).astype(int)

    innings_group = [df["match_id"], df["innings"]]
    batter_group = [df["match_id"], df["innings"], df["batter"]]
    over_group = [df["match_id"], df["innings"], df["over"]]
    df["team_runs"] = df.groupby(["match_id", "innings"], sort=False)["runs_total"].cumsum() - df["runs_total"]
    df["team_wicket"] = df.groupby(["match_id", "innings"], sort=False)["_wicket"].cumsum() - df["_wicket"]
    df["batter_runs"] = (
        df.groupby(["match_id", "innings", "batter"], sort=False)["runs_batter"].cumsum()
        - df["runs_batter"]
    )
    df["batter_balls"] = (
        df.groupby(["match_id", "innings", "batter"], sort=False)["_ball_faced"].cumsum()
        - df["_ball_faced"]
    )
    df["balls_bowled"] = (
        df.groupby(["match_id", "innings"], sort=False)["valid_ball"].cumsum()
        - df["valid_ball"]
    )
    legal_before_over = (
        df.groupby(["match_id", "innings", "over"], sort=False)["valid_ball"].cumsum()
        - df["valid_ball"]
    )
    df["legal_ball"] = legal_before_over + 1

    scheduled_balls = (
        df["overs"].fillna(20).clip(lower=1, upper=50)
        * df["balls_per_over"].fillna(6).clip(lower=1, upper=8)
    )
    scheduled_balls = scheduled_balls.where(scheduled_balls >= 60, 120)
    df["balls_remaining"] = (scheduled_balls - df["balls_bowled"]).clip(lower=0)
    df["wickets_remaining"] = (10 - df["team_wicket"]).clip(lower=0)
    df["current_run_rate"] = np.where(
        df["balls_bowled"] > 0,
        6.0 * df["team_runs"] / df["balls_bowled"],
        0.0,
    )
    df["batter_strike_rate"] = np.where(
        df["batter_balls"] > 0,
        100.0 * df["batter_runs"] / df["batter_balls"],
        0.0,
    )

    innings_totals = df.groupby(["match_id", "innings"], sort=False)["runs_total"].sum()
    first_totals = innings_totals.xs(1, level="innings", drop_level=True)
    derived_target = df["match_id"].map(first_totals).fillna(0) + 1
    supplied_target = df["runs_target"].where(df["runs_target"] > 0)
    df["target"] = np.where(
        df["innings"].eq(2),
        supplied_target.fillna(derived_target),
        0,
    )
    df["runs_required"] = np.where(
        df["innings"].eq(2),
        (df["target"] - df["team_runs"]).clip(lower=0),
        0,
    )
    df["required_run_rate"] = np.where(
        (df["innings"].eq(2)) & (df["balls_remaining"] > 0),
        6.0 * df["runs_required"] / df["balls_remaining"],
        0.0,
    )
    df["rate_pressure"] = np.where(
        df["innings"].eq(2),
        df["required_run_rate"] - df["current_run_rate"],
        0.0,
    )
    df["phase"] = df["over"].map(phase_from_over)

    for col in NUM_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], 0).fillna(0)
    for col in CAT_FEATURES:
        df[col] = df[col].fillna("Unknown").astype(str)
    return df.dropna(subset=["date", "batter", "bowler"]).reset_index(drop=True)


def data_fingerprint(path: Path) -> str:
    path = path.resolve()
    if path.is_file():
        files = [path]
    else:
        files = sorted(path.glob("*.csv"))
    payload = [
        {
            "path": file.name,
            "size": file.stat().st_size,
            "mtime_ns": file.stat().st_mtime_ns,
        }
        for file in files
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]
