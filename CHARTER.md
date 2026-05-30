# Project Charter — ECO 6810 Final Project

---

## Header

| Field | Value |
|---|---|
| Team members | Annay De (annay.de_phd25@ashoka.edu.in), Tanmay Singh (tanmay.singh_phd25@ashoka.edu.in), Siddhant Mukherjee (siddhant.mukherjee_phd25@ashoka.edu.in) |
| Project type | Predictive — Decision Analytics |
| Estimated hours per person | 50 |
| Charter version | v3 |
| Date | 2026-05-08 |

---

## 1. Problem and Stakeholder

**Stakeholder:** An IPL franchise strategy and analytics unit — specifically the team analyst responsible for playing-XI selection before each match.

**The decision problem:** The analyst faces a constrained resource-allocation problem under uncertainty. A squad of approximately 20 players is available, but only 11 slots exist in the playing XI. Each slot has an opportunity cost: selecting a specialist batter sacrifices a bowling option, and vice versa. The optimal allocation depends on conditions that are only partially observable at decision time — opponent batting order, pitch behaviour, weather, and individual player form.

**The decision moment:** Team selection, approximately 24 hours before the match, when the venue, pitch report, weather forecast, toss outcome, and opposing squad are known but match outcomes are not.

**What this project builds:** A probabilistic ball-by-ball simulation engine that lets the analyst compare expected match outcomes across different XI configurations under specified conditions. This replaces intuition with a calibrated, data-driven forecast of the distribution of possible scores — directly quantifying the uncertainty the analyst faces.

**Economics framing:** This is a canonical decision-under-uncertainty problem. The analyst is a constrained optimiser: maximise expected match performance subject to a fixed squad budget (11 slots, fixed player pool). The simulation layer is the model of the world the analyst uses to evaluate choices before committing. The framing is structurally identical to the economic decision problems this course addresses — the domain is cricket, but the methodology is decision analytics and probabilistic resource allocation.

---

## 2. Main Outcome Variable

- **Name:** Multiclass log-loss on ball-outcome prediction
- **Unit:** Nats (lower is better)
- **Source:** IPL ball-by-ball dataset, `chaitu20/ipl-dataset2008-2025` on Kaggle; target column is the delivery outcome class (dot, 1, 2, 3, 4, 6, W, WD, NB, LB, B)
- **Population:** All deliveries across IPL seasons 2008–2025; held-out test slice = final 15% of matches by date

Log-loss is the right metric here because this is a probabilistic simulation project, not a classification task. A model with well-calibrated probability distributions generates more realistic and decision-useful simulations than one that only maximises hard-label accuracy. Better log-loss directly translates to better simulation quality, which is what the franchise analyst actually needs.

---

## 3. Main Quantitative Success Threshold

Out-of-sample multiclass log-loss of the primary model on the held-out test split is strictly lower than the empirical baseline log-loss on the same split.

Concrete form: `primary_log_loss < baseline_log_loss`

Current values (written by `uv run main.py`):
- Primary model (XGBoost): `1.7136`
- Empirical baseline: `1.8670`
- Status: `passed: true`

Both values are machine-readable in `outputs/primary_metric.json` and `outputs/baseline_metric.json`.

---

## 4. Baseline to Beat

The baseline is an **empirical prior model**: for each possible ball outcome, it estimates the probability from its marginal frequency in the training data, ignoring all match-state features. This is the "historical average" forecast — the best prediction an analyst could make with no contextual information.

Any model that uses match-state features (over, wickets fallen, batter, bowler, venue, innings phase) should beat this baseline. The project's success threshold requires that it does. Beating the baseline is proof that the ML model is learning something genuine from context, not just adding computational complexity for no gain.

---

## 5. Falsifiable Hypothesis

An XGBoost model trained on delivery-level match-state features (over, wickets fallen, batter identity, bowler identity, venue, innings phase) will achieve strictly lower multiclass log-loss than the empirical marginal-frequency baseline on held-out IPL deliveries from seasons not seen during training.

---

## 6. Data Sources and Access Plan

**Source:** IPL ball-by-ball dataset, 2008–2025
**Provider:** Kaggle — `chaitu20/ipl-dataset2008-2025`
**URL:** https://www.kaggle.com/datasets/chaitu20/ipl-dataset2008-2025
**Licence:** Public community dataset, free for educational and research use
**Access method:** `kagglehub` Python library

**Data probe** (also at `Data/data_probe.py`):

```python
import kagglehub
from kagglehub import KaggleDatasetAdapter

df = kagglehub.load_dataset(
    KaggleDatasetAdapter.PANDAS,
    "chaitu20/ipl-dataset2008-2025",
    "",
)
print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print(df.head(3))
```

Run with: `pip install kagglehub[pandas-datasets] && python Data/data_probe.py`

The app and `uv run main.py` load saved artefacts from `artifacts/` and do not require the raw CSV at runtime. A snapshot is committed at `Data/IPL_snapshot.csv` for inspection.

---

## 7. Scope Limits

- We are **not** estimating causal effects of any player, policy, or intervention. This is a predictive project.
- We are **not** predicting match winners directly. The output is a probability distribution over ball outcomes from which scores are simulated.
- We are **not** building player injury or availability forecasting.
- We are **not** harmonising all historical venue name variants; known mismatches are mapped but residuals may exist.
- We are **not** shipping a production-grade application.
- Secondary metrics (accuracy, macro-F1) may be reported but are not the graded success criterion.
- Pitch and weather inputs are user-specified scenario assumptions, not data-trained variables.

---

## 8. Risks and Fallback

**Risk:** Kaggle API requires authentication unavailable in the grading environment.

**Fallback:** All pre-trained model files are committed in `artifacts/`. `uv run main.py` runs end-to-end from saved artefacts with no live data download required. The grader can verify data access separately via `Data/data_probe.py`. If that also fails, `artifacts/metadata.json` documents the training data shape as a static record.

---

## 9. Reproducibility Checklist

- [x] `uv run main.py` runs end-to-end with no manual intervention
- [x] Writes `outputs/primary_metric.json` — `{"metric_name": "log_loss", "value": 1.7136, "threshold": 1.8670, "passed": true}`
- [x] Writes `outputs/baseline_metric.json` — `{"metric_name": "log_loss_baseline", "value": 1.8670}`
- [x] Writes `outputs/milestone_manifest.json` — run summary
- [x] `README.md` documents run command and expected outputs
- [x] Data accessible via documented Kaggle probe or `Data/IPL_snapshot.csv`
- [x] Saved artefacts in `artifacts/` allow full run without raw CSV

---

*Submitted by: Annay De, Tanmay Singh, Siddhant Mukherjee — ECO 6810, Ashoka University*
