from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from simulator import load_artifacts, simulate_distribution

ROOT = Path(__file__).resolve().parent


def select_xi(meta: dict, strongest: bool) -> list[str]:
    roles = meta["roles"]
    batters = sorted(
        (player for player, stats in roles.items() if stats.get("bat_balls", 0) >= 300),
        key=lambda player: roles[player].get("batting_score", 0.0),
        reverse=strongest,
    )
    bowlers = sorted(
        (player for player, stats in roles.items() if stats.get("bowl_balls", 0) >= 300),
        key=lambda player: roles[player].get("bowling_score", 0.0),
        reverse=strongest,
    )
    xi = []
    for player in batters:
        if player not in xi:
            xi.append(player)
        if len(xi) == 6:
            break
    for player in bowlers:
        if player not in xi:
            xi.append(player)
        if len(xi) == 11:
            break
    return xi


def historical_chase_rate(data_dir: Path) -> tuple[int, float]:
    matches = pd.read_csv(data_dir / "ipl_matches_data.csv")
    balls = pd.read_csv(
        data_dir / "ball_by_ball_data.csv",
        usecols=["match_id", "innings", "team_batting", "is_super_over"],
    )
    regular = balls[~balls["is_super_over"].fillna(False).astype(bool)]
    second_innings = (
        regular[regular["innings"].eq(2)]
        .drop_duplicates(["match_id", "innings"])[["match_id", "team_batting"]]
        .rename(columns={"team_batting": "chaser"})
    )
    settled = matches.merge(second_innings, on="match_id", how="inner")
    settled = settled[
        settled["match_winner"].notna()
        & settled["result"].astype(str).str.lower().ne("tie")
    ]
    return len(settled), float((settled["match_winner"] == settled["chaser"]).mean())


def win_rate(frame: pd.DataFrame, winner: str) -> float:
    return float(frame["winner"].eq(winner).mean())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run behavioral simulator validation.")
    parser.add_argument("--data", type=Path, default=ROOT / "Data" / "ipl_dataset")
    parser.add_argument("--model", default="xgboost")
    parser.add_argument("--profile", choices=["modern", "lifetime"], default="modern")
    parser.add_argument("--simulations", type=int, default=60)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    meta, _, models = load_artifacts(args.profile)
    strong = select_xi(meta, strongest=True)
    weak = select_xi(meta, strongest=False)
    scenario_runs = max(30, args.simulations // 2)
    common = (
        models,
        meta,
        args.model,
        "Eden Gardens",
        "balanced",
        "clear",
        "Team A",
        "bat",
    )

    mirror = simulate_distribution(
        args.simulations,
        "Team A",
        "Team B",
        strong,
        strong,
        *common,
        seed=5000,
    )
    weak_chase = simulate_distribution(
        scenario_runs,
        "Team A",
        "Team B",
        strong,
        weak,
        *common,
        seed=7000,
    )
    strong_chase = simulate_distribution(
        scenario_runs,
        "Team A",
        "Team B",
        weak,
        strong,
        *common,
        seed=9000,
    )
    historical_n, historical_rate = historical_chase_rate(args.data)

    mirror_chase_rate = win_rate(mirror, "Team B")
    weak_chase_rate = win_rate(weak_chase, "Team B")
    strong_chase_rate = win_rate(strong_chase, "Team B")
    checks = {
        "mirror_chase_rate_near_history": abs(mirror_chase_rate - historical_rate) <= 0.12,
        "weak_xi_does_not_win_from_innings_order": weak_chase_rate <= 0.25,
        "strong_xi_remains_dominant_when_chasing": strong_chase_rate >= 0.75,
    }
    result = {
        "dataset": meta.get("data_source"),
        "coverage_end": meta.get("data_end_date"),
        "model": args.model,
        "historical_settled_matches": historical_n,
        "historical_chase_win_rate": round(historical_rate, 4),
        "mirror_xi": {
            "simulations": args.simulations,
            "batting_first_wins": int(mirror["winner"].eq("Team A").sum()),
            "chasing_wins": int(mirror["winner"].eq("Team B").sum()),
            "ties": int(mirror["winner"].eq("Tie").sum()),
            "chase_win_rate": round(mirror_chase_rate, 4),
        },
        "strength_sensitivity": {
            "simulations_per_direction": scenario_runs,
            "weak_xi_chasing_strong_xi_win_rate": round(weak_chase_rate, 4),
            "strong_xi_chasing_weak_xi_win_rate": round(strong_chase_rate, 4),
        },
        "release_checks": checks,
        "release_checks_passed": all(checks.values()),
    }
    output = args.output or (
        ROOT / "artifacts" / "profiles" / args.profile / "simulation_validation.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not all(checks.values()):
        raise SystemExit("Simulation behavioral release checks failed.")


if __name__ == "__main__":
    main()
