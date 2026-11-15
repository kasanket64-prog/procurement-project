"""Rolling chronological backtest for SYNTHETIC delivery-delay experiments.

Four non-overlapping stages in each fold: fit -> calibration -> threshold
selection -> untouched test. Only outcomes available before the NEXT stage
may be used for calibration and threshold selection. No purchasing decisions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             confusion_matrix, f1_score, precision_score, recall_score,
                             roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from procurement_history import CATEGORICAL, NUMERIC, FEATURES, build_features

COST_FALSE_NEGATIVE = 5
COST_FALSE_POSITIVE = 1
CANDIDATE_THRESHOLDS = tuple(i / 100 for i in range(5, 100, 5))
FRACTIONS = ((.45, .55, .65, .75), (.55, .65, .75, .85),
             (.65, .75, .85, None))


def fold_boundaries(features):
    """Three disjoint test windows selected on distinct order dates."""
    dates = pd.DatetimeIndex(sorted(features.order_date.dropna().unique()))
    if len(dates) < 40:
        raise ValueError("Rolling evaluation needs at least 40 distinct order dates.")
    for i, (a, b, c, d) in enumerate(FRACTIONS, 1):
        indices = [int(len(dates) * f) for f in (a, b, c)]
        if d is not None:
            indices.append(int(len(dates) * d))
        if len(set(indices)) != len(indices):
            raise ValueError("Chronological folds need distinct date boundaries.")
        yield i, dates[indices[0]], dates[indices[1]], dates[indices[2]], (
            dates[indices[3]] if d is not None else None)


def matured_window(features, start, end, availability_before):
    """Label must be known at the start of the next stage."""
    mask = ((features.order_date >= start) & (features.order_date < end)
            & features.outcome_available_at.notna()
            & (features.outcome_available_at < availability_before)
            & features.late_delivery.notna())
    return features.loc[mask].copy()


def stage_rows(features, boundaries):
    fold, calibrate_start, validate_start, test_start, test_end = boundaries
    train = features.loc[
        (features.order_date < calibrate_start)
        & features.outcome_available_at.notna()
        & (features.outcome_available_at < calibrate_start)
        & features.late_delivery.notna()
    ].copy()
    calibration = matured_window(features, calibrate_start, validate_start, validate_start)
    validation = matured_window(features, validate_start, test_start, test_start)
    test = features.loc[
        (features.order_date >= test_start)
        & ((features.order_date < test_end) if test_end is not None else True)
        & features.late_delivery.notna()
    ].copy()
    for name, frame in (("training", train), ("calibration", calibration),
                        ("validation", validation), ("test", test)):
        if frame.empty or frame.late_delivery.nunique() < 2:
            raise ValueError(f"Fold {fold}: {name} needs at least two observed classes.")
    assert (train.outcome_available_at < calibrate_start).all()
    assert (calibration.outcome_available_at < validate_start).all()
    assert (validation.outcome_available_at < test_start).all()
    assert (test.order_date >= test_start).all()
    identities = [set(frame.po_id) for frame in (train, calibration, validation, test)]
    if any(identities[i] & identities[j]
           for i in range(len(identities)) for j in range(i + 1, len(identities))):
        raise AssertionError("Fold stages overlap by order ID.")
    return train, calibration, validation, test


def make_model(trees):
    return Pipeline([
        ("features", ColumnTransformer([
            ("categories", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ("numbers", "passthrough", NUMERIC),
        ])),
        ("forest", RandomForestClassifier(n_estimators=trees, random_state=42,
                                           n_jobs=1, class_weight="balanced")),
    ])


def log_odds(prob):
    x = np.clip(np.asarray(prob, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(x / (1 - x)).reshape(-1, 1)


def reliability(y, probability, bins=10):
    """Fixed bins, including the right edge 1; ECE uses actual bin counts."""
    y = np.asarray(y, dtype=int)
    p = np.asarray(probability, dtype=float)
    if len(y) != len(p) or not len(y) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("Invalid labels or probabilities for calibration report.")
    edges = np.linspace(0, 1, bins + 1)
    bucket = np.minimum(np.searchsorted(edges, p, side="right") - 1, bins - 1)
    entries = []
    ece = 0.0
    for idx in range(bins):
        in_bin = bucket == idx
        n = int(in_bin.sum())
        observed = float(y[in_bin].mean()) if n else None
        predicted = float(p[in_bin].mean()) if n else None
        if n:
            ece += (n / len(y)) * abs(observed - predicted)
        entries.append({"from": float(edges[idx]), "to": float(edges[idx + 1]),
                        "count": n, "predicted_mean": predicted, "observed_rate": observed})
    return {"expected_calibration_error": float(ece), "bins": entries}


def choose_threshold(y, probability, *, false_negative_cost=5, false_positive_cost=1):
    """Illustrative, *validation-only* business-cost threshold choice."""
    if false_negative_cost <= 0 or false_positive_cost <= 0:
        raise ValueError("False-negative and false-positive costs must be positive.")
    y = np.asarray(y, dtype=int)
    p = np.asarray(probability, dtype=float)
    if len(y) != len(p) or not len(y) or not set(y).issubset({0, 1}):
        raise ValueError("Invalid validation labels or probabilities.")
    candidate_costs = []
    for threshold in CANDIDATE_THRESHOLDS:
        pred = p >= threshold
        fn = int(((y == 1) & ~pred).sum())
        fp = int(((y == 0) & pred).sum())
        candidate_costs.append((fn * false_negative_cost + fp * false_positive_cost,
                                threshold, fn, fp))
    cost, threshold, fn, fp = min(candidate_costs)
    return {"threshold": threshold, "validation_cost_units": int(cost),
            "validation_false_negatives": fn, "validation_false_positives": fp}


def scores(y, raw, calibrated, threshold, prior):
    y = np.asarray(y, dtype=int)
    p = np.asarray(calibrated, dtype=float)
    pred = (p >= threshold).astype(int)
    matrix = confusion_matrix(y, pred, labels=[0, 1]).tolist()
    return {
        "orders": int(len(y)), "positive_rate": float(y.mean()),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "confusion_matrix_actual_0_1_predicted_0_1": matrix,
        "false_negative_count": int(matrix[1][0]),
        "false_positive_count": int(matrix[0][1]),
        "raw_brier": float(brier_score_loss(y, raw)),
        "calibrated_brier": float(brier_score_loss(y, p)),
        "constant_training_prior_brier": float(brier_score_loss(y, np.full(len(y), prior))),
        "raw_reliability": reliability(y, raw),
        "calibrated_reliability": reliability(y, p),
        "raw_pr_auc": float(average_precision_score(y, raw)),
        "raw_roc_auc": float(roc_auc_score(y, raw)),
    }


def subgroup_metrics(test, probability, threshold):
    """Diagnostics on disjoint test outcomes; no group-specific threshold tuning.

    Small groups are reported but explicitly flagged, never silently promoted
    into reliable subgroup performance claims.
    """
    y = test.late_delivery.astype(int).to_numpy()
    p = np.asarray(probability, dtype=float)
    if len(test) != len(p):
        raise ValueError("Test scores and subgroup rows must have equal lengths.")
    evidence = pd.cut(
        test.supplier_completed_orders,
        bins=[-1, 0, 19, np.inf],
        labels=["no_completed_history", "1_to_19_completed", "20_plus_completed"],
    ).astype(str)
    dimensions = {
        "business_unit": test.business_unit.astype(str),
        "category": test.category.astype(str),
        "supplier_history_evidence": evidence,
    }
    result = {}
    for field, values in dimensions.items():
        groups = []
        for name in sorted(values.unique()):
            mask = np.asarray(values == name)
            targets = y[mask]
            scores_here = p[mask]
            predictions = scores_here >= threshold
            positives = int(targets.sum())
            flagged = int(predictions.sum())
            tp = int(((targets == 1) & predictions).sum())
            fn = positives - tp
            fp = flagged - tp
            groups.append({
                "group": name,
                "orders": int(mask.sum()),
                "late_orders": positives,
                "alerts": flagged,
                "recall": float(tp / positives) if positives else None,
                "precision": float(tp / flagged) if flagged else None,
                "missed_delays": fn,
                "false_alerts": fp,
                "brier": float(brier_score_loss(targets, scores_here)),
                "low_support": len(targets) < 100 or positives < 20,
            })
        result[field] = groups
    return result


def evaluate_rolling(raw, *, trees=20):
    """Retrospective folds: fit never sees later outcomes, even if orders precede cutoff."""
    if not isinstance(trees, int) or trees < 1:
        raise ValueError("trees must be a positive integer.")
    features = build_features(raw)
    folds = []
    for boundaries in fold_boundaries(features):
        fold, calibrate_start, validate_start, test_start, test_end = boundaries
        train, calibration, validation, test = stage_rows(features, boundaries)
        fitted = make_model(trees)
        fitted.fit(train[FEATURES], train.late_delivery.astype(int))
        p_calibration = fitted.predict_proba(calibration[FEATURES])[:, 1]
        cal_model = LogisticRegression(random_state=42, max_iter=1000)
        cal_model.fit(log_odds(p_calibration), calibration.late_delivery.astype(int))
        p_val = fitted.predict_proba(validation[FEATURES])[:, 1]
        calibrated_validation = cal_model.predict_proba(log_odds(p_val))[:, 1]
        selection = choose_threshold(validation.late_delivery, calibrated_validation,
                                     false_negative_cost=COST_FALSE_NEGATIVE,
                                     false_positive_cost=COST_FALSE_POSITIVE)
        p_test = fitted.predict_proba(test[FEATURES])[:, 1]
        calibrated_test = cal_model.predict_proba(log_odds(p_test))[:, 1]
        measured = scores(test.late_delivery.astype(int), p_test, calibrated_test,
                          selection["threshold"], float(train.late_delivery.mean()))
        subgroup = subgroup_metrics(test, calibrated_test, selection["threshold"])
        seen_suppliers = set(train.supplier_id)
        unseen_mask = ~test.supplier_id.isin(seen_suppliers)
        folds.append({
            "fold": fold,
            "calibration_start": str(calibrate_start.date()),
            "validation_start": str(validate_start.date()),
            "test_start": str(test_start.date()),
            "test_end_exclusive": str(test_end.date()) if test_end is not None else None,
            "train_mature_orders": len(train),
            "calibration_mature_orders": len(calibration),
            "validation_mature_orders": len(validation),
            "excluded_pre_calibration_unmatured": int((
                (features.order_date < calibrate_start)
                & ((features.outcome_available_at.isna())
                   | (features.outcome_available_at >= calibrate_start))).sum()),
            "threshold_selection": selection,
            "test_metrics": measured,
            "test_subgroups": subgroup,
            "test_unseen_supplier_orders": int(unseen_mask.sum()),
            "test_unseen_supplier_distinct": int(test.loc[unseen_mask, "supplier_id"].nunique()),
            "train_positive_rate": float(train.late_delivery.mean()),
        })
    return {
        "status": "SYNTHETIC_EXPERIMENT_NOT_REAL_WORLD_VALIDATION",
        "method": "expanding chronological fit, separated calibration, validation and test",
        "folds": folds, "trees_per_fold": trees, "random_seed": 42,
        "false_negative_cost_units": COST_FALSE_NEGATIVE,
        "false_positive_cost_units": COST_FALSE_POSITIVE,
        "cost_ratio_status": "illustrative; not approved by any buyer",
        "threshold_selection": "on validation labels available before test only",
        "calibration_method": "sigmoid on clipped raw score log-odds; fitted on separate mature calibration labels",
        "python": platform.python_version(), "sklearn": sklearn.__version__,
        "limitations": [
            "All scores are on synthetic, retrospectively labeled data, not live buyer outcomes.",
            "Calibration and thresholds must not be deployed without buyer-approved costs.",
            "Test windows are disjoint, but later folds may reuse earlier fold observations as history.",
            "Group diagnostics are synthetic, unadjusted, and not evidence of real-world subgroup reliability.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("dataset/procurement.csv"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--trees", type=int, default=20)
    args = parser.parse_args()
    report = evaluate_rolling(pd.read_csv(args.data, low_memory=False), trees=args.trees)
    report["data_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    report["evaluator_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    encoded = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
