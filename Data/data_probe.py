# Data probe: downloads IPL dataset from Kaggle and verifies it loads correctly.
# Run this once to confirm data access: python Data/data_probe.py
# Requires: pip install kagglehub[pandas-datasets]

import kagglehub
from kagglehub import KaggleDatasetAdapter

df = kagglehub.load_dataset(
    KaggleDatasetAdapter.PANDAS,
    "chaitu20/ipl-dataset2008-2025",
    "",
)

print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print("First 3 rows:")
print(df.head(3))
