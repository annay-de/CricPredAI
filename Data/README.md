# Data

The raw IPL dataset is NOT committed to this repo due to GitHub's 100 MB file size limit.

## Snapshot file

`IPL_snapshot.csv` is included in this folder. It preserves the full column structure of the
original dataset and contains a representative sample for inspection and pipeline validation.

## Full dataset — two ways to get it

**Option A — Google Drive (direct download):**  
https://drive.google.com/drive/folders/1G06ILrvEOes6zN0_nbIXkAhCtsMM9kP9?usp=sharing

**Option B — Kaggle (programmatic, recommended for reproducibility):**  
Dataset: `chaitu20/ipl-dataset2008-2025`  
URL: https://www.kaggle.com/datasets/chaitu20/ipl-dataset2008-2025  
Licence: Public community dataset (free for educational and research use)

To download via Kaggle and verify it loads:
pip install kagglehub[pandas-datasets]
python Data/data_probe.py

## What the full dataset was used for

The complete dataset was used locally for feature engineering, model training, calibration,
and artefact generation. The deployed app and `uv run main.py` load saved artefacts from
`artifacts/` and do NOT require the raw CSV at runtime.
