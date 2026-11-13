# Low-recall investigation: validation only

All model/threshold choices below use the 9,574 mature validation orders from
2025-01-01 through 2025-10-18, with outcomes available before 2025-10-25.
There are 1,549 late and 8,025 on-time orders. No final-test predictions or metrics
were calculated in this investigation. The baseline final test had already been
reported in the previous experiment; this does not turn that previously viewed
test into a new unseen dataset.

## What explains the misses

At threshold 0.50, the original model detects 604 late orders and misses 945.
Of those misses, 273 score below 0.10, 410 between 0.10 and 0.15, 187 between
0.15 and 0.20, 74 between 0.20 and 0.30, and only one between 0.30 and 0.50.
Thus 870/945 misses (92.1%) are below 0.20. The median score of an actual late
order is 0.1667. Simply changing 0.50 to 0.30 barely improves recall.

At 0.50 the original model misses all validation late orders in Chemicals
(93/93), Logistics (121/121), Machinery (32/32) and Professional Services
(74/74), while catching 351/445 in MRO. These are descriptive synthetic subgroup
results, not evidence of actual sector risk or a causal explanation of delays.

The scores strongly separate some late orders but leave many others intermingled
with on-time orders. The small benefit from changing leaf size below supports
the practical conclusion that threshold tuning alone does not solve detection.
Whether better real order-time evidence would improve ranking remains untested.

## Precision–recall trade-off

All numbers in this table are **validation** results. Alerts are out of 9,574 orders.

| Model / operating rule | Threshold | Precision | Recall | Late detected | False alerts | Late missed | Total alerts |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original, existing threshold | 0.50 | 94.97% | 38.99% | 604 | 32 | 945 | 636 |
| Original, recall maximized at >=90% precision | 0.32 | 92.79% | 39.06% | 605 | 47 | 944 | 652 |
| Original, recall maximized at >=75% precision | 0.243333 | 78.46% | 40.22% | 623 | 171 | 926 | 794 |
| Original, recall maximized at >=50% precision | 0.196667 | 51.92% | 44.42% | 688 | 637 | 861 | 1,325 |
| Leaf size 20, recall maximized at >=50% precision | 0.396334 | 50.29% | 44.61% | 691 | 683 | 858 | 1,374 |
| Leaf size 100, recall maximized at >=50% precision | 0.416515 | 50.14% | 45.19% | 700 | 696 | 849 | 1,396 |
| Original, lower fixed threshold | 0.15 | 27.94% | 55.91% | 866 | 2,233 | 683 | 3,099 |
| Original, lower fixed threshold | 0.10 | 18.48% | 82.38% | 1,276 | 5,629 | 273 | 6,905 |
| Original, maximum F2 | 0.063333 | 16.51% | 97.22% | 1,506 | 7,613 | 43 | 9,119 |

Thresholds are rounded for display only. Use the exact threshold in the saved
policy, and do not transfer thresholds between models.

## Provisional improvement and its cost

The initial recall-oriented rule, maximum validation F2, flags 95.2% of all
orders. Its precision is only slightly above the 16.18% validation prevalence.
This is a measured trade-off, not a useful default recommendation merely because
recall is high.

After observing that operational cost, an explicit **provisional** guardrail was
used for two limited model comparisons: maximize validation recall while keeping
precision at least 50%. The 50% floor means roughly no more than one false alert
per correctly detected delay in this validation sample. It was not supplied or
approved by a buyer and does not guarantee future precision.

Two candidates changed only `min_samples_leaf` to 20 or 100, retaining the existing
300 trees, seed 42, balanced class weights, feature definitions and preprocessing.
They were fitted only on the same 26,316 mature training orders before 2025-01-01.
Validation was used to choose the threshold and candidate, never to fit trees.

Leaf size 100 with exact threshold **0.4165148635841162** wins this constrained
comparison. Relative to the old model at 0.50, recall rises by 6.20 percentage
points, detecting 96 additional delays, but adds 664 false alerts. Total alerts
rise from 636 (6.64% of orders) to 1,396 (14.58%). Precision falls from 94.97% to
50.14%. It still misses 849 late orders (54.81%).

Most of the gain comes from the operating threshold. Compared with tuning the
original model under the same 50% precision floor, larger leaves add just 12
detections and 59 false alerts: recall improves by only 0.77 percentage points.
That small model gain is not independently confirmed. Keeping the original model
and using threshold 0.19666666666666666 is the simpler alternative if its slightly
better validation precision and lower alert volume are preferred.

The selected configuration is an experimental review policy, not an automatic
application change or a purchasing recommendation. Business error costs and
review capacity must determine whether this trade-off is acceptable.

## Artifacts, reproducibility and tests

`validation-recall-policy.json` records the exact policy, model hashes, candidate
counts and selection rule. The user-facing archive contains `selected-model.pkl`,
the policy, the complete original-model threshold curve, diagnostics and test logs.
The original saved model was not overwritten.

Source model SHA-256:
`707f607994001e6afddb236dfdf87b83c3f32722150e667f85f581c20bff3840`.

Selected model SHA-256:
`333f5d80e5f7cc0a9fe71562f9d8cb9ab762311fb8deb36cf484ab52c46ecf23`.

The selected model is 1,809,709 bytes (compressed Joblib). Its validation
probabilities matched before/after serialization within 1e-14, and threshold
decisions matched exactly. A fresh Python process independently reloaded it,
reproduced the selected validation counts and confirmed the original model hash.
For reproducible threshold boundaries, scoring uses fixed tree order (`n_jobs=1`).

Apply the sidecar policy explicitly:

```python
scores = model.predict_proba(X)[:, list(model.classes_).index(policy['positive_class'])]
late_alert = scores >= policy['threshold']
```

The model pipeline's ordinary `predict()` still uses threshold 0.50. Existing
interfaces and the supplier-history risk baseline were not changed.

Reproduce with the commands under “Investigate recall without scoring the final
test” in README. Use the pinned environment recorded by the corrected-trainer
report (Python 3.12.14, scikit-learn 1.6.1, pandas 2.2.3, NumPy 2.3.5 and Joblib 1.4.2).
The comparison command writes to a new directory and refuses to overwrite it.

All 17 regression tests pass. New coverage checks threshold/count consistency,
precision-constrained selection, invalid probabilities and dates, and final-test
exclusion using a deliberately invalid test-period outcome that would fail if
parsed. Compilation and whitespace checks pass. The local test runner required
a writable workspace temporary directory because its default temporary directory
denied file creation; that was an environment setting, not a skipped test.

## Limits and next decision

These are adaptively selected validation results on synthetic data. Selection
optimism, subgroup uncertainty, calibration and drift remain unmeasured. Neither
the threshold-only alternative nor the selected candidate has a newly reported
final-test result. Main and the existing trainer were not changed.

Choose the acceptable precision/review workload before approving a policy. For
independent evaluation after further development, prefer a genuinely future,
permissioned dataset. No confidence interval or real-world performance claim is
made here, and no final-test access is needed to review this trade-off.
