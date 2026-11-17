"""Regression tests for independent procurement What-If scenarios.

Run from the repository root after installing requirements-ml.txt:
    python -m unittest discover -s tests -p "test_what_if_simulation.py"
"""
import sys
import unittest
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from procurement_ai import (  # noqa: E402
    WEIGHT_NAMES,
    compare_results,
    recommend_suppliers,
    simulate,
    unit_budget,
)


class WhatIfSimulationTests(unittest.TestCase):
    def setUp(self):
        self.today = datetime(2026, 11, 17)
        self.request = {
            "product": "Widget",
            "country": None,
            "quantity": 10.0,
            "delivery_days": 7,
            "max_price": None,
            "total_budget": 1000.0,
            "business_unit": "Operations",
            "payment_terms": "Net 30",
            "on_contract": 1,
            "delivery_weight": 0.25,
            "quality_weight": 0.25,
            "experience_weight": 0.25,
            "price_weight": 0.25,
        }
        self.items = pd.DataFrame([
            {
                "supplier_id": "A", "supplier_name": "Alpha", "item": "Widget",
                "supplier_country": "India", "avg_unit_price": 80.0,
                "on_time_rate": 95.0, "rejection_rate": 2.0,
                "historical_orders": 20, "late_delivery_rate": 5.0,
            },
            {
                "supplier_id": "B", "supplier_name": "Beta", "item": "Widget",
                "supplier_country": "India", "avg_unit_price": 120.0,
                "on_time_rate": 85.0, "rejection_rate": 3.0,
                "historical_orders": 30, "late_delivery_rate": 10.0,
            },
        ])
        self.history = pd.DataFrame()
        self.risk_model = object()

    def recommend(self, request):
        # Isolate scenario comparison and ranking from unavailable risk validation.
        with patch("procurement_ai.validate_commercial_inputs"), patch(
            "procurement_ai.predict_delivery_risk", return_value=12.0
        ):
            return recommend_suppliers(
                self.items, self.history, self.risk_model, request, self.today
            )

    def test_total_budget_ceiling_changes_with_quantity(self):
        self.assertEqual(unit_budget(self.request), 100.0)
        changed = deepcopy(self.request)
        changed["quantity"] = 20.0
        self.assertEqual(unit_budget(changed), 50.0)
        self.assertEqual(self.request["quantity"], 10.0)

    def test_simulation_does_not_mutate_original_request(self):
        original = deepcopy(self.request)
        with patch("procurement_ai.recommend_suppliers", return_value="result") as run:
            scenario, result = simulate(
                self.request, "quantity", 20.0, self.items,
                self.history, self.risk_model, self.today
            )
        self.assertEqual(self.request, original)
        self.assertEqual(scenario["quantity"], 20.0)
        self.assertEqual(scenario["total_budget"], 1000.0)
        self.assertEqual(result, "result")
        run.assert_called_once()

    def test_budget_expansion_makes_supplier_eligible(self):
        baseline = self.recommend(self.request)
        self.assertEqual(baseline["supplier_id"].tolist(), ["A"])
        scenario = deepcopy(self.request)
        scenario["total_budget"] = 1500.0
        expanded = self.recommend(scenario)
        self.assertEqual(set(expanded["supplier_id"]), {"A", "B"})
        changes = compare_results(baseline, expanded)
        added = changes.loc[changes["Supplier ID"] == "B"].iloc[0]
        self.assertEqual(added["Rank change"], "NEWLY ELIGIBLE")
        self.assertEqual(added["Original rank"], "N/A")

    def test_quantity_increase_can_remove_supplier_without_changing_risk(self):
        baseline = self.recommend(self.request)
        scenario = deepcopy(self.request)
        scenario["quantity"] = 20.0
        reduced = self.recommend(scenario)
        self.assertTrue(reduced.empty)
        changes = compare_results(baseline, reduced)
        self.assertIn("REMOVED", changes.iloc[0]["Rank change"])
        self.assertEqual(changes.iloc[0]["What-if rank"], "N/A")
        # Risk for the original recommendation is not rewritten by a simulation.
        self.assertEqual(baseline.iloc[0]["ai_late_risk"], 12.0)

    def test_priority_preset_does_not_change_other_inputs(self):
        original = deepcopy(self.request)
        with patch("procurement_ai.recommend_suppliers", return_value=pd.DataFrame()):
            scenario, _ = simulate(
                self.request, "priorities", "Price", self.items,
                self.history, self.risk_model, self.today
            )
        self.assertEqual(tuple(scenario[k] for k in WEIGHT_NAMES), (0.2, 0.2, 0.1, 0.5))
        self.assertEqual(sum(scenario[k] for k in WEIGHT_NAMES), 1.0)
        for key in ("quantity", "delivery_days", "max_price", "total_budget"):
            self.assertEqual(scenario[key], original[key])
        self.assertEqual(self.request, original)

    def test_comparison_uses_supplier_ids_not_duplicate_names(self):
        before = pd.DataFrame([
            {"supplier_id": "A", "item": "Widget", "supplier_name": "Same",
             "rank": 1, "match_score": 90.0, "ai_late_risk": 10.0},
            {"supplier_id": "B", "item": "Widget", "supplier_name": "Same",
             "rank": 2, "match_score": 80.0, "ai_late_risk": 20.0},
        ])
        after = before.iloc[::-1].copy()
        after["rank"] = [1, 2]
        comparison = compare_results(before, after)
        self.assertEqual(len(comparison), 2)
        self.assertEqual(
            comparison.set_index("Supplier ID").loc["B", "Rank change"], "Up 1"
        )
        self.assertEqual(
            comparison.set_index("Supplier ID").loc["A", "Rank change"], "Down 1"
        )


if __name__ == "__main__":
    unittest.main()
