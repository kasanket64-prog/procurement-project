# Phase 1 audit: verified baseline (15 November 2026)

Scope: [draft PR #19](https://github.com/kasanket64-prog/procurement-project/pull/19), branch `test/point-in-time-history-regression`. This is a **prototype validation record**, not evidence of live procurement performance.

## Executed checks

Latest verified CI commit covering code and tests: `f18af07ac6eb616418eb91bbee683f87ebebfc0b`.

GitHub Actions run [43674937779](https://github.com/kasanket64-prog/procurement-project/actions/runs/43674937779) passed on Python 3.11 / Ubuntu:

- 5 supplier-history point-in-time regression tests.
- 6 terminal What-If isolation and comparison tests.
- 1 terminal demo ranking regression test.
- 3 no-mock supplier-risk and What-If integration tests.
- 4 synthetic-fixture quotation-review and human-approval invariant tests.
- 3 single-holdout temporal ML evaluation tests.
- 7 rolling-backtest tests: disjoint chronological stages, maturity, calibration bins, validation-only thresholds, future-label isolation and subgroup accounting.
- 7 headless Chromium browser tests, including stable budget ranking, RFQ preview with no outbound request, invalid timezone and past-date rejection, and preview invalidation on edit.

**36 tests passed; 0 failed.** The CI also evaluated the 40-tree fixed-threshold model and a separate three-window 20-tree chronological backtest with calibrated scores and validation-selected illustrative thresholds. No live suppliers, real buyer outcomes, or purchasing authorization were validated.

## Reproduced and fixed

1. Browser experience-score normalization changed whenever a budget excluded a supplier. Headless browser regression reproduced a remaining supplier's experience contribution moving from 2.5 to 16.67 when only the budget changed. `ml/procurement_platform_template.html` now benchmarks experience against the product/country population before the budget eligibility filter.
2. The terminal demo had the corresponding issue. `ml/supplier_matcher.py` now takes its experience benchmark from the product/country population independent of budget. A regression guards that behavior.
3. `ml/procurement_history.py` used a deprecated pandas weekday accessor; migrated to `.dt.day_of_week`. Latest regression logs contain no `Pandas4Warning`.

## Remaining risks and release gates

**P0 — Evaluation evidence and real-world validation**
- [Rolling-backtest report](rolling-backtest.md): late-delivery recall was 38.58–40.93% across three synthetic test windows; **Chemicals, Logistics and Professional Services had zero detected late deliveries** in all three, totaling **506 missed delays**. The test contains **no unseen suppliers**. Neither category-level reliability nor cold-start ability is established.
- Probability calibration improved synthetic Brier/ECE in all three folds, but this did not resolve missed-delay recall. The 5:1 missed-delay versus false-alert cost is illustrative and **not buyer approved**.
- The *exact historical* model figures have **not** been independently reproduced. A new point-in-time holdout evaluation is reproducible for the specified configuration; see [model evaluation and confusion matrix](model-evaluation.md). At a fixed 0.5 threshold, **recall was 39.97%** and 943 of 1,571 late deliveries were missed.
- Legacy training scripts such as `ml/train_improved_model.py` accumulate historical delivery outcomes by **order date**, not by when the outcomes became known; this can leak future completion information into features. Do not label those historical results 'leakage-free' without rebuilding on `ml/procurement_history.py` and verifying chronological evaluation.
- Synthetic supplier performance is not real supplier capacity, active inventory, or committed delivery. The real-quotation engine only reviews operator-declared data and explicitly does not authorize purchases.

**P1 — More integration coverage**
- **Completed:** no-mock supplier-risk recommendation and scenario integration tests, plus a reproducible experimental temporal holdout command with data/evaluator hashes.
- **Still needed:** broader quotation and browser security tests, root-cause analysis for zero-recall categories, representative unseen-supplier evaluation, drift checks, and genuine data validation. The rolling test already separates calibration, threshold validation, and final holdout.
- **Not approved:** saving or deploying the experimental model in the real-quotation pilot, or treating its scores as purchase decisions.

**P2 — Maintenance**
- Review pinned dependency versions and GitHub Action runner compatibility.
- Keep generated `ml/procurement_platform.html` separate from source template review; the test suite currently generates its own temporary HTML file.

## Merge policy

### Public delivery research added after the baseline

[Public delivery-data research](public-delivery-research.md) now records a local descriptive analysis of 10,324 historical SCMS line items obtained through a pinned public mirror. Scheduled and actual client-delivery dates are available, but source authenticity, conflicting reuse metadata, schedule revisions and feature-availability history remain unresolved. The analysis distinguishes line items from ASN/DN groups and does not train or deploy a model, rank suppliers, or validate the real-quotation pilot. Original baseline results and release gates above remain applicable. Full data analysis was local; CI covers date accounting and rejection of an unreviewed input file with controlled fixtures.

Do not merge this draft PR merely because 36 automated tests are green. Review the source diff, confirm all CI checks at the final SHA, then merge only by explicit maintainer decision. Do not interpret these tests as validation of prediction accuracy or purchasing decisions.
