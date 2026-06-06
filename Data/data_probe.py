from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline import load_dataset_source, prepare_deliveries

SOURCE = ROOT / "Data" / "ipl_dataset"

if not SOURCE.exists():
    raise FileNotFoundError(
        "Download the dataset first with: python Data/download_dataset.py"
    )

deliveries = prepare_deliveries(load_dataset_source(SOURCE))
print(f"Deliveries: {len(deliveries):,}")
print(f"Matches: {deliveries['match_id'].nunique():,}")
print(f"Coverage: {deliveries['date'].min().date()} to {deliveries['date'].max().date()}")
print(f"Canonical venues: {deliveries['venue'].nunique()}")
print(f"Outcomes: {deliveries['outcome'].value_counts().to_dict()}")
