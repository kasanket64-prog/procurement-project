"""Protect threshold selection and the final-test exclusion boundary."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from validation_recall import (load_validation, operating_point, select_false_alert_budget,
                               select_precision_constrained, threshold_tradeoff)


class ValidationRecallTests(unittest.TestCase):
    def test_curve_matches_actual_threshold_decisions(self):
        labels = np.array([0, 1, 0, 1, 1])
        scores = np.array([.1, .2, .2, .7, .9])
        for row in threshold_tradeoff(labels, scores).itertuples():
            point = operating_point(labels, scores, row.threshold)
            self.assertAlmostEqual(row.precision, point['precision'])
            self.assertAlmostEqual(row.recall, point['recall'])
            self.assertAlmostEqual(row.f2, point['f2'])
        point = operating_point(labels, scores, .2)
        self.assertEqual((point['true_positives'], point['false_positives']), (3, 1))

    def test_invalid_probabilities_and_outcomes_are_rejected(self):
        for labels, scores in [([0, 1], [np.nan, .5]), ([0, 1], [np.inf, .5]),
                               ([0, 1], [-.1, .5]), ([0, 1], [.1, 1.1]),
                               ([0, 1], [.1]), ([1, 1], [.1, .2]), ([], [])]:
            with self.subTest(labels=labels, scores=scores), self.assertRaises(ValueError):
                threshold_tradeoff(labels, scores)

    def test_final_test_outcomes_are_not_parsed(self):
        common = dict(supplier_id='s', supplier_country='India', category='Test', item='Item',
                      business_unit='Test', payment_terms='Net 30', unit_price='10',
                      quantity='1', line_total='10', on_contract='true')
        rows = [dict(common, po_id=key, order_date=placed, promised_delivery_date=placed,
                     actual_delivery_date=completed) for key, placed, completed in [
            ('train', '2025-01-01', '2025-01-02'),
            ('validation-late', '2025-01-10', '2025-01-12'),
            ('validation-on-time', '2025-01-11', '2025-01-11'),
            ('immature', '2025-01-15', '2025-01-21'),
            ('test-poison', '2025-01-20', 'THIS MUST NEVER BE PARSED'),
        ]]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'orders.csv'
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            validation = load_validation(path, '2025-01-10', '2025-01-20')
        self.assertEqual(validation.po_id.tolist(), ['validation-late', 'validation-on-time'])
        self.assertEqual(validation.late_delivery.tolist(), [1, 0])

    def test_invalid_date_boundaries_are_rejected(self):
        for start, end in [('2025-01-20', '2025-01-10'), ('2025-01-10', '2025-01-10'),
                           ('NaT', '2025-01-20'), ('2025-01-10T01:00', '2025-01-20')]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                load_validation('not-opened.csv', start, end)

    def test_selection_respects_precision_floor(self):
        labels = np.array([0, 0, 0, 1, 1, 1])
        scores = np.array([.1, .2, .4, .3, .35, .9])
        curve = threshold_tradeoff(labels, scores)
        chosen = select_precision_constrained(curve)
        self.assertGreaterEqual(chosen.precision, .5)
        self.assertEqual(chosen.recall, 1)
        self.assertGreater(chosen.recall, operating_point(labels, scores, .5)['recall'])
        self.assertEqual(chosen.threshold, .3)

    def test_unachievable_precision_floor_is_rejected(self):
        curve = threshold_tradeoff([1, 0, 0], [.1, .8, .9])
        with self.assertRaisesRegex(ValueError, '50% precision'):
            select_precision_constrained(curve)

    def test_false_alert_budget_maximizes_detections(self):
        labels = np.array([0, 1, 0, 1, 1])
        scores = np.array([.1, .2, .2, .7, .9])
        for budget in (0, 1, 2):
            with self.subTest(budget=budget):
                selected = select_false_alert_budget(labels, scores, budget)
                feasible = [operating_point(labels, scores, t) for t in np.unique(scores)]
                feasible = [point for point in feasible if point['false_positives'] <= budget]
                self.assertLessEqual(selected['false_positives'], budget)
                self.assertEqual(selected['true_positives'], max(p['true_positives'] for p in feasible))

    def test_unaffordable_score_tie_produces_no_alerts(self):
        point = select_false_alert_budget([0, 1], [.8, .8], 0)
        self.assertEqual(point['alerts'], 0)
        self.assertEqual(point['false_positives'], 0)
        self.assertGreater(point['threshold'], 1)

    def test_invalid_false_alert_budgets_are_rejected(self):
        for budget in (-1, .5, True):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                select_false_alert_budget([0, 1], [.1, .9], budget)


if __name__ == '__main__':
    unittest.main()
