from __future__ import annotations

import argparse
from pathlib import Path

import kagglehub

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDLE = "maratheabhishek/ipl-dataset-2008-to-2025"


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the normalized IPL dataset.")
    parser.add_argument("--handle", default=DEFAULT_HANDLE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "Data" / "ipl_dataset")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = Path(
        kagglehub.dataset_download(
            args.handle,
            output_dir=str(args.output_dir),
            force_download=args.force,
        )
    )
    required = {
        "ball_by_ball_data.csv",
        "ipl_matches_data.csv",
        "teams_data.csv",
    }
    available = {path.name for path in downloaded.rglob("*.csv")}
    missing = sorted(required - available)
    if missing:
        raise FileNotFoundError(f"Downloaded dataset is missing required files: {missing}")
    print(f"Dataset ready: {downloaded}")
    print(f"Retrain with: python train_models.py --data \"{downloaded}\"")


if __name__ == "__main__":
    main()
