# Leakage-safe feature investigation

## Result and recommendation

**Recent delivery history gives a small measured validation gain: one additional
late order detected with no additional false alerts. This is not a material or
independently confirmed improvement. Keep the existing application model.**

At the original budget of 32 false alerts, recall changes from 38.99% to 39.06%
(+0.0646 percentage points) and precision from 94.97% to 94.98%. The new policy
detects all 604 late orders detected by the baseline plus one more. The 32 false
alerts are exactly the same orders, not merely an equal count. It still misses
944 of 1,549 late validation orders.

## Scope and leakage controls

Models fit only the existing 26,316 mature training orders before 2025-01-01.
Selection uses 9,574 mature validation orders with outcomes known before
2025-10-25. Final-test rows are removed before their outcome fields are parsed
or any history features are built. No final-test predictions or metrics were
calculated. Model and threshold selection reused validation, not an independent
evaluation period.

Three feature groups were specified before comparing candidates:

| Group | Inputs and timing |
|---|---|
| Workload (5) | Existing completed/open/overdue counts, plus open/previous and overdue/open shares. Only previously placed orders and outcomes known before the decision day contribute. |
| Recent history (5) | Completed count and late fraction for disclosure dates in `[day-30, day)` and `[day-90, day)`, plus average disclosed delay in the 90-day window. |
| Supplier-item history (7) | Prior placements, known completed count, late fraction and average delay for the exact supplier/item pair; current quantity, unit price and promised lead time relative to means of strictly earlier placements for that pair. |

Empty history has count/rate zero. Order-to-history ratios use neutral value one
when no positive historical mean exists; the previous-order count provides
history context. Same-day placements are excluded together, and same-day outcome
disclosures are excluded. All features must be finite. The source frame and
existing base-feature values remain unchanged.

Current-order completion, delay, late label, quality rejection, order IDs and
supplier names are excluded from candidate inputs. Quality rejection has no
documented availability timestamp, so it was not added as historical evidence.
The synthetic source has no independently verified disruption, capacity or
promise-revision records; none were invented.

The loader deliberately builds features from **all pre-test orders** before
excluding immature training/validation labels. Otherwise open or not-yet-mature
orders would disappear from workload and placed-order histories. Tests explicitly
cover this distinction.

## Fixed candidate comparison

The original 16-feature model is frozen. Four Random Forest ablations retain the
same 300 trees, seed 42, balanced class weights and preprocessing, adding one
group or all groups. A histogram-boosting candidate uses all groups with the
previous experiment's fixed settings. No hyperparameter search or new dependency
was introduced. The false-alert constraint remains 32, fixed before comparison.

| Candidate | Input columns | Late detected | False alerts | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| Original | 16 | 604 | 32 | 94.97% | 38.99% |
| Forest + workload | 21 | 604 | 32 | 94.97% | 38.99% |
| Forest + recent history | 21 | 605 | 32 | 94.98% | 39.06% |
| Forest + supplier-item history | 23 | 604 | 32 | 94.97% | 38.99% |
| Forest + all groups | 33 | 604 | 32 | 94.97% | 38.99% |
| Boosting + all groups | 33 | 604 | 32 | 94.97% | 38.99% |

The provisional selected artifact is `forest_recent`, exact threshold
`0.38333333333333336`. Its confusion matrix, actual rows / predicted columns,
class order `[0, 1]`, is:

```text
[[7993,  32],
 [ 944, 605]]
```

There is some value at tighter diagnostic budgets: supplier-item history detects
395 late orders with 16 false alerts (25.50% recall), versus 309 with 16 for the
original model (19.95%). Recent history detects 392 with 15 false alerts. These
are lower-workload options, but their absolute recall remains below the original
32-false-alert policy. They are not a solution to the primary low-recall problem.

## Verification and correction

All 29 regression tests pass. Eight new feature tests cover disclosure gating,
same-day exclusions, 30/90-day boundaries, product isolation, past order-time
aggregates, future-outcome isolation, neutral defaults/base-column preservation,
and immature-order retention plus final-test exclusion. Compilation and
whitespace checks pass.

This investigation exposed a false-alert selector edge case: deriving alert
counts from `TP / precision` incorrectly yields zero when both TP and precision
are zero but false alerts exist. The selector now counts scores at or above each
threshold directly. A regression test covers the failing case. The affected
feature comparison was rerun after the correction; all reported diagnostic
points respect their false-alert budgets, including zero. Preliminary outputs
are excluded from the delivered evidence archive.

The provisional selected model was saved separately, reloaded and checked against
in-memory probabilities (absolute tolerance 1e-14) with identical alert decisions.
A fresh Python process reconstructed only development features and reproduced
the selected validation counts and alert overlap. Scoring uses fixed tree order
for stable threshold boundaries. The original model hash is unchanged.

Selected model: 44,300,169 bytes, compressed Joblib, 21 expected input columns.
SHA-256: `52c332ad2c1d692f24c981c799cfccca092298e6474c0833292cfe0e6682ce1c`.

Original model SHA-256:
`707f607994001e6afddb236dfdf87b83c3f32722150e667f85f581c20bff3840`.

Input CSV SHA-256:
`a6f64c2629fc1983a9e1722d22aa88317a6d1d3dfb6ed2a827eb4d9f1b893b32`.

`leakage-safe-features-policy.json` records complete group definitions, input
columns, exact threshold, model hashes and every candidate/budget count. The
user-facing archive includes the separately saved model, policy, tests and
verification. This is an experimental artifact, not an application replacement.

## Reproduction and use

Use the previously pinned environment (Python 3.12.14, pandas 2.2.3, NumPy 2.3.5,
scikit-learn 1.6.1, SciPy 1.15.2 and Joblib 1.4.2), then run from repository root:

```powershell
python ml/compare_low_alert_recall.py --experimental-features --validation-start 2025-01-01 --test-start 2025-10-25 --output validation-runs/history-features
```

Use a new output directory. To reproduce validation decisions, load development
data with `load_development(..., feature_builder=build_experiment_features)`, use
the policy's `selected_features`, and compare class-1 probability with its exact
threshold using `>=`. Ordinary pipeline `predict()` still uses 0.50. Existing
inference callers do not supply the new history columns automatically.

## Practical conclusion and limits

The available synthetic histories did not provide a convincing improvement at
the current alert budget. The one-order gain may be selection noise after many
experiments on this same validation period. It is not evidence that all possible
features fail, and it does not justify claiming higher real-world recall.

For real use, open/overdue features describe what was recorded as known, not
verified physical capacity. Recent windows track disclosure time, not necessarily
actual completion time. Missing disclosure timestamps still default to completion
dates in this dataset. Product/price comparisons assume stable identity, unit and
currency within the synthetic supplier-item pair; genuine records need explicit
IDs, units, currency and original/revised promise provenance.

Keep the current model and seek verified decision-time evidence tied to actual
delay mechanisms, with permissioned buyer records and a genuinely future
evaluation period. Do not add post-delivery quality, final promise revisions or
invented capacity indicators to improve an experimental score. Main, the original
trainer/model, app defaults and final-test results remain unchanged.
