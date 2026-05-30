**ECO 6810 Final Project — Annay De (annay.de_phd25@ashoka.edu.in), Tanmay Singh (tanmay.singh_phd25@ashoka.edu.in), Siddhant Mukherjee (siddhant.mukherjee_phd25@ashoka.edu.in)**

This project builds a probabilistic decision-support tool for resource allocation under uncertainty. The stakeholder is an IPL franchise strategy unit facing a constrained optimisation problem: which 11 players (from a fixed squad) maximise expected match performance given opponent, venue, pitch, and weather conditions? The tool simulates ball-by-ball match outcomes under different XI configurations, replacing analyst intuition with a calibrated ML model.

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

The simulator takes a user-specified XI, venue, pitch type, weather, toss outcome, and opponent XI — then runs a ball-by-ball probabilistic simulation of both innings using a trained XGBoost model. The output is a projected scorecard and score progression curve, allowing the analyst to compare expected outcomes across different squad configurations before committing to a selection.

This is a decision analytics tool, not a score prediction app. The value is in comparing scenarios, not in producing a single point forecast.

---

## Project framing

The resource-allocation problem: a franchise has a squad of ~20 players and must select 11. Each slot has an opportunity cost. The decision is made under uncertainty about pitch conditions, opponent strategy, and individual player form. This project builds the simulation layer that lets an analyst quantify that uncertainty and stress-test selection choices before the decision moment (24 hours before match).

---

## Improvements in this version

- Removed unreliable preset team-pool dependency from main workflow
- User types team names manually; player selection uses dataset-derived autocomplete
- Adds venue, pitch, weather, toss winner and toss decision as simulation inputs
- Adds XGBoost alongside Random Forest, Logistic, Extra Trees, HistGradientBoosting, and baseline prior
- Empirical calibration/blending prevents ML probability collapse in simulation
- Correct wide/no-ball handling: bowler locked until six legal balls bowled
- No-ball, free-hit, wide, bye and leg-bye logic using dataset-derived extra distributions
- Combined both innings scorecards on one page
- Superimposed score progression curves for both innings with wicket markers
- Ball-by-ball verification table and optional commentary

---

## Deploying

Deploy `app.py` on Streamlit Cloud. The app loads saved artefacts from `artifacts/` and does not require `IPL.csv` at runtime.

## Retraining

To retrain models from scratch, place `IPL.csv` in the root folder and run:
python train_models.py

This regenerates all files under `artifacts/`.

## Data

See `Data/README.md` for the full data source, Kaggle download path, and snapshot details.
