# Rolling temporal backtest — synthetic delivery-delay prediction

**Experimental report, 15 November 2026. Not validated against real buyers or suppliers. Not a release approval.**

Evidence: [GitHub Actions run 43674682489](https://github.com/kasanket64-prog/procurement-project/actions/runs/43674682489) and [archived JSON](https://github.com/kasanket64-prog/procurement-project/actions/runs/43674682489/artifacts/14146071042) (retained 30 days).

Input: `dataset/procurement.csv`; SHA-256 `fba22a467e5dd800a0af960930d2ca5e2ecbd9d2bc747e37304867d8d031ae21`. Backtest evaluator SHA-256 at the reported run: `c4bb49269057d5a2a39c7bbc89b88ade22eef38c9d4af89621db5ba3c05fa548`.

## Reproduce

From the repository root with Python 3.11 and NumPy, pandas and scikit-learn:

```bash
python -m pip install numpy pandas scikit-learn joblib
python -m unittest discover -s tests -p "test_rolling_backtest.py" -v
python ml/backtest_delivery_risk.py --trees 20 --output rolling-backtest.json
```

This script evaluates the *synthetic dataset*, not supplier quotations or real procurement history. The result includes its data and evaluator digest, scikit-learn version, fold boundaries, stage counts, and fixed reliability-bin reports.

## Evaluation protocol

Each of **three** expanding chronological folds has four non-overlapping order-date intervals. A fixed-seed 20-tree random forest fits only on orders with delivery outcomes known **strictly before** the calibration interval. A separate sigmoid calibrator fits on scores and outcomes available before validation starts. A threshold is chosen solely using validation outcomes available before test starts. The final test interval is not used to fit, calibrate, or choose that fold's threshold.

The threshold grid is 0.05–0.95 in 0.05 steps. The demonstration cost ratio is **5 missed delays : 1 false alert**; this ratio was chosen for the experiment, **not approved by any buyer**, and is not an operating policy. The test windows do not overlap, although a later fold can use historical outcomes from earlier folds once those outcomes have matured.

Training uses `procurement_history.build_features`, which constructs the features available as of the start of each order date. All final test labels are used retrospectively for evaluation only.

## Results

| Test period (start inclusive) | Orders | Late-delivery rate | Validation-selected threshold | Precision | Recall | Missed delays | False alerts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2025-04-10 to 2025-08-15 | 4,337 | 16.28% | 0.30 | 85.63% | **38.81%** | 432 | 46 |
| 2025-08-15 to 2025-12-21 | 5,417 | 16.41% | 0.30 | 87.95% | **38.58%** | 546 | 47 |
| 2025-12-21 to dataset end | 6,782 | 16.25% | 0.40 | 93.76% | **40.93%** | 651 | 30 |

The model misses approximately **six in ten known late deliveries** in each time window. High precision means the alerts it does produce tend to be correct; it does *not* mean it catches most disruptions.

### Probability calibration and discrimination

| Test window | Raw Brier | Calibrated Brier | Training-prior Brier | Raw ECE | Calibrated ECE | Raw ROC-AUC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.1199 | **0.1098** | 0.1363 | 0.1287 | **0.0638** | 0.7069 |
| 2 | 0.1162 | **0.1103** | 0.1372 | 0.1151 | **0.0686** | 0.6847 |
| 3 | 0.1144 | **0.0961** | 0.1361 | 0.1239 | **0.0466** | 0.7161 |

Brier score and expected calibration error (ECE) are lower-is-better here. ECE uses ten fixed probability bins and is sensitive to binning and sample size; it is diagnostic, not proof of real-world calibration. Calibration improved both diagnostics in these synthetic windows, **but missed-delay recall remains inadequate**.

## Severe product-category failures and missing cold-start evidence

The latest CI artifact also reports pre-specified subgroup diagnostics (business unit, product category, supplier completed-order history) using the **same validation-selected threshold**. No category-specific threshold was tuned on the test sets. Groups with fewer than 100 orders or 20 late-delivery events are labeled low support.

| Category | Late deliveries across the three disjoint test windows | Detected by selected threshold | Observed recall |
| --- | ---: | ---: | ---: |
| Chemicals | 185 | **0** | **0%** |
| Logistics | 207 | **0** | **0%** |
| Professional Services | 114 | **0** | **0%** |
| MRO | 777 | approximately 606 | approximately 78% |

The model entirely missed **506** known late deliveries in the first three categories, despite detecting many MRO delays. This is evidence of serious *synthetic-data subgroup disparity*, not a claim about actual industries. The cause has not been established; the dataset-generation process, group prevalence, feature selection, and threshold behavior all need investigation. **Do not generalize this model to procurement categories with zero detected delays.**

Across all three test intervals, **zero orders belonged to suppliers absent from the fold's training supplier-ID set**. Therefore this backtest provides **no cold-start/new-supplier performance evidence**. Only a handful of supplier observations had fewer than 20 completed historical orders; those groups are labeled low support. Missing cold-start coverage must not be represented as a passing test.

## Release-blocking limitations

- **Do not deploy this threshold/model to the live quotation pilot** or portray scores as supplier reliability.
- A 5:1 false-negative-to-false-positive cost ratio is an illustrative choice; actual operating policy requires buyer input, capacity and escalation consequences.
- Address the measured category-level failure, obtain genuine cold-start supplier examples, and examine data drift. An aggregated synthetic result can conceal severe subgroup failures.
- Reproduce on independently sourced, permissioned delivery histories with reliable order, promise, outcome and *information-availability* timestamps.
- Keep quotation decisions and purchase authorization under human control.
- Calibration was fitted on held-out synthetic intervals; transportability to actual suppliers remains unknown.

**Conclusion:** The evaluation machinery is now reproducible and temporally separated. The predictive component is **not release-ready**.
