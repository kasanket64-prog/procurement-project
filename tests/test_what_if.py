"""Regression tests for terminal What-If scenario isolation and comparisons."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from procurement_ai import compare_results, simulate, unit_budget, WEIGHT_NAMES, PRIORITY_PRESETS


class WhatIfTests(unittest.TestCase):
    def setUp(self):
        self.original = {
            "product": "Bearing", "quantity": 10, "delivery_days": 14,
            "max_price": 100, "total_budget": 500,
            "delivery_weight": .25, "quality_weight": .25,
            "experience_weight": .25, "price_weight": .25,
        }

    def test_quantity_scenario_preserves_original_and_total_budget(self):
        with patch("procurement_ai.recommend_suppliers", return_value="results") as recommend:
            scenario, result = simulate(self.original, "quantity", 20, None, None, None, None)
        self.assertEqual(result, "results")
        self.assertEqual(self.original["quantity"], 10)
        self.assertEqual(scenario["quantity"], 20)
        self.assertEqual(scenario["total_budget"], 500)
        self.assertEqual(unit_budget(scenario), 25)
        self.assertEqual(unit_budget(self.original), 50)
        self.assertIs(recommend.call_args.args[3], scenario)

    def test_each_scenario_starts_from_original_not_previous_scenario(self):
        with patch("procurement_ai.recommend_suppliers", return_value=None):
            first, _ = simulate(self.original, "quantity", 20, None, None, None, None)
            second, _ = simulate(self.original, "delivery_days", 7, None, None, None, None)
        self.assertEqual(first["quantity"], 20)
        self.assertEqual(second["quantity"], 10)
        self.assertEqual(second["delivery_days"], 7)
        self.assertEqual(self.original["delivery_days"], 14)

    def test_priority_preset_changes_only_weights(self):
        with patch("procurement_ai.recommend_suppliers", return_value=None):
            scenario, _ = simulate(self.original, "priorities", "Price", None, None, None, None)
        self.assertEqual(tuple(scenario[k] for k in WEIGHT_NAMES), PRIORITY_PRESETS["Price"])
        self.assertEqual(tuple(self.original[k] for k in WEIGHT_NAMES), (.25,) * 4)
        self.assertEqual(scenario["total_budget"], self.original["total_budget"])

    def test_unknown_simulation_variable_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate(self.original, "supplier_id", "tampered", None, None, None, None)

    def test_comparison_uses_supplier_id_not_display_name(self):
        before = pd.DataFrame([
            dict(supplier_id="A", item="Bearing", supplier_name="Same Name", rank=1, match_score=90, ai_late_risk=10),
            dict(supplier_id="B", item="Bearing", supplier_name="Same Name", rank=2, match_score=80, ai_late_risk=20),
        ])
        after = pd.DataFrame([
            dict(supplier_id="B", item="Bearing", supplier_name="Same Name", rank=1, match_score=91, ai_late_risk=20),
            dict(supplier_id="A", item="Bearing", supplier_name="Same Name", rank=2, match_score=75, ai_late_risk=10),
        ])
        result = compare_results(before, after).set_index("Supplier ID")
        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc["B", "Rank change"], "Up 1")
        self.assertEqual(result.loc["A", "Rank change"], "Down 1")
        self.assertEqual(result.loc["A", "Original risk %"], result.loc["A", "What-if risk %"])

    def test_comparison_reports_removed_and_newly_eligible_suppliers(self):
        def row(sid):
            return dict(supplier_id=sid, item="Bearing", supplier_name=sid, rank=1, match_score=80, ai_late_risk=10)
        result = compare_results(pd.DataFrame([row("A")]), pd.DataFrame([row("B")])).set_index("Supplier ID")
        self.assertTrue(result.loc["A", "Rank change"].startswith("REMOVED"))
        self.assertEqual(result.loc["B", "Rank change"], "NEWLY ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
