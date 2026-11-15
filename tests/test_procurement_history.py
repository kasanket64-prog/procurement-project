"""Regression tests for point-in-time supplier history (no model training)."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from procurement_history import build_features


def order(po_id, placed, promised, completed=None, available=None):
    row = {
        "po_id": po_id,
        "supplier_id": "supplier-A",
        "supplier_country": "IN",
        "category": "Parts",
        "item": "Bearing",
        "business_unit": "Operations",
        "payment_terms": "Net 30",
        "order_date": placed,
        "promised_delivery_date": promised,
        "actual_delivery_date": completed,
        "unit_price": 10,
        "quantity": 2,
        "line_total": 20,
        "on_contract": True,
    }
    if available is not None:
        row["outcome_available_at"] = available
    return row


class PointInTimeHistoryTests(unittest.TestCase):
    def test_future_completion_is_not_known_at_later_order_placement(self):
        rows = [
            order("first", "2025-01-01", "2025-01-05", "2025-01-20"),
            order("second", "2025-01-10", "2025-01-15"),
        ]
        result = build_features(pd.DataFrame(rows)).set_index("po_id")
        second = result.loc["second"]
        self.assertEqual(second["supplier_previous_orders"], 1)
        self.assertEqual(second["supplier_completed_orders"], 0)
        self.assertEqual(second["supplier_open_orders"], 1)
        self.assertEqual(second["supplier_overdue_orders"], 1)
        self.assertEqual(second["supplier_completed_late"], 0)
        self.assertEqual(second["supplier_late_rate"], 0)
        self.assertEqual(second["supplier_avg_delay"], 0)

    def test_outcome_is_hidden_until_explicit_availability_date(self):
        rows = [
            order("first", "2025-01-01", "2025-01-05",
                  "2025-01-06", "2025-01-12"),
            order("before", "2025-01-10", "2025-01-20", None, None),
            order("after", "2025-01-13", "2025-01-20", None, None),
        ]
        # Explicit availability is needed on every row for this fixture.
        rows[1]["outcome_available_at"] = None
        rows[2]["outcome_available_at"] = None
        result = build_features(pd.DataFrame(rows)).set_index("po_id")
        self.assertEqual(result.loc["before", "supplier_completed_orders"], 0)
        self.assertEqual(result.loc["after", "supplier_completed_orders"], 1)
        self.assertEqual(result.loc["after", "supplier_completed_late"], 1)

    def test_same_day_orders_cannot_see_one_anothers_outcomes(self):
        rows = [
            order("a", "2025-01-01", "2025-01-02", "2025-01-03"),
            order("b", "2025-01-01", "2025-01-02", "2025-01-04"),
            order("c", "2025-01-05", "2025-01-10"),
        ]
        result = build_features(pd.DataFrame(rows)).set_index("po_id")
        for po_id in ("a", "b"):
            self.assertEqual(result.loc[po_id, "supplier_previous_orders"], 0)
            self.assertEqual(result.loc[po_id, "supplier_completed_orders"], 0)
        self.assertEqual(result.loc["c", "supplier_previous_orders"], 2)
        self.assertEqual(result.loc["c", "supplier_completed_orders"], 2)

    def test_open_order_does_not_become_on_time_label(self):
        result = build_features(pd.DataFrame([
            order("open", "2025-01-01", "2025-01-05"),
            order("next", "2025-01-10", "2025-01-15"),
        ])).set_index("po_id")
        self.assertTrue(pd.isna(result.loc["open", "late_delivery"]))
        self.assertEqual(result.loc["next", "supplier_completed_orders"], 0)
        self.assertEqual(result.loc["next", "supplier_open_orders"], 1)

    def test_same_day_outcome_availability_is_not_usable_at_day_start(self):
        rows = [
            order("first", "2025-01-01", "2025-01-02",
                  "2025-01-04", "2025-01-10"),
            order("second", "2025-01-10", "2025-01-20", None, None),
            order("third", "2025-01-11", "2025-01-20", None, None),
        ]
        rows[1]["outcome_available_at"] = None
        rows[2]["outcome_available_at"] = None
        result = build_features(pd.DataFrame(rows)).set_index("po_id")
        self.assertEqual(result.loc["second", "supplier_completed_orders"], 0)
        self.assertEqual(result.loc["third", "supplier_completed_orders"], 1)


if __name__ == "__main__":
    unittest.main()
