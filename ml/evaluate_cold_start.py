"""Synthetic held-out supplier stress test, NOT real-world cold-start validation.

Entire supplier IDs are excluded from training. At holdout inference, their
historical supplier signals are deliberately masked to model a no-history
scenario. The data are synthetic; the experiment cannot validate new real
suppliers, actual delivery constraints, or purchase decisions.
"""
import argparse
import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (accuracy_score, brier_score_loss, confusion_matrix,
                             precision_score, recall_score, roc_auc_score,
                             average_precision_score)

from procurement_history import FEATURES, build_features
from evaluate_delivery_risk import split_mature_orders
from backtest_delivery_risk import make_model

ZERO_HISTORY = (
    "supplier_previous_orders", "supplier_completed_orders",
    "supplier_open_orders", "supplier_overdue_orders",
    "supplier_late_rate", "supplier_avg_delay",
)


def select_unseen_suppliers(features, fraction=0.2, seed=42):
    """Deterministic identity-disjoint split, independent of any labels."""
    if not 0 < fraction < 1:
        raise ValueError("fraction must be between zero and one.")
    suppliers = [str(x) for x in features.supplier_id.unique()]
    if len(suppliers) < 3:
        raise ValueError("Require at least three distinct suppliers.")
    ranked = sorted(suppliers, key=lambda sid: (
        hashlib.sha256(f"{seed}|{sid}".encode("utf-8")).hexdigest(), sid))
    count = max(1, min(len(ranked) - 2, math.ceil(len(ranked) * fraction)))
    return frozenset(ranked[:count])


def make_cold_start_split(features, *, cutoff=None, supplier_fraction=.2, seed=42):
    """Exclude whole supplier IDs from fitting and mask all held-out history."""
    train_all, test_all, boundary = split_mature_orders(features, cutoff)
    unseen = select_unseen_suppliers(features, supplier_fraction, seed)
    train = train_all.loc[~train_all.supplier_id.astype(str).isin(unseen)].copy()
    seen = test_all.loc[~test_all.supplier_id.astype(str).isin(unseen)].copy()
    cold = test_all.loc[test_all.supplier_id.astype(str).isin(unseen)].copy()
    if train.empty or seen.empty or cold.empty:
        raise ValueError("Supplier split has no train, seen or unseen holdout rows.")
    if train.late_delivery.nunique() < 2:
        raise ValueError("Training requires both delivery outcomes.")
    for col in ZERO_HISTORY:
        cold[col] = 0.0
    if any(col not in FEATURES for col in ZERO_HISTORY):
        raise AssertionError("Missing no-history model features.")
    if set(train.supplier_id.astype(str)) & unseen:
        raise AssertionError("Held-out supplier entered model fitting.")
    if set(cold.supplier_id.astype(str)) - unseen:
        raise AssertionError("Unexpected supplier in cold-start holdout.")
    if not (train.outcome_available_at < boundary).all():
        raise AssertionError("Immature training label.")
    if not (cold[ZERO_HISTORY] == 0).all().all():
        raise AssertionError("Cold-start history was not masked.")
    return train, seen, cold, boundary, unseen


def measure_holdout(frame, probabilities, threshold):
    y = frame.late_delivery.astype(int).to_numpy()
    p = np.asarray(probabilities, dtype=float)
    pred = (p >= threshold).astype(int)
    matrix = confusion_matrix(y, pred, labels=[0, 1]).tolist()
    return {
        "orders": int(len(y)),
        "suppliers": int(frame.supplier_id.nunique()),
        "positive_rate": float(y.mean()),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "false_negatives": int(matrix[1][0]),
        "false_positives": int(matrix[0][1]),
        "confusion_matrix": matrix,
        "brier": float(brier_score_loss(y, p)),
        "average_precision": float(average_precision_score(y, p)) if y.sum() else None,
        "roc_auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
    }


def evaluate_cold_start(raw, *, cutoff=None, trees=25, threshold=.5,
                        supplier_fraction=.2, seed=42):
    if not isinstance(trees, int) or trees <= 0:
        raise ValueError("trees must be a positive integer.")
    if not np.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError("threshold must be strictly between zero and one.")
    features = build_features(raw)
    train, seen, cold, boundary, unseen = make_cold_start_split(
        features, cutoff=cutoff, supplier_fraction=supplier_fraction, seed=seed)
    model = make_model(trees)
    model.fit(train[FEATURES], train.late_delivery.astype(int))
    p_seen = model.predict_proba(seen[FEATURES])[:, 1]
    p_cold = model.predict_proba(cold[FEATURES])[:, 1]
    return {
        "status": "SYNTHETIC_HELD_OUT_SUPPLIER_STRESS_TEST_NOT_REAL_VALIDATION",
        "definition": ("Entire supplier identities unseen during training; held-out "
                       "supplier-history inputs manually zeroed at test inference."),
        "cutoff_exclusive_for_training": str(boundary.date()),
        "training_mature_orders": int(len(train)),
        "training_supplier_count": int(train.supplier_id.nunique()),
        "held_out_supplier_count": len(unseen),
        "held_out_supplier_ids_sha256": hashlib.sha256(
            "\n".join(sorted(unseen)).encode("utf-8")).hexdigest(),
        "threshold": float(threshold),
        "supplier_fraction": supplier_fraction,
        "random_seed": seed,
        "forest_trees": trees,
        "unseen_holdout": measure_holdout(cold, p_cold, threshold),
        "seen_holdout": measure_holdout(seen, p_seen, threshold),
        "holdout_group_counts": {
            "unseen": {str(k): int(v) for k, v in
                       cold.category.value_counts().sort_index().items()},
            "seen": {str(k): int(v) for k, v in
                     seen.category.value_counts().sort_index().items()},
        },
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "limitations": [
            "Synthetic data, not real first-time suppliers or unseen company performance.",
            "Zeroing history artificially may not match actual information access.",
            "Supplier holdout groups need not have equivalent category or risk prevalence.",
            "A fixed 0.5 alert threshold is illustrative and was not approved by a buyer.",
            "No model from this experiment is connected to real quotation review.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("dataset/procurement.csv"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--trees", type=int, default=25)
    parser.add_argument("--cutoff", type=str)
    parser.add_argument("--supplier-fraction", type=float, default=.2)
    args = parser.parse_args()
    raw = pd.read_csv(args.data, low_memory=False)
    report = evaluate_cold_start(raw, cutoff=args.cutoff, trees=args.trees,
                                 supplier_fraction=args.supplier_fraction)
    report["data_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    report["evaluator_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out, encoding="utf-8")
    print(out, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
