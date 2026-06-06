# Data

The full dataset is not committed. The trained runtime artifacts are committed,
so simulations do not read the 100+ MB source data.

## Authoritative source

- Kaggle: `maratheabhishek/ipl-dataset-2008-to-2025`
- URL: https://www.kaggle.com/datasets/maratheabhishek/ipl-dataset-2008-to-2025
- Current downloaded coverage: April 18, 2008 through May 1, 2026
- Current size: 1,212 matches and 288,051 non-super-over deliveries

The Kaggle slug still says 2025, but the current files include 43 matches from
the 2026 season.

## One-time setup

```bash
python -m pip install -r requirements-training.txt
python Data/download_dataset.py
python Data/data_probe.py
```

The downloader stores the normalized source files in `Data/ipl_dataset/`, which
is ignored by Git.

## Retraining

```bash
python train_models.py --data Data/ipl_dataset --profiles modern lifetime
python validate_simulator.py --data Data/ipl_dataset --profile modern
python validate_simulator.py --data Data/ipl_dataset --profile lifetime
```

Preprocessed deliveries are cached under `artifacts/cache/`. Repeating a
training run against unchanged files skips the expensive feature-preparation
step. The app and simulator load only `artifacts/metadata.json`,
`artifacts/model_report.csv`, and `artifacts/models/*.joblib`.

The loader accepts future updates of the same normalized dataset layout. New
seasons, players, teams, and venue spellings are handled without changing the
model code.
