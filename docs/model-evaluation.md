# Synthetic delivery-risk evaluation — 15 November 2026

**Status: reproducible experimental baseline, NOT validated supplier prediction.**

- Code: `ml/evaluate_delivery_risk.py`
- Input: `dataset/procurement.csv` (synthetic records)
- Evidence: [GitHub Actions run 43673552706](https://github.com/kasanket64-prog/procurement-project/actions/runs/43673552706)
- [Download the archived evaluation JSON](https://github.com/kasanket64-prog/procurement-project/actions/runs/43673552706/artifacts/14144634077) (GitHub retention: 30 days)
- Data SHA-256: `fba22a467e5dd800a0af960930d2ca5e2ecbd9d2bc747e37304867d8d031ae21`
- Evaluator SHA-256: `2bf5fc32926b68b84e0309aecf56ccdd8d3a2b4a588ce48b87edf2b9fa76e8e5`
- Environment: Python 3.11.18, scikit-learn 1.9.1, random seed 42, random forest with 40 trees
- Decision-time cutoff: **2025-10-18** (orders on that date belong to the holdout)
- Operating threshold: **none selected**. The reported 0.5 classification threshold is a fixed experimental comparator, not a buyer-approved alert policy.

## Reproduction

From the repository root after installing NumPy, pandas, scikit-learn and joblib:

```bash
python ml/evaluate_delivery_risk.py --trees 40 --output evaluation.json
```

The script hashes its input and evaluator, captures scikit-learn and Python versions, and emits machine-readable performance and temporal-split details. The GitHub Actions workflow runs three independent evaluation-invariant tests and archives the JSON.

## What was checked

1. Source features are built by `procurement_history.build_features`: completed delivery outcomes are included only after their availability date, and not for predictions at the start of that date.
2. All training orders are **strictly before** the cutoff and have outcomes **known strictly before** the cutoff.
3. The holdout contains orders placed on or after the cutoff; their eventual labels are read retrospectively to score predictions. Some earlier orders lacking mature outcomes were excluded from fitting.
4. Preprocessing fits only on mature training rows. Random forest uses a fixed random seed; the 0.5 threshold was not tuned on the holdout.

This resolves the specific *known training-label maturity* problem, but a single split cannot establish future operational reliability.

## Verified results (synthetic holdout)

| Measure | Result |
| --- | ---: |
| Mature training orders | 36,525 |
| Labeled holdout orders | 9,744 |
| Earlier orders omitted because outcomes were not mature | 859 |
| Late deliveries in holdout | 1,571 (16.12%) |
| True negatives | 8,094 |
| False positives | 79 |
| False negatives | **943** |
| True positives | 628 |
| Accuracy | 89.51% |
| Precision | 88.83% |
| **Recall** | **39.97%** |
| F1 | 55.14% |
| ROC-AUC | 0.706 |
| Average precision (PR-AUC) | 0.534 |
| Brier score (lower is better) | 0.1137 |
| Constant prior Brier | 0.1352 |

An always-on-time classifier would achieve about **83.88% accuracy** on this holdout while missing *every* late delivery. Therefore, accuracy alone is a poor release criterion.

At a 0.5 threshold, this experimental model missed approximately **60% of known late deliveries**, despite high precision. There is **no justification for deploying this as an autonomous disruption warning**.

## Outstanding gates

1. Reproduce results under a **rolling temporal backtest** and report variability between time windows and business segments.
2. Use a separate chronological **validation** interval to select an alert threshold using an explicitly approved false-negative/false-positive cost tradeoff. Never tune on the final holdout.
3. Assess probability calibration and class prevalence drift, including new suppliers and suppliers with no mature history.
4. Validate on licensed, permissioned real buyer data with documented availability timestamps and agreed evaluation criteria.
5. Keep all purchasing and quotation acceptance decisions under human review.

**Legacy training scripts:** `ml/train_improved_model.py`, `ml/train_v3_model.py` and related experiments are not the validated evaluator. Some build supplier-history labels from earlier *order dates* rather than outcome-availability dates. Do not cite their historical accuracy as a leakage-free result without independent reproduction.
