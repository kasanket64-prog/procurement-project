"""Synthetic fixture tests for the local, human-reviewed quotation engine.

No genuine buyer/supplier records are used. Nothing authorizes purchases.
"""
import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from real_procurement import DataError, evaluate

AS_OF = datetime.fromisoformat("2025-05-04T12:00:00+05:30")


def synthetic_bundle():
    def quote(quote_id, supplier_id, total):
        return {
            "id": quote_id, "source_id": "fixture", "source_record_id": "doc-" + quote_id,
            "product_id": "bearing", "supplier_id": supplier_id, "currency": "INR",
            "unit": "each", "quantity": "10", "total_amount": total,
            "destination_id": "nagpur", "issued_at": "2025-05-02T10:00:00+05:30",
            "received_at": "2025-05-02T11:00:00+05:30",
            "valid_until": "2025-05-20T23:59:00+05:30",
            "reviewed_at": "2025-05-03T10:00:00+05:30", "reviewed_by": "Fixture Reviewer",
            "promised_delivery_date": "2025-05-12", "specification_confirmed": True,
            "all_costs_included": True, "terms_reference": "fixture terms",
        }

    return {
        "schema_version": "1.0",
        "sources": [{
            "id": "fixture", "data_kind": "synthetic", "permission_confirmed": False,
            "reference": "TEST ONLY", "reviewed_by": "Fixture Reviewer",
            "reviewed_at": "2025-05-02T09:00:00+05:30",
        }],
        "products": [{
            "id": "bearing", "source_id": "fixture", "source_record_id": "product-1",
            "name": "Bearing", "specification": "Exact bearing specification", "unit": "each",
        }],
        "suppliers": [
            {"id": "A", "source_id": "fixture", "source_record_id": "supplier-A",
             "name": "Fictional A", "country": "India"},
            {"id": "B", "source_id": "fixture", "source_record_id": "supplier-B",
             "name": "Fictional B", "country": "India"},
        ],
        "request": {
            "product_id": "bearing", "currency": "INR",
            "decision_timezone": "Asia/Kolkata", "unit": "each",
            "quantity": "10", "total_budget": "2000.00",
            "needed_by": "2025-05-20", "destination_id": "nagpur",
            "supplier_country": None,
        },
        "quotes": [quote("Q1", "A", "1600.00"), quote("Q2", "B", "1500.00")],
    }


class QuotationReviewTests(unittest.TestCase):
    def test_eligible_quotations_rank_exact_decimals_without_purchasing(self):
        original = synthetic_bundle()
        untouched = copy.deepcopy(original)
        result = evaluate(original, AS_OF, demo=True)
        self.assertEqual(result["status"], "SYNTHETIC_DEMONSTRATION")
        self.assertFalse(result["purchase_authorized"])
        self.assertEqual(result["eligible_quotes"], 2)
        by_id = {row["quote_id"]: row for row in result["quotes"]}
        self.assertEqual(by_id["Q2"]["cost_rank"], 1)
        self.assertEqual(by_id["Q1"]["cost_rank"], 2)
        self.assertTrue(all(row["risk_estimate"] is None for row in result["quotes"]))
        self.assertEqual(original, untouched)

    def test_quote_after_budget_or_deadline_becomes_ineligible(self):
        bundle = synthetic_bundle()
        bundle["quotes"][0]["total_amount"] = "2000.000001"
        bundle["quotes"][1]["promised_delivery_date"] = "2025-05-21"
        result = evaluate(bundle, AS_OF, demo=True)
        self.assertEqual(result["eligible_quotes"], 0)
        self.assertTrue(any("budget" in x.lower() for x in result["quotes"][0]["reasons"]))
        self.assertTrue(any("deadline" in x.lower() for x in result["quotes"][1]["reasons"]))

    def test_duplicate_source_quotation_is_rejected(self):
        bundle = synthetic_bundle()
        bundle["quotes"][1]["source_record_id"] = bundle["quotes"][0]["source_record_id"]
        with self.assertRaises(DataError):
            evaluate(bundle, AS_OF, demo=True)

    def test_real_mode_requires_explicit_source_authorization(self):
        bundle = synthetic_bundle()
        with self.assertRaises(DataError):
            evaluate(bundle, AS_OF, demo=False)
        bundle["sources"][0]["data_kind"] = "real"
        bundle["sources"][0]["permission_confirmed"] = True
        result = evaluate(bundle, AS_OF, demo=False)
        self.assertEqual(result["status"], "QUOTATION_REVIEW_ONLY")
        self.assertFalse(result["purchase_authorized"])
        self.assertIn("not independently verified", result["provenance_status"])


if __name__ == "__main__":
    unittest.main()
