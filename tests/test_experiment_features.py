"""Information-availability regressions for experimental history signals."""
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from procurement_experiment_features import EXTRA, build_experiment_features
from procurement_history import build_features
from validation_recall import load_development
from tests.test_procurement_history import orders


class ExperimentFeatureTests(unittest.TestCase):
    def test_outcomes_wait_for_disclosure(self):
        f = build_experiment_features(orders()).set_index('po_id')
        for column in ('supplier_completed_30d', 'supplier_completed_90d', 'item_completed_orders'):
            self.assertEqual(f.loc['b', column], 0)
            self.assertEqual(f.loc['c', column], 1)
        self.assertEqual(f.loc['c', 'supplier_late_rate_30d'], 1)
        self.assertEqual(f.loc['c', 'item_avg_delay'], 3)

    def test_same_day_outcomes_are_excluded(self):
        raw = orders()
        raw.loc[1, 'order_date'] = '2025-01-07'
        f = build_experiment_features(raw).set_index('po_id')
        self.assertEqual(f.loc['b', 'supplier_completed_30d'], 0)
        self.assertEqual(f.loc['b', 'item_completed_orders'], 0)

    def test_recent_window_lower_boundary_is_inclusive(self):
        for days, expected in [(30, 1), (31, 0), (90, 1), (91, 0)]:
            with self.subTest(days=days):
                raw = orders()
                day = pd.Timestamp('2025-01-07') + pd.Timedelta(days=days)
                raw.loc[2, 'order_date'] = str(day.date())
                raw.loc[2, 'promised_delivery_date'] = str((day + pd.Timedelta(days=2)).date())
                f = build_experiment_features(raw).set_index('po_id')
                window = 30 if days < 90 else 90
                self.assertEqual(f.loc['c', f'supplier_completed_{window}d'], expected)

    def test_item_histories_do_not_mix_products(self):
        raw = orders()
        raw.loc[0, ['quantity', 'line_total']] = [10, 100]
        raw.loc[1, ['item', 'quantity', 'line_total']] = ['Other item', 100, 1000]
        raw.loc[2, ['quantity', 'line_total']] = [20, 200]
        f = build_experiment_features(raw).set_index('po_id')
        self.assertEqual(f.loc['c', 'supplier_previous_orders'], 2)
        self.assertEqual(f.loc['c', 'item_previous_orders'], 1)
        self.assertEqual(f.loc['c', 'quantity_vs_item_history'], 2)
        self.assertEqual(f.loc['c', 'lead_vs_item_history'], 2)

    def test_same_day_prices_and_quantities_are_excluded(self):
        raw = orders()
        raw.loc[1, 'order_date'] = '2025-01-08'
        raw.loc[1, ['unit_price', 'quantity', 'line_total']] = [100, 100, 10000]
        f = build_experiment_features(raw).set_index('po_id')
        self.assertEqual(f.loc['c', 'item_previous_orders'], 1)
        self.assertEqual(f.loc['c', 'quantity_vs_item_history'], 1)
        self.assertEqual(f.loc['c', 'price_vs_item_history'], 1)

    def test_undisclosed_outcome_and_future_rows_cannot_change_past(self):
        raw = orders()
        before = build_experiment_features(raw).set_index('po_id')
        raw.loc[0, 'actual_delivery_date'] = '2025-01-02'
        raw.loc[2, ['quantity', 'line_total']] = [100, 1000]
        after = build_experiment_features(raw).set_index('po_id')
        pd.testing.assert_series_equal(before.loc['b', EXTRA], after.loc['b', EXTRA])
        self.assertNotEqual(before.loc['c', 'item_late_rate'], after.loc['c', 'item_late_rate'])

    def test_no_history_defaults_and_base_columns_are_preserved(self):
        raw = orders()
        original = raw.copy(deep=True)
        f = build_experiment_features(raw)
        base = build_features(raw)
        pd.testing.assert_frame_equal(f[base.columns], base)
        pd.testing.assert_frame_equal(raw, original)
        for field in ('quantity_vs_item_history', 'price_vs_item_history', 'lead_vs_item_history'):
            self.assertEqual(f.loc[0, field], 1)
        self.assertEqual(f.loc[0, 'supplier_open_share'], 0)

    def test_loader_preserves_immature_orders_as_history_and_excludes_test(self):
        raw = orders()
        raw.loc[1, 'actual_delivery_date'] = '2025-01-12'
        raw.loc[1, 'outcome_available_at'] = '2025-01-12'
        raw.loc[2, 'actual_delivery_date'] = '2025-01-08'
        raw.loc[2, 'outcome_available_at'] = '2025-01-08'
        poisoned = raw.iloc[2].copy()
        poisoned['po_id'], poisoned['order_date'], poisoned['actual_delivery_date'] = 'test', '2025-01-10', 'DO NOT PARSE'
        raw = pd.concat([raw, poisoned.to_frame().T], ignore_index=True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'orders.csv'
            raw.to_csv(path, index=False)
            train, validation = load_development(path, '2025-01-08', '2025-01-10', feature_builder=build_experiment_features)
        self.assertEqual(train.po_id.tolist(), ['a'])
        self.assertEqual(validation.po_id.tolist(), ['c'])
        self.assertEqual(validation.iloc[0].supplier_previous_orders, 2)
        self.assertEqual(validation.iloc[0].supplier_open_orders, 1)
        self.assertEqual(validation.iloc[0].item_previous_orders, 2)


if __name__ == '__main__':
    unittest.main()
