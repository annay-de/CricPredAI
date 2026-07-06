"""The Scout — universal player acquisition, separate from the IPL pipeline.

This module lets any cricketer with a public record be added to the player
pool: it searches ESPNcricinfo, pulls a career T20 record, and converts it
into a calibrated engine profile using the *same* Bayesian-shrinkage
formulas the training pipeline uses (train_models.py), so scouted players
sit on the same scale as trained IPL players.

Architecture notes — deliberately separate from the IPL simulation:
- Nothing here touches simulator.py, train_models.py, or the trained
  artifacts. The engine is treated as a sealed black box.
- Scouted profiles are injected by building a *copy* of the artifact
  metadata at simulation time (``merge_into_meta``); the cached IPL
  metadata is never mutated.
- The trained ML models tolerate unseen player names by construction
  (OneHotEncoder(handle_unknown="ignore")), and the empirical prior falls
  back to phase/venue context when a player has no delivery history.
  Player identity therefore flows through the synthesized role profile —
  exactly the mechanism used for trained players, which is what makes
  cross-era "never faced each other" matchups composable.

Data acquisition is a fallback chain, because none of these surfaces is
contractual: (1) ESPNcricinfo's consumer search API, (2) the legacy player
search page, and for statistics the Statsguru career-averages tables,
which have kept the same HTML shape for well over a decade. If every
remote strategy fails (network policy, site changes), the UI offers a
manual-entry path with the same profile math.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Optional

import requests

ROSTER_PATH = Path(__file__).with_name("scout_roster.json")

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _UA, "Accept": "application/json, text/html;q=0.9,*/*;q=0.5"}
_TIMEOUT = 12

SEARCH_API = (
    "https://hs-consumer-api.espncricinfo.com/v1/pages/search/results"
    "?mode=BOTH&page=1&query={query}"
)
SEARCH_HTML = "https://search.espncricinfo.com/ci/content/player/search.html?search={query}"
STATSGURU = (
    "https://stats.espncricinfo.com/ci/engine/player/{player_id}.html"
    "?class={klass};template=results;type={kind}"
)
PROFILE_URL = "https://www.espncricinfo.com/cricketers/player-{player_id}"

# Statsguru class codes: 6 = all Twenty20, 3 = T20 internationals only.
_T20_CLASSES = (6, 3)


class ScoutError(RuntimeError):
    """Raised when every acquisition strategy fails; message is user-facing."""


def _get(url: str) -> requests.Response:
    response = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    response.raise_for_status()
    return response


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def _walk_players(node, found: dict) -> None:
    if isinstance(node, dict):
        object_id = node.get("objectId") or node.get("id")
        long_name = node.get("longName") or node.get("title")
        if (
            object_id
            and long_name
            and (
                "battingStyles" in node
                or "playingRole" in node
                or str(node.get("type", "")).lower() == "player"
            )
        ):
            try:
                pid = int(object_id)
            except (TypeError, ValueError):
                pid = None
            if pid:
                country = ""
                team = node.get("country") or node.get("countryTeam") or {}
                if isinstance(team, dict):
                    country = str(team.get("longName") or team.get("name") or "")
                found.setdefault(
                    pid,
                    {
                        "id": pid,
                        "name": str(long_name),
                        "country": country,
                        "role": str(node.get("playingRole") or ""),
                    },
                )
        for value in node.values():
            _walk_players(value, found)
    elif isinstance(node, list):
        for value in node:
            _walk_players(value, found)


def search_players(query: str, limit: int = 8) -> list[dict]:
    """Search ESPNcricinfo for players by name. Returns id/name/country dicts."""
    query = query.strip()
    if len(query) < 3:
        raise ScoutError("Type at least three characters of the player's name.")
    errors = []
    # strategy 1: consumer search API
    try:
        payload = _get(SEARCH_API.format(query=requests.utils.quote(query))).json()
        found: dict = {}
        _walk_players(payload, found)
        if found:
            return list(found.values())[:limit]
        errors.append("search API returned no players")
    except Exception as exc:  # noqa: BLE001 - fall through to next strategy
        errors.append(f"search API: {exc}")
    # strategy 2: legacy search page
    try:
        html = _get(SEARCH_HTML.format(query=requests.utils.quote(query))).text
        matches = re.findall(
            r'/ci/content/player/(\d+)\.html[^>]*>\s*([^<]{3,60})\s*<',
            html,
        )
        seen, results = set(), []
        for pid, name in matches:
            pid = int(pid)
            if pid in seen:
                continue
            seen.add(pid)
            results.append({"id": pid, "name": name.strip(), "country": "", "role": ""})
            if len(results) >= limit:
                break
        if results:
            return results
        errors.append("legacy search returned no players")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"legacy search: {exc}")
    raise ScoutError(
        "Could not reach ESPNcricinfo search (" + " · ".join(errors) + "). "
        "You can still add the player manually below."
    )


# ---------------------------------------------------------------------------
# career statistics (Statsguru career-averages tables)
# ---------------------------------------------------------------------------

def _strip_tags(fragment: str) -> str:
    return re.sub(r"<[^>]+>", "", fragment).replace("&nbsp;", " ").strip()


def _parse_engine_tables(html: str) -> list[tuple[list[str], list[list[str]]]]:
    """Parse Statsguru's engineTable elements into (headers, rows) pairs."""
    tables = []
    for table_html in re.findall(
        r'<table[^>]*class="engineTable"[^>]*>(.*?)</table>', html, re.S
    ):
        headers = [_strip_tags(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table_html, re.S)]
        rows = []
        for row_html in re.findall(r'<tr[^>]*class="data1"[^>]*>(.*?)</tr>', table_html, re.S):
            cells = [_strip_tags(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)]
            if cells:
                rows.append(cells)
        if headers and rows:
            tables.append((headers, rows))
    return tables


def _to_float(value: str) -> Optional[float]:
    value = value.strip().replace("*", "")
    if not value or value in {"-", "–", ""}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _career_row(html: str, wanted: dict[str, str]) -> Optional[dict[str, float]]:
    """Pull the first career-averages row, mapped through `wanted` col names."""
    for headers, rows in _parse_engine_tables(html):
        index = {h.strip().lower(): i for i, h in enumerate(headers)}
        if not all(key in index for key in wanted.values()):
            continue
        row = rows[0]
        out = {}
        for field, column in wanted.items():
            i = index[column]
            out[field] = _to_float(row[i]) if i < len(row) else None
        return out
    return None


def fetch_t20_career(player_id: int) -> dict:
    """Fetch a player's career T20 batting and bowling aggregates."""
    batting = bowling = None
    errors = []
    for klass in _T20_CLASSES:
        if batting is None:
            try:
                html = _get(
                    STATSGURU.format(player_id=player_id, klass=klass, kind="batting")
                ).text
                batting = _career_row(
                    html,
                    {
                        "matches": "mat",
                        "innings": "inns",
                        "not_outs": "no",
                        "runs": "runs",
                        "balls": "bf",
                        "strike_rate": "sr",
                    },
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"batting class {klass}: {exc}")
        if bowling is None:
            try:
                html = _get(
                    STATSGURU.format(player_id=player_id, klass=klass, kind="bowling")
                ).text
                bowling = _career_row(
                    html,
                    {
                        "matches": "mat",
                        "balls": "balls",
                        "runs": "runs",
                        "wickets": "wkts",
                        "economy": "econ",
                    },
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"bowling class {klass}: {exc}")
        if batting is not None and bowling is not None:
            break
    if batting is None and bowling is None:
        raise ScoutError(
            "Could not read a T20 record from Statsguru ("
            + " · ".join(errors[:2])
            + "). You can still add the player manually."
        )
    return {"batting": batting or {}, "bowling": bowling or {}}


# ---------------------------------------------------------------------------
# profile synthesis — mirrors train_models.py shrinkage exactly
# ---------------------------------------------------------------------------

_PHASE_TEMPLATES = {
    "pace": {"powerplay": 0.38, "middle": 0.27, "death": 0.35},
    "spin": {"powerplay": 0.14, "middle": 0.66, "death": 0.20},
    "none": None,  # use league expected shares
}


def profile_from_career(
    *,
    name: str,
    meta: dict,
    bat_innings: float = 0.0,
    bat_runs: float = 0.0,
    bat_balls: float = 0.0,
    bat_outs: float = 0.0,
    bowl_balls: float = 0.0,
    bowl_runs: float = 0.0,
    bowl_wickets: float = 0.0,
    preferred_position: int = 5,
    bowler_type: str = "none",
    trust: float = 0.5,
) -> dict:
    """Convert public career T20 aggregates into an engine role profile.

    `trust` (0..1) discounts the career sample before shrinkage: scouted
    numbers come from unknown leagues and eras, so a scouted player's
    evidence is deliberately weaker than the same volume of IPL deliveries.
    All shrinkage constants (120 batting, 180 bowling, 36 usage) and score
    formulas are copied from train_models.py so profiles share the scale.
    """
    trust = min(1.0, max(0.05, float(trust)))
    baselines = meta.get("player_rate_baselines", {})
    g_bat = max(0.1, float(baselines.get("bat_runs_per_ball", 1.35)))
    g_out = max(0.005, float(baselines.get("dismissal_rate", 0.05)))
    g_bowl = max(0.1, float(baselines.get("bowl_runs_per_ball", 1.40)))
    g_wkt = max(0.005, float(baselines.get("wicket_rate", 0.05)))

    bat_balls = max(0.0, float(bat_balls or 0.0))
    bowl_balls = max(0.0, float(bowl_balls or 0.0))
    eff_bat = bat_balls * trust
    eff_bowl = bowl_balls * trust

    career_bat_rate = (bat_runs / bat_balls) if bat_balls else g_bat
    career_out_rate = (bat_outs / bat_balls) if bat_balls else g_out
    career_bowl_rate = (bowl_runs / bowl_balls) if bowl_balls else g_bowl
    career_wkt_rate = (bowl_wickets / bowl_balls) if bowl_balls else g_wkt

    bat_rate = (eff_bat * career_bat_rate + 120 * g_bat) / (eff_bat + 120)
    dismissal_rate = (eff_bat * career_out_rate + 120 * g_out) / (eff_bat + 120)
    bowl_rate = (eff_bowl * career_bowl_rate + 180 * g_bowl) / (eff_bowl + 180)
    wicket_rate = (eff_bowl * career_wkt_rate + 180 * g_wkt) / (eff_bowl + 180)

    trusted_bat_balls = int(bat_balls * trust)
    trusted_bowl_balls = int(bowl_balls * trust)
    if trusted_bowl_balls >= 120 and trusted_bat_balls >= 180:
        role = "all-rounder"
    elif trusted_bowl_balls >= max(60, trusted_bat_balls * 0.65):
        role = "bowler"
    else:
        role = "batter"

    effective_innings = round(float(bat_innings or 0.0) * trust * 0.9, 2)
    position = int(min(11, max(1, preferred_position)))
    batting_position = {
        "preferred": float(position),
        "spread": 1.5,
        "innings": int(bat_innings or 0),
        "effective_innings": effective_innings,
        "positions": {
            str(position): {
                "innings": int(bat_innings or 0),
                "effective_innings": effective_innings,
            }
        },
        "effectiveness": {},
    }

    phase_baselines = meta.get("bowling_phase_baselines", {}) or {}
    template = _PHASE_TEMPLATES.get(bowler_type, None)
    bowling_phases = {}
    for phase in ["powerplay", "middle", "death"]:
        baseline = phase_baselines.get(phase, {})
        base_run = float(baseline.get("run_rate", g_bowl))
        base_wkt = float(baseline.get("wicket_rate", g_wkt))
        expected_share = max(0.02, float(baseline.get("ball_share", 1 / 3)))
        share = template.get(phase, expected_share) if template else expected_share
        eff_phase = eff_bowl * share
        prior_run = 0.65 * bowl_rate + 0.35 * base_run
        prior_wkt = 0.65 * wicket_rate + 0.35 * base_wkt
        posterior_run = (eff_phase * prior_run + 120 * prior_run) / (eff_phase + 120)
        posterior_wkt = (eff_phase * prior_wkt + 120 * prior_wkt) / (eff_phase + 120)
        posterior_usage = (eff_phase + 36 * expected_share) / (max(0.0, eff_bowl) + 36)
        usage_ratio = max(0.20, posterior_usage / expected_share)
        selection_score = (
            1.30 * math.log(max(0.25, base_run / max(0.1, posterior_run)))
            + 0.80 * math.log(max(0.25, posterior_wkt / max(0.005, base_wkt)))
            + 0.28 * math.log(usage_ratio)
        )
        bowling_phases[phase] = {
            "balls": int(bowl_balls * share),
            "effective_balls": round(eff_phase, 2),
            "runs_per_ball": round(posterior_run, 5),
            "wicket_rate": round(posterior_wkt, 5),
            "usage_share": round(posterior_usage, 5),
            "selection_score": round(selection_score, 5),
        }

    return {
        "role": role,
        "batting_score": float(
            bat_rate - 2.2 * dismissal_rate + 0.025 * math.log1p(trusted_bat_balls)
        ),
        "bowling_score": float(
            -bowl_rate + 5.0 * wicket_rate + 0.02 * math.log1p(trusted_bowl_balls)
        ),
        "bat_runs_per_ball": float(bat_rate),
        "dismissal_rate": float(dismissal_rate),
        "bowl_runs_per_ball": float(bowl_rate),
        "wicket_rate": float(wicket_rate),
        "bat_balls": int(bat_balls),
        "bowl_balls": int(bowl_balls),
        "effective_bat_balls": round(eff_bat, 2),
        "effective_bowl_balls": round(eff_bowl, 2),
        "batting_position": batting_position,
        "bowling_phases": bowling_phases,
        "scouted": True,
        "scout_source": "espncricinfo",
    }


def profile_from_statsguru(
    *,
    name: str,
    meta: dict,
    career: dict,
    preferred_position: int,
    bowler_type: str,
    trust: float,
) -> dict:
    """Build a profile from fetch_t20_career output, estimating gaps."""
    batting = career.get("batting") or {}
    bowling = career.get("bowling") or {}
    runs = float(batting.get("runs") or 0.0)
    balls = float(batting.get("balls") or 0.0)
    strike_rate = float(batting.get("strike_rate") or 0.0)
    if not balls and runs and strike_rate:
        balls = runs * 100.0 / strike_rate
    innings = float(batting.get("innings") or 0.0)
    not_outs = float(batting.get("not_outs") or 0.0)
    outs = max(0.0, innings - not_outs)
    bowl_balls = float(bowling.get("balls") or 0.0)
    bowl_runs = float(bowling.get("runs") or 0.0)
    economy = float(bowling.get("economy") or 0.0)
    if not bowl_runs and bowl_balls and economy:
        bowl_runs = economy * bowl_balls / 6.0
    wickets = float(bowling.get("wickets") or 0.0)
    return profile_from_career(
        name=name,
        meta=meta,
        bat_innings=innings,
        bat_runs=runs,
        bat_balls=balls,
        bat_outs=outs,
        bowl_balls=bowl_balls,
        bowl_runs=bowl_runs,
        bowl_wickets=wickets,
        preferred_position=preferred_position,
        bowler_type=bowler_type,
        trust=trust,
    )


# ---------------------------------------------------------------------------
# roster persistence + meta augmentation
# ---------------------------------------------------------------------------

def load_roster() -> dict:
    try:
        with ROSTER_PATH.open() as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_roster(roster: dict) -> None:
    try:
        with ROSTER_PATH.open("w") as fh:
            json.dump(roster, fh, indent=1)
    except OSError:
        pass  # ephemeral filesystems (Streamlit Cloud) — session copy still works


def merge_into_meta(meta: dict, roster: dict) -> dict:
    """Return a copy of the artifact metadata with scouted players injected.

    The IPL metadata object is never mutated — the simulation architecture
    stays sealed; scouted players exist only in this merged view.
    """
    if not roster:
        return meta
    merged = dict(meta)
    merged["roles"] = {**meta.get("roles", {}), **{n: r["profile"] for n, r in roster.items()}}
    players = set(meta.get("players", [])) | set(roster.keys())
    merged["players"] = sorted(players)
    return merged


def career_summary(career: dict) -> str:
    """One-line human summary of a fetched record for the UI."""
    batting = career.get("batting") or {}
    bowling = career.get("bowling") or {}
    parts = []
    if batting.get("runs"):
        strike_rate = batting.get("strike_rate")
        parts.append(
            f"{int(batting['runs'])} runs in {int(batting.get('innings') or 0)} inns"
            + (f" · SR {strike_rate:.1f}" if strike_rate else "")
        )
    if bowling.get("wickets"):
        economy = bowling.get("economy")
        parts.append(
            f"{int(bowling['wickets'])} wkts"
            + (f" · econ {economy:.2f}" if economy else "")
        )
    return " — ".join(parts) if parts else "no T20 record found"
