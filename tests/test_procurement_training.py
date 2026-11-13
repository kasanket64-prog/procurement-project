"""Boundary and label-maturity checks for chronological training evaluation."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from procurement_history import build_features
from procurement_training import chronological_split


def features():
    common = dict(supplier_id='s', supplier_country='India', category='Test', item='Item',
                  business_unit='Test', payment_terms='Net 30', unit_price=10,
                  quantity=1, line_total=10, on_contract=True)
    rows = [
        ('train', '2025-01-01', '2025-01-03'),
        ('train-boundary', '2025-01-02', '2025-01-10'),
        ('open', '2025-01-03', None),
        ('validation-1', '2025-01-10', '2025-01-12'),
        ('validation-2', '2025-01-10', '2025-01-13'),
        ('validation-boundary', '2025-01-19', '2025-01-20'),
        ('test', '2025-01-20', '2025-01-22'),
        ('test-boundary', '2025-01-21', '2025-02-01'),
        ('future', '2025-02-01', '2025-02-02'),
    ]
    return build_features(pd.DataFrame([
        dict(common, po_id=key, order_date=placed, promised_delivery_date=placed,
             actual_delivery_date=available, outcome_available_at=available)
        for key, placed, available in rows
    ]))


class ChronologicalSplitTests(unittest.TestCase):
    def setUp(self):
        self.features = features()

    def split(self, *dates):
        return chronological_split(self.features, *(dates or ('2025-01-10', '2025-01-20', '2025-02-01')))

    def test_calendar_boundaries_keep_same_day_orders_together(self):
        train, validation, test = self.split()
        self.assertEqual(train.po_id.tolist(), ['train'])
        self.assertEqual(validation.po_id.tolist(), ['validation-1', 'validation-2'])
        self.assertEqual(test.po_id.tolist(), ['test'])
        self.assertLess(train.order_date.max(), validation.order_date.min())
        self.assertLess(validation.order_date.max(), test.order_date.min())

    def test_labels_must_be_known_strictly_before_cutoffs(self):
        partitions = self.split()
        included = set().union(*(set(part.po_id) for part in partitions))
        self.assertTrue(included.isdisjoint({'train-boundary', 'validation-boundary', 'test-boundary', 'open', 'future'}))
        for part, cutoff in zip(partitions, ['2025-01-10', '2025-01-20', '2025-02-01']):
            self.assertTrue((part.outcome_available_at < pd.Timestamp(cutoff)).all())
            self.assertTrue(part.late_delivery.notna().all())

    def test_partition_changes_cannot_mutate_source(self):
        original = self.features.copy(deep=True)
        train, _, _ = self.split()
        train.loc[:, 'quantity'] = 100
        pd.testing.assert_frame_equal(self.features, original)

    def test_invalid_or_unordered_cutoffs_are_rejected(self):
        for dates in [
            ('2025-01-20', '2025-01-10', '2025-02-01'),
            ('2025-01-10', '2025-01-10', '2025-02-01'),
            ('2025-01-10', '2025-01-20', '2025-01-20'),
            ('NaT', '2025-01-20', '2025-02-01'),
            ('2025-01-10T12:00', '2025-01-20', '2025-02-01'),
            ('2025-01-10T00:00Z', '2025-01-20', '2025-02-01'),
        ]:
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                self.split(*dates)

    def test_each_partition_requires_mature_labels(self):
        for dates, partition in [
            (('2024-01-01', '2025-01-20', '2025-02-01'), 'training'),
            (('2025-01-09', '2025-01-10', '2025-02-01'), 'validation'),
            (('2025-01-10', '2025-01-20', '2025-01-21'), 'test'),
        ]:
            with self.subTest(partition=partition), self.assertRaisesRegex(ValueError, partition):
                self.split(*dates)


if __name__ == '__main__':
    unittest.main()
