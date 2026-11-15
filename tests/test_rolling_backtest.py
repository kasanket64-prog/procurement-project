"""Rolling temporal-fold, calibration and validation isolation regressions."""
import copy
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from procurement_history import build_features
from backtest_delivery_risk import (
    CANDIDATE_THRESHOLDS, choose_threshold, evaluate_rolling,
    fold_boundaries, reliability, stage_rows,
)


def fixture():
    rows = []
    for i in range(100):
        placed = pd.Timestamp("2025-01-01") + pd.Timedelta(days=i)
        promise = placed + pd.Timedelta(days=2)
        completed = promise + pd.Timedelta(days=2 if i % 4 == 0 else -1)
        rows.append({
            "po_id": f"order-{i:03d}",
            "supplier_id": "A" if i % 2 else "B",
            "supplier_country": "India",
            "category": "Parts",
            "item": "Bearing",
            "business_unit": "Operations",
            "payment_terms": "Net 30",
            "order_date": str(placed.date()),
            "promised_delivery_date": str(promise.date()),
            "actual_delivery_date": str(completed.date()),
            "unit_price": 10,
            "quantity": 2,
            "line_total": 20,
            "on_contract": True,
        })
    return pd.DataFrame(rows)


class RollingBacktestTests(unittest.TestCase):
    def test_fold_stages_are_disjoint_and_observation_dates_mature(self):
        features = build_features(fixture())
        boundaries = list(fold_boundaries(features))
        self.assertEqual(len(boundaries), 3)
        test_sets = []
        for boundary in boundaries:
            _, cal_start, val_start, test_start, test_end = boundary
            train, calibration, validation, test = stage_rows(features, boundary)
            for a, b in ((train, calibration), (train, validation),
                         (train, test), (calibration, validation),
                         (calibration, test), (validation, test)):
                self.assertFalse(set(a.po_id) & set(b.po_id))
            self.assertTrue((train.outcome_available_at < cal_start).all())
            self.assertTrue((calibration.outcome_available_at < val_start).all())
            self.assertTrue((validation.outcome_available_at < test_start).all())
            self.assertTrue((test.order_date >= test_start).all())
            if test_end is not None:
                self.assertTrue((test.order_date < test_end).all())
            test_sets.append(set(test.po_id))
        self.assertFalse(test_sets[0] & test_sets[1])
        self.assertFalse(test_sets[1] & test_sets[2])
        self.assertFalse(test_sets[0] & test_sets[2])

    def test_unmatured_outcome_excluded_from_training_and_calibration(self):
        raw = fixture()
        raw.loc[raw.po_id == "order-003", "actual_delivery_date"] = "2026-01-01"
        raw.loc[raw.po_id == "order-050", "actual_delivery_date"] = "2026-01-01"
        features = build_features(raw)
        fold = list(fold_boundaries(features))[0]
        train, calibration, validation, _ = stage_rows(features, fold)
        self.assertNotIn("order-003", set(train.po_id))
        self.assertNotIn("order-050", set(calibration.po_id))
        self.assertNotIn("order-050", set(validation.po_id))

    def test_threshold_choice_is_cost_sensitive_and_deterministic(self):
        labels = np.array([0, 0, 0, 1, 1])
        probability = np.array([.15, .25, .55, .35, .75])
        high_miss_cost = choose_threshold(labels, probability,
                                          false_negative_cost=10, false_positive_cost=1)
        high_alarm_cost = choose_threshold(labels, probability,
                                           false_negative_cost=1, false_positive_cost=10)
        self.assertIn(high_miss_cost["threshold"], CANDIDATE_THRESHOLDS)
        self.assertLessEqual(high_miss_cost["threshold"], high_alarm_cost["threshold"])
        self.assertEqual(high_miss_cost, choose_threshold(
            labels, probability, false_negative_cost=10, false_positive_cost=1))
        with self.assertRaises(ValueError):
            choose_threshold(labels, probability, false_negative_cost=0)

    def test_rolling_evaluation_reproducible_and_calibration_bounded(self):
        source = fixture()
        untouched = copy.deepcopy(source)
        first = evaluate_rolling(source, trees=5)
        second = evaluate_rolling(source, trees=5)
        self.assertEqual(first, second)
        self.assertEqual(len(first["folds"]), 3)
        self.assertEqual(first["status"], "SYNTHETIC_EXPERIMENT_NOT_REAL_WORLD_VALIDATION")
        for fold in first["folds"]:
            report = fold["test_metrics"]
            self.assertEqual(sum(sum(r) for r in report[
                "confusion_matrix_actual_0_1_predicted_0_1"]), report["orders"])
            self.assertGreaterEqual(report["calibrated_brier"], 0)
            self.assertLessEqual(report["calibrated_brier"], 1)
            self.assertGreaterEqual(report["raw_brier"], 0)
            self.assertLessEqual(report["raw_brier"], 1)
            for key in ("raw_reliability", "calibrated_reliability"):
                self.assertEqual(sum(b["count"] for b in report[key]["bins"]), report["orders"])
                self.assertTrue(0 <= report[key]["expected_calibration_error"] <= 1)
        pd.testing.assert_frame_equal(source, untouched)

    def test_changing_future_test_labels_does_not_choose_a_different_threshold(self):
        original = fixture()
        altered = fixture()
        # All altered orders fall in the last fold's *test* window, strictly
        # after its calibration and threshold-selection windows.
        for idx in range(86, 100):
            placed = pd.Timestamp(altered.loc[idx, "order_date"])
            promise = pd.Timestamp(altered.loc[idx, "promised_delivery_date"])
            new_completion = promise + pd.Timedelta(days=3 if idx % 4 else -1)
            altered.loc[idx, "actual_delivery_date"] = str(new_completion.date())
        a = evaluate_rolling(original, trees=3)
        b = evaluate_rolling(altered, trees=3)
        self.assertEqual(
            [fold["threshold_selection"] for fold in a["folds"]],
            [fold["threshold_selection"] for fold in b["folds"]],
        )
        self.assertNotEqual(
            a["folds"][-1]["test_metrics"]["positive_rate"],
            b["folds"][-1]["test_metrics"]["positive_rate"],
        )

    def test_reliability_rejects_nonprobabilities(self):
        with self.assertRaises(ValueError):
            reliability([0, 1], [-.1, .5])
        with self.assertRaises(ValueError):
            reliability([0, 1], [.2, 1.1])
        r = reliability([0, 1], [0, 1])
        self.assertEqual(sum(b["count"] for b in r["bins"]), 2)
        self.assertEqual(r["expected_calibration_error"], 0)


if __name__ == "__main__":
    unittest.main()
