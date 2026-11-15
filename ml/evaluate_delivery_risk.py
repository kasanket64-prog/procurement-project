"""Reproducible, point-in-time delivery-delay evaluation on synthetic data.

This evaluator is an experiment, NOT the real-quotation pilot or proof that a
supplier will deliver on time. It trains only on order labels whose outcomes
were available strictly before the chronological test cutoff.
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
from sklearn.metrics import (
    accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from procurement_history import CATEGORICAL, FEATURES, NUMERIC, build_features


def split_mature_orders(features, cutoff=None):
    """Split by order date; only previously *known* labels train the model.

    When no cutoff is supplied, choose the start of the last chronological
    quintile of UNIQUE order dates (so an entire day goes to one side).
    """
    dates = pd.DatetimeIndex(sorted(features.order_date.dropna().unique()))
    if len(dates) < 5:
        raise ValueError("Need at least five distinct order dates for a temporal holdout.")
    boundary = pd.Timestamp(cutoff).normalize() if cutoff is not None else dates[int(len(dates) * .8)]
    train = features.loc[
        (features.order_date < boundary)
        & features.outcome_available_at.notna()
        & (features.outcome_available_at < boundary)
        & features.late_delivery.notna()
    ].copy()
    test = features.loc[
        (features.order_date >= boundary) & features.late_delivery.notna()
    ].copy()
    if train.empty or test.empty:
        raise ValueError("No mature training orders or labeled held-out orders at cutoff.")
    if train.late_delivery.nunique() < 2:
        raise ValueError("The mature training set must include both delivery outcomes.")
    if not (train.order_date < boundary).all() or not (train.outcome_available_at < boundary).all():
        raise AssertionError("Training contains outcomes unavailable at the cutoff.")
    if not (test.order_date >= boundary).all():
        raise AssertionError("Training and holdout overlap in decision time.")
    return train, test, boundary


def evaluate(raw, *, cutoff=None, trees=60, threshold=.5):
    """Train/test with a fixed threshold. No holdout-driven threshold tuning."""
    if not isinstance(trees, int) or trees < 1:
        raise ValueError("trees must be a positive integer.")
    if not np.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError("threshold must be strictly between zero and one.")
    features = build_features(raw)
    train, test, boundary = split_mature_orders(features, cutoff)
    transformer = ColumnTransformer([
        ("categories", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ("numbers", "passthrough", NUMERIC),
    ])
    model = Pipeline([
        ("features", transformer),
        ("forest", RandomForestClassifier(
            n_estimators=trees, random_state=42, n_jobs=1, class_weight="balanced"
        )),
    ])
    y_train = train.late_delivery.astype(int).to_numpy()
    y_test = test.late_delivery.astype(int).to_numpy()
    model.fit(train[FEATURES], y_train)
    probability = model.predict_proba(test[FEATURES])[:, 1]
    prediction = (probability >= threshold).astype(int)
    prior = float(y_train.mean())
    metrics = {
        "accuracy": float(accuracy_score(y_test, prediction)),
        "precision": float(precision_score(y_test, prediction, zero_division=0)),
        "recall": float(recall_score(y_test, prediction, zero_division=0)),
        "f1": float(f1_score(y_test, prediction, zero_division=0)),
        "brier": float(brier_score_loss(y_test, probability)),
        "constant_prior_brier": float(brier_score_loss(y_test, np.full(len(test), prior))),
        "pr_auc": float(average_precision_score(y_test, probability)),
        "roc_auc": float(roc_auc_score(y_test, probability)) if len(set(y_test)) == 2 else None,
        "confusion_matrix_actual_0_1_predicted_0_1": confusion_matrix(
            y_test, prediction, labels=[0, 1]
        ).tolist(),
    }
    report = {
        "status": "SYNTHETIC_EXPERIMENT_NOT_REAL_WORLD_VALIDATION",
        "prediction_target": "late_delivery",
        "decision_time": "start of order_date",
        "history_builder": "procurement_history.build_features",
        "training_rule": "order_date < cutoff AND outcome_available_at < cutoff",
        "holdout_rule": "order_date >= cutoff; retrospectively observed outcome",
        "cutoff_exclusive_for_training": str(boundary.date()),
        "train_orders": int(len(train)),
        "holdout_orders": int(len(test)),
        "excluded_unmatured_pre_cutoff_orders": int(((features.order_date < boundary)
            & ~(features.outcome_available_at.notna()
                & (features.outcome_available_at < boundary))).sum()),
        "train_positive_rate": prior,
        "holdout_positive_rate": float(y_test.mean()),
        "threshold": float(threshold),
        "random_seed": 42,
        "forest_trees": trees,
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "metrics": metrics,
        "limitations": [
            "Synthetic procurement records do not validate real delivery risk.",
            "Threshold fixed before holdout; no calibration or business-cost tuning.",
            "A single chronological split does not prove temporal stability.",
            "Real-world supplier capacity and promised future delivery are not verified.",
        ],
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("dataset/procurement.csv"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--cutoff", type=str, default=None, help="First holdout order date: YYYY-MM-DD")
    parser.add_argument("--trees", type=int, default=60)
    parser.add_argument("--threshold", type=float, default=.5)
    args = parser.parse_args()
    raw = pd.read_csv(args.data, low_memory=False)
    report = evaluate(raw, cutoff=args.cutoff, trees=args.trees, threshold=args.threshold)
    report["data_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    report["evaluator_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    formatted = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(formatted + "\n", encoding="utf-8")
    print(formatted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
