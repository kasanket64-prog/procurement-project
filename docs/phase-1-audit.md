# Phase 1 audit: verified baseline (15 November 2026)

Scope: [draft PR #19](https://github.com/kasanket64-prog/procurement-project/pull/19), branch `test/point-in-time-history-regression`. This is a **prototype validation record**, not evidence of live procurement performance.

## Executed checks

Latest verified CI commit: `4c4b7ca506d95bcbf3cd9cc14deed913e7860c39`.

GitHub Actions run [43673876992](https://github.com/kasanket64-prog/procurement-project/actions/runs/43673876992) passed on Python 3.11 / Ubuntu:

- 5 supplier-history point-in-time regression tests.
- 6 terminal What-If isolation and comparison tests.
- 1 terminal demo ranking regression test.
- 3 no-mock supplier-risk and What-If integration tests.
- 4 synthetic-fixture quotation-review and human-approval invariant tests.
- 3 temporal ML evaluation tests.
- 4 headless Chromium browser smoke tests, including a budget-normalization regression and request draft generation.

**26 tests passed; 0 failed.** The ML job also trained and evaluated a 40-tree random forest on the committed synthetic dataset. No live suppliers, real buyer outcomes, or purchasing authorization were validated.

## Reproduced and fixed

1. Browser experience-score normalization changed whenever a budget excluded a supplier. Headless browser regression reproduced a remaining supplier's experience contribution moving from 2.5 to 16.67 when only the budget changed. `ml/procurement_platform_template.html` now benchmarks experience against the product/country population before the budget eligibility filter.
2. The terminal demo had the corresponding issue. `ml/supplier_matcher.py` now takes its experience benchmark from the product/country population independent of budget. A regression guards that behavior.
3. `ml/procurement_history.py` used a deprecated pandas weekday accessor; migrated to `.dt.day_of_week`. Latest regression logs contain no `Pandas4Warning`.

## Remaining risks and release gates

**P0 — Evaluation evidence and real-world validation**
- The *exact historical* model figures have **not** been independently reproduced. A new point-in-time holdout evaluation is reproducible for the specified configuration; see [model evaluation and confusion matrix](model-evaluation.md). At a fixed 0.5 threshold, **recall was 39.97%** and 943 of 1,571 late deliveries were missed.
- Legacy training scripts such as `ml/train_improved_model.py` accumulate historical delivery outcomes by **order date**, not by when the outcomes became known; this can leak future completion information into features. Do not label those historical results 'leakage-free' without rebuilding on `ml/procurement_history.py` and verifying chronological evaluation.
- Synthetic supplier performance is not real supplier capacity, active inventory, or committed delivery. The real-quotation engine only reviews operator-declared data and explicitly does not authorize purchases.

**P1 — More integration coverage**
- **Completed:** no-mock supplier-risk recommendation and scenario integration tests, plus a reproducible experimental temporal holdout command with data/evaluator hashes.
- **Still needed:** boundary-case RFQ browser tests; rolling temporal ML backtests; a separate validation period for threshold selection and calibration; subgroup drift checks.
- **Not approved:** saving or deploying the experimental model in the real-quotation pilot, or treating its scores as purchase decisions.

**P2 — Maintenance**
- Review pinned dependency versions and GitHub Action runner compatibility.
- Keep generated `ml/procurement_platform.html` separate from source template review; the test suite currently generates its own temporary HTML file.

## Merge policy

Do not merge this draft PR merely because 26 automated tests are green. Review the source diff, confirm all CI checks at the final SHA, then merge only by explicit maintainer decision. Do not interpret these tests as validation of prediction accuracy or purchasing decisions.
