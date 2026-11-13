# Corrected trainer: reproduced synthetic experiment

Training code: `1b06adda0648430e3aa773af5b62576b1dcc90f1`, branch `fix/trainer-leakage-split`.
Run and verified on 13 November 2026. Main was not changed.

## Command and environment

From the repository root, in an isolated Python 3.12.14 environment:

```powershell
python ml/train_improved_model.py --validation-start 2025-01-01 --test-start 2025-10-25 --as-of 2026-11-13
```

Verified versions: NumPy 2.3.5, pandas 2.2.3, scikit-learn 1.6.1, SciPy 1.15.2,
Joblib 1.4.2, threadpoolctl 3.6.0, python-dateutil 2.9.0.post0, pytz 2025.2,
tzdata 2025.2 and six 1.17.0. Package wheels were downloaded from official PyPI,
verified against published SHA-256 hashes, and installed locally. `pip check`
reported no broken requirements. All 11 regression tests passed in 0.254 seconds.

Input `dataset/procurement.csv` SHA-256:
`a6f64c2629fc1983a9e1722d22aa88317a6d1d3dfb6ed2a827eb4d9f1b893b32`.

## Partitions

| Partition | Rows | Included order dates | Latest included outcome availability |
|---|---:|---|---|
| Training | 26,316 | 2023-01-01 to 2024-12-26 | 2024-12-31 |
| Validation | 9,574 | 2025-01-01 to 2025-10-18 | 2025-10-24 |
| Final test | 9,440 | 2025-10-25 to 2026-06-30 | 2026-08-12 |

Of 47,128 input rows, 1,798 miss a partition's maturity/window requirements.
Calendar boundaries are exclusive for outcome availability. The shared builder
uses only outcomes available before each order day. With this dataset, missing
explicit disclosure timestamps are assumed to equal completion dates; this is
not independently verified real-world disclosure evidence.

## Final-test results

The threshold was fixed at 0.50 before running. Threshold diagnostics use only
validation data; there was no tuning or refitting based on final-test results.

| Metric | Result |
|---|---:|
| Accuracy | 0.8991525423728813 |
| Precision for late delivery | 0.936923076923077 |
| Recall for late delivery | 0.4006578947368421 |
| F1 | 0.5612903225806452 |
| ROC-AUC | 0.7061215360845295 |
| Average precision | 0.542155509540257 |
| Brier score | 0.09354541902071563 |
| Always-on-time accuracy baseline | 0.8389830508474576 |
| Constant training-prevalence Brier baseline | 0.135090723329747 |

The trainer labels average precision as PR-AUC; this value is average precision,
not a separately calculated trapezoidal area. Lower Brier score is better, but
the Brier comparison alone does not establish probability calibration.

Confusion matrix, rows = actual and columns = predicted, class order `[0, 1]`:

```text
[[7879,  41],
 [ 911, 609]]
```

There are 1,520 late orders: 609 detected and 911 missed. High precision and
accuracy therefore coexist with approximately 60% of late orders being missed.

## Saved-model verification

The unchanged trainer saved `models/delivery_risk_model_clean.pkl` successfully:
227,956,210 bytes (217.4 MiB), 300 trees, 16 expected input columns, classes `[0, 1]`.
Training plus the first serialization checks took 24.75 seconds in this environment.

Saved model SHA-256:
`707f607994001e6afddb236dfdf87b83c3f32722150e667f85f581c20bff3840`.

The model was reloaded using Joblib. Its probabilities across all 9,440 test rows
matched the in-memory model within absolute tolerance 1e-14. Class predictions
and the trainer's fixed-threshold decisions also matched. A fresh Python process
checked the file hash, rebuilt features and partitions, reloaded the artifact,
matched the reference probabilities and independently reproduced the metrics above.
The generated model remains excluded from Git; it is included in the local
user-facing results archive with raw logs, a run manifest and pinned versions.

## Limits

These are reproduced synthetic results, not validation on real buyer/supplier
outcomes. This run does not reproduce the historical experiment exactly because
the history construction and partitioning changed. No threshold optimization,
calibration study, confidence intervals, hardware benchmarking or new-supplier
evaluation was performed. Other experimental trainers remain uncorrected.
Legacy callers retaining older history definitions were not validated here.
Purchasing approval must remain with a human.
