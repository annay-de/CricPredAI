"""Cricsheet ingestion — delivery-level evidence for the world profile.

Converts Cricsheet's open ball-by-ball JSON archives (cricsheet.org) into
the flat delivery CSV that the existing training pipeline consumes, so a
new "world" evidence profile can be trained across leagues: IPL, PSL,
BBL, CPL, T20 internationals, and any other T20 competition Cricsheet
publishes. Once trained, scouted players from those leagues stop being
career-aggregate approximations and gain real delivery-level history in
the models.

The IPL architecture stays intact: this module only *produces data* in
the schema `data_pipeline.prepare_deliveries` already accepts (a single
CSV path is a supported `--data` input for train_models.py). Nothing in
the simulator or the existing profiles changes.

Usage (run where cricsheet.org is reachable):

    python cricsheet_ingest.py --leagues ipl psl bbl cpl t20s \
        --output Data/world_dataset.csv
    python train_models.py --data Data/world_dataset.csv --profiles world
    python validate_simulator.py --data Data/world_dataset.csv --profile world

The app discovers `artifacts/profiles/world/` automatically and offers it
in the Evidence selector next to modern and lifetime.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

DOWNLOAD_URL = "https://cricsheet.org/downloads/{slug}_json.zip"

# Curated Cricsheet competition slugs. Any other slug cricsheet.org
# publishes can be passed verbatim to --leagues.
LEAGUES = {
    "ipl": "Indian Premier League",
    "psl": "Pakistan Super League",
    "bbl": "Big Bash League",
    "cpl": "Caribbean Premier League",
    "bpl": "Bangladesh Premier League",
    "lpl": "Lanka Premier League",
    "sat": "SA20",
    "ssm": "Super Smash",
    "mlc": "Major League Cricket",
    "ilt": "International League T20",
    "ntb": "T20 Blast",
    "t20s": "T20 Internationals",
}

CSV_COLUMNS = [
    "match_id",
    "date",
    "venue",
    "city",
    "match_type",
    "gender",
    "competition",
    "toss_decision",
    "balls_per_over",
    "overs",
    "innings",
    "over",
    "ball",
    "batter",
    "non_striker",
    "bowler",
    "batting_team",
    "bowling_team",
    "valid_ball",
    "runs_batter",
    "runs_total",
    "runs_extras",
    "runs_bowler",
    "extra_type",
    "wicket_kind",
    "player_out",
    "fielders_involved",
    "runs_target",
]

_EXTRA_PRIORITY = ["wides", "noballs", "legbyes", "byes", "penalty"]


def parse_match(
    data: dict,
    match_id: str,
    *,
    gender: str = "male",
) -> list[dict]:
    """Convert one Cricsheet match dict into pipeline-schema delivery rows.

    Returns [] for matches outside scope: wrong gender, non-T20 formats
    (e.g. The Hundred's five-ball overs), or malformed files. Super-over
    innings inside a T20 are skipped, matching the IPL corpus.
    """
    info = data.get("info") or {}
    if gender != "all" and str(info.get("gender", "")).lower() != gender:
        return []
    match_type = str(info.get("match_type", "")).upper()
    if match_type not in {"T20", "IT20"}:
        return []
    if int(info.get("balls_per_over", 6) or 6) != 6:
        return []

    teams = [str(team) for team in (info.get("teams") or [])]
    if len(teams) != 2:
        return []
    dates = info.get("dates") or []
    date = str(dates[0]) if dates else ""
    venue = str(info.get("venue") or "Unknown")
    city = str(info.get("city") or "")
    toss = info.get("toss") or {}
    toss_decision = str(toss.get("decision") or "Unknown")
    competition = str((info.get("event") or {}).get("name") or "")
    overs_limit = int(info.get("overs", 20) or 20)

    rows: list[dict] = []
    innings_number = 0
    for innings in data.get("innings") or []:
        if innings.get("super_over"):
            continue
        innings_number += 1
        if innings_number > 2:
            break
        batting_team = str(innings.get("team") or "")
        if batting_team not in teams:
            continue
        bowling_team = teams[1] if batting_team == teams[0] else teams[0]
        target = (innings.get("target") or {}).get("runs")
        runs_target = float(target) if target is not None else None

        for over_block in innings.get("overs") or []:
            over_number = int(over_block.get("over", 0))
            for ball_number, delivery in enumerate(
                over_block.get("deliveries") or [], start=1
            ):
                runs = delivery.get("runs") or {}
                extras = delivery.get("extras") or {}
                extra_type = ""
                for kind in _EXTRA_PRIORITY:
                    if kind in extras:
                        extra_type = kind
                        break
                runs_total = float(runs.get("total", 0) or 0)
                runs_batter = float(runs.get("batter", 0) or 0)
                runs_extras = float(runs.get("extras", 0) or 0)
                runs_bowler = max(
                    0.0,
                    runs_total
                    - float(extras.get("legbyes", 0) or 0)
                    - float(extras.get("byes", 0) or 0)
                    - float(extras.get("penalty", 0) or 0),
                )
                wickets = delivery.get("wickets") or []
                wicket_kind = str(wickets[0].get("kind", "")) if wickets else ""
                player_out = str(wickets[0].get("player_out", "")) if wickets else ""
                fielders = (
                    [
                        str(fielder.get("name", "")).strip()
                        for fielder in (wickets[0].get("fielders") or [])
                        if fielder.get("name")
                    ]
                    if wickets
                    else []
                )
                rows.append(
                    {
                        "match_id": match_id,
                        "date": date,
                        "venue": venue,
                        "city": city,
                        "match_type": "T20",
                        "gender": str(info.get("gender", "")),
                        "competition": competition,
                        "toss_decision": toss_decision,
                        "balls_per_over": 6,
                        "overs": overs_limit,
                        "innings": innings_number,
                        "over": over_number,
                        "ball": ball_number,
                        "batter": str(delivery.get("batter", "")),
                        "non_striker": str(delivery.get("non_striker", "")),
                        "bowler": str(delivery.get("bowler", "")),
                        "batting_team": batting_team,
                        "bowling_team": bowling_team,
                        "valid_ball": 0 if ("wides" in extras or "noballs" in extras) else 1,
                        "runs_batter": runs_batter,
                        "runs_total": runs_total,
                        "runs_extras": runs_extras,
                        "runs_bowler": runs_bowler,
                        "extra_type": extra_type,
                        "wicket_kind": wicket_kind,
                        "player_out": player_out or None,
                        "fielders_involved": repr(fielders) if fielders else None,
                        "runs_target": runs_target,
                    }
                )
    return rows


def parse_zip(zip_path: Path, *, league: str, gender: str = "male") -> list[dict]:
    """Parse every match JSON inside one Cricsheet archive."""
    rows: list[dict] = []
    skipped = 0
    with zipfile.ZipFile(zip_path) as archive:
        names = [n for n in archive.namelist() if n.endswith(".json")]
        for name in sorted(names):
            try:
                data = json.loads(archive.read(name))
            except (json.JSONDecodeError, KeyError):
                skipped += 1
                continue
            match_id = f"{league}_{Path(name).stem}"
            rows.extend(parse_match(data, match_id, gender=gender))
    if skipped:
        print(f"  {league}: skipped {skipped} unreadable files")
    return rows


def download_league(league: str, dest_dir: Path) -> Optional[Path]:
    """Download one league archive; tries the gendered URL first."""
    import requests

    dest = dest_dir / f"{league}_json.zip"
    for slug in (f"{league}_male", league):
        url = DOWNLOAD_URL.format(slug=slug)
        try:
            response = requests.get(url, timeout=120, stream=True)
            if response.status_code != 200:
                continue
            with dest.open("wb") as fh:
                for chunk in response.iter_content(chunk_size=1 << 16):
                    fh.write(chunk)
            print(f"  downloaded {url} ({dest.stat().st_size / 1e6:.1f} MB)")
            return dest
        except requests.RequestException as exc:
            print(f"  {url}: {exc}")
    return None


def build_dataset(
    leagues: Iterable[str],
    output: Path,
    *,
    gender: str = "male",
    zips_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """Download (or reuse local) archives and write the combined CSV."""
    all_rows: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        for league in leagues:
            print(f"[{league}] {LEAGUES.get(league, 'custom competition')}")
            local = (zips_dir / f"{league}_json.zip") if zips_dir else None
            if local is not None and local.exists():
                zip_path = local
                print(f"  using local archive {local}")
            else:
                zip_path = download_league(league, Path(tmp))
                if zip_path is None:
                    print(f"  could not download {league}; skipping")
                    continue
            league_rows = parse_zip(zip_path, league=league, gender=gender)
            print(f"  {len(league_rows):,} deliveries")
            all_rows.extend(league_rows)

    if not all_rows:
        raise SystemExit("No deliveries ingested; nothing to write.")
    frame = pd.DataFrame(all_rows, columns=CSV_COLUMNS)
    frame = frame.sort_values(["date", "match_id", "innings", "over", "ball"])
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    matches = frame["match_id"].nunique()
    players = pd.unique(frame[["batter", "bowler"]].values.ravel()).size
    print(
        f"\nWrote {len(frame):,} deliveries from {matches:,} matches "
        f"({players:,} players) to {output}"
    )
    print(f"Train with: python train_models.py --data {output} --profiles world")
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a multi-league delivery CSV from Cricsheet archives."
    )
    parser.add_argument(
        "--leagues",
        nargs="+",
        default=["ipl", "psl", "bbl", "cpl", "t20s"],
        help=f"Cricsheet competition slugs. Curated: {', '.join(LEAGUES)}. "
        "Any other cricsheet.org slug is accepted verbatim.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "Data" / "world_dataset.csv",
    )
    parser.add_argument(
        "--gender",
        choices=["male", "female", "all"],
        default="male",
        help="Which competitions to keep (Cricsheet tags every match).",
    )
    parser.add_argument(
        "--zips-dir",
        type=Path,
        default=None,
        help="Directory of already-downloaded <league>_json.zip archives "
        "to use instead of downloading.",
    )
    args = parser.parse_args()
    build_dataset(args.leagues, args.output, gender=args.gender, zips_dir=args.zips_dir)


if __name__ == "__main__":
    main()
