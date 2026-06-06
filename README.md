**ECO 6810 Final Project — Annay De (annay.de_phd25@ashoka.edu.in)**

This project builds a probabilistic decision-support tool for resource allocation under uncertainty. The stakeholder is an IPL franchise strategy unit facing a constrained optimisation problem: which 11 players maximise expected match performance given opponent, venue, batting order, and historical player form? The tool simulates ball-by-ball match outcomes under different XI configurations using calibrated models.

---

## Course Milestone Run

To run the grading pipeline:
uv run --with-requirements requirements.txt main.py


This writes three output files:
- `outputs/baseline_metric.json` — empirical baseline log-loss (historical average prior)
- `outputs/primary_metric.json` — primary model log-loss (XGBoost, beats baseline)
- `outputs/milestone_manifest.json` — run summary

Current result: XGBoost log-loss `1.7136` < baseline `1.8670` → `passed: true`

To launch the interactive decision-support app:
streamlit run app.py


Live deployment: https://cricpredai3.streamlit.app/

---

## What this tool does

The simulator takes a user-specified XI, venue, toss outcome, model profile, and opponent XI, then runs a ball-by-ball probabilistic simulation of both innings. The output includes a projected scorecard, score progression, and repeated-match distribution.

This is a decision analytics tool, not a score prediction app. The value is in comparing scenarios, not in producing a single point forecast.

---

## Project framing

The resource-allocation problem: a franchise has a squad of ~20 players and must select 11. Each slot has an opportunity cost. The decision is made under uncertainty about opponent strategy, venue effects, and individual player form. This project builds the simulation layer that lets an analyst quantify that uncertainty and stress-test selection choices before the decision moment (24 hours before match).

---

## Improvements in this version

- Leakage-safe pre-delivery features; the outcome delivery is never included in its own predictors
- Target, runs-required, balls-remaining, required-rate, and pressure features for second innings
- Chronological match-level train/calibration/test split and validation-selected probability calibration
- Five-year recency half-life so current IPL scoring patterns matter more than early-era matches
- Canonical venue and franchise names shared by training and simulation
- Full-data XGBoost and logistic models instead of tiny random row samples
- Versioned, compact runtime artifacts; the raw dataset is not needed for simulations
- Removed unreliable preset team-pool dependency from main workflow
- User types team names manually; player selection uses dataset-derived autocomplete
- Adds data-backed venue, toss winner, toss decision, model, and temporal profile controls
- Includes XGBoost, calibrated ensemble, logistic, and empirical baseline simulation paths
- Empirical calibration/blending prevents ML probability collapse in simulation
- Correct wide/no-ball handling: bowler locked until six legal balls bowled
- No-ball, free-hit, wide, bye and leg-bye logic using dataset-derived extra distributions
- Combined both innings scorecards on one page
- Superimposed score progression curves for both innings with wicket markers
- Ball-by-ball verification table and downloadable delivery log

---

## Deploying

### Streamlit Cloud

Deploy `app.py` on Streamlit Cloud. The app loads saved artefacts from `artifacts/` and does not require `IPL.csv` at runtime.

1. Push the repository to GitHub.
2. Connect the repo in Streamlit Cloud.
3. Set the app entrypoint to `app.py` if prompted.

### Docker

A `Dockerfile` and `.dockerignore` are included for container-based deployment.

Build and run locally:

```bash
docker build -t cricpredai .
docker run -p 8501:8501 cricpredai
```

On platforms that use `Procfile`, the provided `Procfile` starts the app with:

```bash
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

## Retraining

The normal workflow downloads and preprocesses the dataset once:

```bash
python -m pip install -r requirements-training.txt
python Data/download_dataset.py
python train_models.py --data Data/ipl_dataset --profiles modern lifetime
python validate_simulator.py --data Data/ipl_dataset --profile modern
python validate_simulator.py --data Data/ipl_dataset --profile lifetime
```

Prepared features are cached under `artifacts/cache/`. Simulations never load
the raw dataset; they use the compact files under `artifacts/`.

Runtime profile selection:

```python
from simulator import load_artifacts

modern_meta, modern_report, modern_models = load_artifacts("modern")
legends_meta, legends_report, legends_models = load_artifacts("lifetime")
```

`modern` applies a five-year recency half-life. `lifetime` gives every IPL
delivery equal weight and is intended for legends and cross-era matches.
Both profiles have their own XGBoost/logistic models, empirical priors,
calibration settings, and player metadata under `artifacts/profiles/`.

## Data

See `Data/README.md` for the exact Kaggle source, current date coverage, and
future-season update workflow.
