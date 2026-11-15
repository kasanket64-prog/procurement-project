"""Keep synthetic demo ranking references stable across budget changes."""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from supplier_matcher import rank_demo


class DemoRankingTests(unittest.TestCase):
    def test_budget_filter_does_not_rebase_experience_of_remaining_supplier(self):
        records = []
        for sid, price, orders in (("A", 100, 100), ("B", 10, 10), ("C", 20, 15)):
            records.append({
                "supplier_id": sid,
                "supplier_name": "Fixture " + sid,
                "supplier_country": "India",
                "item": "Bearing",
                "avg_unit_price": price,
                "historical_orders": orders,
                "on_time_rate": 80,
                "rejection_rate": 2,
                "max_historical_quantity": 100,
            })
        frame = pd.DataFrame(records)
        selected = rank_demo(frame, "Bearing", budget=25).set_index("supplier_id")
        self.assertEqual(set(selected.index), {"B", "C"})
        # 40% on-time, 30% quality, 20% experience against all three
        # product/country suppliers, and 10% price against buyer budget.
        expected = 80 * .4 + 98 * .3 + (10 / 100 * 100) * .2 + ((25 - 10) / 25 * 100) * .1
        self.assertAlmostEqual(selected.loc["B", "match_score"], expected)


if __name__ == "__main__":
    unittest.main()
