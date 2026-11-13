"""Regression checks for information available at the start of a decision day."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from procurement_history import HISTORY, build_features
from procurement_risk import SupplierHistoryRisk


def orders():
    common = dict(supplier_id='supplier-1', supplier_country='India', category='Test',
                  item='Test item', business_unit='Test unit', payment_terms='Net 30',
                  unit_price=10, quantity=1, line_total=10, on_contract=True)
    return pd.DataFrame([
        dict(common, po_id='a', order_date='2025-01-01',
             promised_delivery_date='2025-01-02', actual_delivery_date='2025-01-05',
             outcome_available_at='2025-01-07'),
        dict(common, po_id='b', order_date='2025-01-05',
             promised_delivery_date='2025-01-10', actual_delivery_date=None,
             outcome_available_at=None),
        dict(common, po_id='c', order_date='2025-01-08',
             promised_delivery_date='2025-01-10', actual_delivery_date=None,
             outcome_available_at=None),
    ])


class HistoryRegressionTests(unittest.TestCase):
    def test_outcomes_wait_for_availability(self):
        features = build_features(orders()).set_index('po_id')
        before = features.loc['b']
        self.assertEqual(before.supplier_previous_orders, 1)
        self.assertEqual(before.supplier_completed_orders, 0)
        self.assertEqual(before.supplier_open_orders, 1)
        self.assertEqual(before.supplier_late_rate, 0)
        after = features.loc['c']
        self.assertEqual(after.supplier_completed_orders, 1)
        self.assertEqual(after.supplier_completed_late, 1)
        self.assertEqual(after.supplier_late_rate, 1)
        self.assertEqual(after.supplier_avg_delay, 3)

    def test_same_day_outcomes_and_orders_are_excluded(self):
        raw = orders()
        raw.loc[1:, 'order_date'] = '2025-01-07'
        features = build_features(raw).set_index('po_id')
        for order_id in ('b', 'c'):
            with self.subTest(order_id=order_id):
                self.assertEqual(features.loc[order_id, 'supplier_completed_orders'], 0)
                self.assertEqual(features.loc[order_id, 'supplier_previous_orders'], 1)

    def test_open_orders_have_no_outcome_label(self):
        features = build_features(orders()).set_index('po_id')
        self.assertTrue(features.loc[['b', 'c'], 'late_delivery'].isna().all())
        self.assertTrue(features.loc[['b', 'c'], 'delivery_delay_days'].isna().all())

    def test_future_outcomes_cannot_change_past_history(self):
        raw = orders()
        before = build_features(raw).set_index('po_id')
        # Change late to on time, but keep its disclosure after order b's decision.
        raw.loc[0, 'actual_delivery_date'] = '2025-01-02'
        after = build_features(raw).set_index('po_id')
        pd.testing.assert_series_equal(before.loc['b', HISTORY], after.loc['b', HISTORY])
        self.assertEqual(before.loc['c', 'supplier_completed_late'], 1)
        self.assertEqual(after.loc['c', 'supplier_completed_late'], 0)

    def test_duplicate_order_ids_are_rejected(self):
        raw = orders()
        raw.loc[1, 'po_id'] = 'a'
        with self.assertRaisesRegex(ValueError, 'Order IDs must be present and unique'):
            build_features(raw)

    def test_risk_snapshot_rejects_a_different_decision_day(self):
        model = SupplierHistoryRisk(orders(), '2025-04-02', prior=.2)
        self.assertEqual(model.evidence('supplier-1', '2025-04-02')['risk_completed_orders'], 1)
        with self.assertRaisesRegex(ValueError, 'Risk snapshot date differs'):
            model.evidence('supplier-1', '2025-04-03')


if __name__ == '__main__':
    unittest.main()
