"""Integration coverage for fixed-day history risk in the real terminal workflow.

No mocks: exercises supplier matching, What-If, and the point-in-time
supplier-history snapshot together using a small synthetic fixture.
"""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from procurement_ai import recommend_suppliers, simulate
from procurement_risk import SupplierHistoryRisk


def historical_order(po_id, supplier_id, placed, promise, actual):
    return dict(
        po_id=po_id, supplier_id=supplier_id, supplier_country="India",
        category="Parts", item="Bearing", business_unit="Operations",
        payment_terms="Net 30", order_date=placed,
        promised_delivery_date=promise, actual_delivery_date=actual,
        unit_price=10, quantity=2, line_total=20, on_contract=True,
    )


class IntegratedHistoryRiskTests(unittest.TestCase):
    def setUp(self):
        self.day = pd.Timestamp("2025-05-01")
        self.history = pd.DataFrame([
            historical_order("a1", "A", "2025-01-01", "2025-01-05", "2025-01-09"),
            historical_order("a2", "A", "2025-01-07", "2025-01-15", None),
            historical_order("b1", "B", "2025-02-01", "2025-02-05", "2025-02-04"),
        ])
        self.risk = SupplierHistoryRisk(self.history, self.day, prior=.2)
        self.items = pd.DataFrame([
            dict(supplier_id=sid, supplier_name="Supplier " + sid, supplier_country="India",
                 category="Parts", item="Bearing", avg_unit_price=price, on_time_rate=80,
                 rejection_rate=2, historical_orders=orders, late_delivery_rate=20,
                 max_historical_quantity=50)
            for sid, price, orders in [("A", 12, 40), ("B", 16, 20)]
        ])
        self.request = dict(
            product="Bearing", country="India", quantity=10, delivery_days=14,
            max_price=100, total_budget=1000, business_unit="Operations",
            payment_terms="Net 30", on_contract=1,
            delivery_weight=.25, quality_weight=.25,
            experience_weight=.25, price_weight=.25,
        )

    def test_historical_risk_remains_fixed_across_independent_scenarios(self):
        before = self.items.copy(deep=True)
        original = recommend_suppliers(self.items, self.history, self.risk, self.request, self.day)
        for field, value in [("quantity", 20), ("delivery_days", 4),
                             ("total_budget", 500), ("priorities", "Price")]:
            scenario, changed = simulate(
                self.request, field, value, self.items, self.history, self.risk, self.day
            )
            self.assertIsNot(scenario, self.request)
            a = original.set_index("supplier_id")["ai_late_risk"].sort_index()
            b = changed.set_index("supplier_id")["ai_late_risk"].sort_index()
            pd.testing.assert_series_equal(a, b)
            self.assertTrue((changed.risk_as_of == "2025-05-01").all())
        self.assertEqual(self.request["quantity"], 10)
        self.assertEqual(self.request["total_budget"], 1000)
        pd.testing.assert_frame_equal(self.items, before)

    def test_open_orders_are_excluded_from_known_completed_risk(self):
        original = recommend_suppliers(self.items, self.history, self.risk, self.request, self.day)
        by_id = original.set_index("supplier_id")
        self.assertEqual(by_id.loc["A", "risk_completed_orders"], 1)
        self.assertEqual(by_id.loc["A", "risk_late_orders"], 1)
        self.assertEqual(by_id.loc["A", "risk_open_orders"], 1)
        self.assertEqual(by_id.loc["B", "risk_completed_orders"], 1)
        self.assertEqual(by_id.loc["B", "risk_late_orders"], 0)
        self.assertGreater(by_id.loc["A", "ai_late_risk"], by_id.loc["B", "ai_late_risk"])

    def test_date_mismatched_snapshot_fails_closed(self):
        with self.assertRaises(ValueError):
            self.risk.supplier_risk("A", pd.Timestamp("2025-05-02"))


if __name__ == "__main__":
    unittest.main()
