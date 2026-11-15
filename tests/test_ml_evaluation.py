"""Temporal evaluation gates: no future outcome labels may enter training."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from procurement_history import build_features
from evaluate_delivery_risk import evaluate, split_mature_orders


def fixture():
    rows = []
    for i in range(14):
        start = pd.Timestamp("2025-01-01") + pd.Timedelta(days=2 * i)
        promised = start + pd.Timedelta(days=2)
        delivered = promised + pd.Timedelta(days=1 if i % 2 else -1)
        rows.append({
            "po_id": f"po-{i:02d}",
            "supplier_id": "A" if i % 3 else "B",
            "supplier_country": "India",
            "category": "Parts",
            "item": "Bearing",
            "business_unit": "Operations",
            "payment_terms": "Net 30",
            "order_date": start.date().isoformat(),
            "promised_delivery_date": promised.date().isoformat(),
            "actual_delivery_date": delivered.date().isoformat(),
            "unit_price": 10,
            "quantity": 2,
            "line_total": 20,
            "on_contract": True,
        })
    # This order was placed before cutoff, but completed *after* it.
    rows[0]["actual_delivery_date"] = "2025-02-10"
    # An open order must never be treated as an on-time completion.
    rows[1]["actual_delivery_date"] = None
    return pd.DataFrame(rows)


class TemporalEvaluationTests(unittest.TestCase):
    def test_training_excludes_unavailable_outcomes_and_open_orders(self):
        f = build_features(fixture())
        train, test, cutoff = split_mature_orders(f, "2025-01-17")
        self.assertEqual(str(cutoff.date()), "2025-01-17")
        self.assertNotIn("po-00", set(train.po_id))
        self.assertNotIn("po-01", set(train.po_id))
        self.assertTrue((train.outcome_available_at < cutoff).all())
        self.assertTrue((train.order_date < cutoff).all())
        self.assertTrue((test.order_date >= cutoff).all())
        self.assertFalse(set(train.po_id) & set(test.po_id))

    def test_evaluator_is_deterministic_and_reports_baseline(self):
        a = evaluate(fixture(), cutoff="2025-01-17", trees=8)
        b = evaluate(fixture(), cutoff="2025-01-17", trees=8)
        self.assertEqual(a, b)
        self.assertEqual(a["status"], "SYNTHETIC_EXPERIMENT_NOT_REAL_WORLD_VALIDATION")
        self.assertGreater(a["train_orders"], 0)
        self.assertGreater(a["holdout_orders"], 0)
        self.assertGreaterEqual(a["excluded_unmatured_pre_cutoff_orders"], 2)
        self.assertIn("constant_prior_brier", a["metrics"])
        self.assertEqual(sum(sum(row) for row in a["metrics"]["confusion_matrix_actual_0_1_predicted_0_1"]), a["holdout_orders"])

    def test_bad_threshold_and_insufficient_training_data_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(fixture(), cutoff="2025-01-17", threshold=1)
        with self.assertRaises(ValueError):
            evaluate(fixture(), cutoff="2025-01-03", trees=3)


if __name__ == "__main__":
    unittest.main()
