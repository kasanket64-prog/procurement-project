# Recall under a strict false-alert budget

## Decision

**No recall improvement was found at the original false-alert budget. Retain the
original model at threshold 0.50.** This experiment does not promote the earlier
50%-precision policy or replace the application model.

Four candidate configurations were evaluated only on validation data. All four
detect 604 of 1,549 late orders when constrained to at most 32 false alerts, the
original model's validation false-positive count at 0.50. Precision remains
94.97%, recall 38.99%, with 945 late orders missed and 636 alerts in total.
An equal-count threshold change is not treated as an improvement.

## Protocol

The false-alert constraint was stated before fitting the new candidates. Trees
were fitted only on 26,316 mature training orders before 2025-01-01. Candidate
and threshold selection used the same 9,574 mature validation orders before
2025-10-25, including 1,549 late and 8,025 on-time outcomes. The loader discards
test-period rows before parsing their outcomes or constructing history features.
No final-test predictions or metrics were calculated.

Candidates retained the existing 16 input features and as-of history:

1. Original 300-tree Random Forest (no refitting).
2. Random Forest with minimum leaf size 100; other settings retained.
3. Extra Trees: 300 trees, minimum leaf size 5, balanced class weights, seed 42;
   the original one-hot preprocessing is retained.
4. Histogram gradient boosting: 300 iterations, learning rate 0.05, 31 maximum
   leaf nodes, L2 regularization 1, balanced class weights, no early stopping,
   seed 42. Training-fitted ordinal encoding feeds native categorical splits;
   unknown categories become missing values.

There was no broad parameter search, no new dependency, and no model fitting on
validation labels. Scores are thresholded using `>=`; tied scores are not split
to manufacture a favorable alert count. Among feasible thresholds, selection
maximizes detections, then precision, then the threshold. Model ties keep the
earlier, simpler candidate, and the original 0.50 policy is retained on a tie.

## Results and trade-off

| Candidate | Late detected at <=32 false alerts | False alerts | Precision | Recall |
|---|---:|---:|---:|---:|
| Original forest | 604 | 32 | 94.97% | 38.99% |
| Forest, leaf size 100 | 604 | 32 | 94.97% | 38.99% |
| Extra Trees | 604 | 32 | 94.97% | 38.99% |
| Histogram boosting | 604 | 32 | 94.97% | 38.99% |

Diagnostic comparisons at other fixed budgets show the remaining cost:

| Operating point | Late detected | False alerts | Precision | Recall |
|---|---:|---:|---:|---:|
| Original forest, zero-false-alert budget | 41 | 0 | 100.00% | 2.65% |
| Boosting, zero-false-alert budget | 51 | 0 | 100.00% | 3.29% |
| Original forest, 16-false-alert budget | 309 | 16 | 95.08% | 19.95% |
| Larger-leaf forest, 16-false-alert budget | 348 | 16 | 95.60% | 22.47% |
| Original policy | 604 | 32 | 94.97% | 38.99% |
| Boosting, 64-false-alert budget | 611 | 60 | 91.06% | 39.44% |
| Earlier 50%-precision policy | 700 | 696 | 50.14% | 45.19% |

The larger-leaf forest improves recall within the stricter 16-false-alert budget,
but its absolute recall remains below the original 32-false-alert policy. It is
an optional lower-workload trade-off, not a solution to the original low recall.

Boosting offers seven extra detections at 28 extra false alerts: recall rises by
only 0.45 percentage points, while false alerts increase by 87.5%. That is much
less costly than the previous policy, but not a convincing reason to replace the
baseline without an agreed error-cost/review-capacity objective. These results
do not establish that every possible model or feature set has the same limit.

## Evidence and safeguards

The experiment writes `policy.json` with the complete candidate/budget counts and
explicit flags `improved_operating_point: false`, `new_model_saved: false` and
`final_test_scored: false`. No new model artifact is saved when there is no better
operating point. The original model remains unchanged:

`707f607994001e6afddb236dfdf87b83c3f32722150e667f85f581c20bff3840` (SHA-256).

Input CSV SHA-256:
`a6f64c2629fc1983a9e1722d22aa88317a6d1d3dfb6ed2a827eb4d9f1b893b32`.

Reloaded model scores match the selected in-memory validation scores within
absolute tolerance 1e-14; alert decisions match exactly. A separate process
checks the original file hash and reproduces the retained validation counts.

All 20 regression tests pass, including the existing final-test outcome exclusion
test and new checks for exact false-alert budgeting, optimal feasible detection
counts, tied-score behavior and invalid budgets. Compilation and whitespace
checks pass. The comparison uses the previously pinned training environment;
Joblib emitted a nonfatal physical-core detection warning and used logical cores.

Reproduce from the repository root:

```powershell
python ml/compare_low_alert_recall.py --validation-start 2025-01-01 --test-start 2025-10-25 --output validation-runs/low-alert
```

Use a new output directory. A successful run can legitimately report no improvement.
The user-facing evidence archive includes full JSON counts, verification and tests;
it does not contain a replacement model because none is recommended.

## Practical next step and limits

Keep the existing high-precision policy. Before further tuning, agree an actual
review budget and inspect missed-delay examples with a buyer to determine which
verified order-time facts could distinguish them: original lead-time commitments,
known disruption events or verified capacity constraints, for example. These
inputs must be genuinely available at decision time; they cannot be reconstructed
from later outcomes and called predictive evidence.

These experiments reuse the same synthetic validation period, so all candidate
comparisons are exploratory and may contain selection optimism. Earlier baseline
final-test results were already visible in the project history, but no candidate
in this investigation was evaluated there. Main, the trainer, original model,
application defaults and final-test results remain unchanged. No real-world
supplier-risk improvement or calibrated probability claim is established.
