# AI Supply Chain Prediction & Procurement Platform

Private project for supplier discovery, procurement analysis and quotation review.

**Status (13 November 2026): prototype.** The main branch contains procurement datasets, Python analysis and matching modules, an offline HTML demo, and a separately documented real-quotation pilot. This repository snapshot does not establish production readiness or validation against real buyer outcomes.

## Start the browser demo

From the repository root with Python 3.10 or later, run: `python ml/procurement_platform.py`.

The script generates and opens `ml/procurement_platform.html` using the Python standard library. It rewrites that tracked HTML file; save local edits to it first.

Optional command-line/data tools: `python -m pip install -r requirements-terminal.txt`.
Optional machine-learning and semantic-matching dependencies: `python -m pip install -r requirements-ml.txt`.
The ML requirements include the terminal requirements. Install them only for those modules; the browser demo does not need them. The repository does not document one universal training command.

## Run the history regression tests

With Python 3.10 or later, install `python -m pip install pandas numpy scikit-learn joblib`,
then run `python -m unittest discover -v` from the repository root.
The history, chronological-split and validation-policy tests use Python's standard-library
test runner. No trained ML models or semantic-model downloads are needed.
They check outcome availability, same-day exclusions, open-order labels, future-outcome
isolation, duplicate order IDs and risk-snapshot dates; they do not validate real supplier performance.

## Run the corrected training experiment

Install `python -m pip install pandas numpy scikit-learn joblib`, then run from the repository root:

```powershell
python ml/train_improved_model.py --validation-start 2025-01-01 --test-start 2025-10-25 --as-of 2026-11-13
```

Choose and freeze the dates before comparing results. Training uses orders and labels known before
validation starts. Validation uses later orders with labels known before testing starts. The final
test includes orders and labels strictly before `--as-of`; open or immature labels are excluded,
and their count is printed. No calendar day is divided between partitions. History features use
the shared outcome-available builder, including outcomes disclosed during validation/test before
each order day. When the source lacks `outcome_available_at`, completion date is the assumed
availability date; real records require verified disclosure timestamps.

Threshold diagnostics use validation only; final-test metrics use the fixed 0.50 threshold.
The existing 300-tree seeded Random Forest and input columns are retained. The command overwrites
`models/delivery_risk_model_clean.pkl`; copy any model you need to preserve before training.
This remains a synthetic experiment, and other experimental trainers have not been corrected.

## Investigate recall without scoring the final test

Using the corrected saved model, run from the repository root:

```powershell
python ml/validation_recall.py --validation-start 2025-01-01 --test-start 2025-10-25 --output validation-runs/thresholds.json
python ml/compare_validation_recall.py --validation-start 2025-01-01 --test-start 2025-10-25 --output validation-runs/candidates
```

Use new output paths for every run. The first command reports threshold trade-offs, maximum F2
and missed-delay score bands. The second fits only two additional Random Forest leaf sizes
(20 and 100) on mature training labels, then selects maximum validation recall subject to
precision of at least 50%. That floor is a provisional review-workload assumption, not an
approved buyer requirement. Test-period rows are excluded before outcome parsing or feature
building; neither command scores the final test or overwrites the original model.

The second command saves `selected-model.pkl` and `policy.json`. To apply the experimental
policy, compare its class-1 probability with the exact threshold in `policy.json` using `>=`.
The pipeline's ordinary `predict()` still uses 0.50; application behavior is not changed
automatically. Verify the model hash against the policy before use. See
[validation results](training-results/validation-recall.md) for the false-alert cost and limits.

To compare recall while allowing no more false alerts than the original validation
baseline, run:

```powershell
python ml/compare_low_alert_recall.py --validation-start 2025-01-01 --test-start 2025-10-25 --output validation-runs/low-alert
```

This compares the original forest, larger forest leaves, Extra Trees and histogram
boosting using the same training/validation cutoffs. The budget is the original
model's validation false-positive count at 0.50. Ties retain the original policy;
a new model is saved only for a better validation operating point. It never scores
the final test. See [the low-alert results](training-results/low-alert-recall.md):
the current candidate set did not improve recall at the original false-alert budget.

To test additional leakage-safe history features with the same validation protocol:

```powershell
python ml/compare_low_alert_recall.py --experimental-features --validation-start 2025-01-01 --test-start 2025-10-25 --output validation-runs/history-features
```

The flag compares workload, recent disclosed outcomes, supplier-item history and their
combination. Features are built before excluding immature labels, so open orders remain
visible in workload history. Final-test rows are still excluded before feature building.
The production history schema, trainer and app defaults remain unchanged. See
[feature investigation results](training-results/leakage-safe-features.md) for definitions,
the small validation-only gain and artifact limitations. The experimental model needs
`build_experiment_features` and its recorded feature columns; existing caller inputs
are not automatically compatible.

## What is in the repository

- `dataset/`: procurement records, supplier history, supplier-item data, and a public-procurement sample.
- `ml/`: procurement analysis, supplier discovery/matching, catalog search, risk and training experiments, and the browser demo.
- `real-pilot/`: input templates and a guided quotation-review pilot. Start with [real-pilot/README.md](real-pilot/README.md).

## Current limits and known issues

The real-pilot guide describes a local quotation-review engine tested with fixtures, but no real buyer records or supplier-risk outcomes have been validated. It ranks eligible quotes by documented cost only; risk remains unavailable, and a person must review source documents and make every purchasing decision.

Historical project notes reported an experimental model with 89.90% accuracy, 93.65% precision and 39.91% recall. Those figures are not reproduced or verified here. The same notes flagged low recall, possible same-day data leakage, and a prior model-saving error. Recheck the current implementation and evaluation before relying on any model result. The demo and synthetic data are not evidence of supplier performance.

## Decisions to preserve

- Keep synthetic examples clearly separate from real buyer records.
- Do not put credentials or private supplier/buyer information in GitHub.
- Do not let model scores or quote rankings make purchasing decisions.
- Keep the real-quotation pilot alongside the synthetic prototype until real-data permissions and validation are established.

## Next steps

1. Clone this private repository and review the current main branch before continuing.
2. Run the browser demo and record setup or output issues.
3. Verify whether the planned What-If simulation is complete and connected end to end; an earlier project checkpoint listed it as upcoming.
4. Reproduce model results with a chronological, leakage-safe evaluation and document recall/calibration limitations.
5. Define a small, permissioned buyer pilot; reconcile each quote and eligibility result against original documents before considering any risk prediction.

For another GitHub account, the private repository must be shared with that account or cloned through an account that already has access. This commit does not change repository visibility or access.
