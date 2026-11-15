"""Headless browser smoke tests for the generated offline procurement workspace.

The browser is deliberately created from a temporary HTML build: tests must
not rewrite the tracked ml/procurement_platform.html artifact.
"""
import sys
import tempfile
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from procurement_platform import build


class BrowserWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp = tempfile.TemporaryDirectory(prefix="procurement-browser-")
        cls.path = Path(cls._temp.name) / "procurement_platform.html"
        build(ROOT, cls.path)
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls._browser.close()
        cls._playwright.stop()
        cls._temp.cleanup()

    def setUp(self):
        self.page = self._browser.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.goto(self.path.as_uri(), wait_until="load")

    def tearDown(self):
        self.page.close()

    def search_demo(self):
        self.page.locator("#product").fill("Steel Coil (per ton)")
        self.page.locator("#search-form button[type=submit]").click()
        self.assertTrue(self.page.locator("#results").is_visible())
        self.assertTrue(self.page.locator("#demo").is_visible())
        self.assertGreater(self.page.locator("#demo-cards article").count(), 0)

    def test_baseline_compares_changed_buyer_priorities(self):
        self.search_demo()
        baseline = self.page.locator("#demo-cards article").first.inner_text()
        self.page.locator("#save-baseline").click()
        self.page.locator("#priority").select_option("price")
        self.page.locator("#search-form button[type=submit]").click()
        compare = self.page.locator("#comparison")
        self.assertTrue(compare.locator("table").is_visible())
        self.assertIn("ORIGINAL:", compare.inner_text())
        self.assertIn("WHAT-IF:", compare.inner_text())
        self.assertGreater(compare.locator("tr").count(), 1)
        self.assertIn("SYNTHETIC DEMO", baseline)
        self.assertFalse(self.errors, self.errors)

    def test_budget_filters_and_comparison_records_removals(self):
        self.search_demo()
        self.page.locator("#save-baseline").click()
        self.page.locator("#budget").fill("0.000001")
        self.page.locator("#search-form button[type=submit]").click()
        self.assertIn("0 eligible synthetic companies", self.page.locator("#summary").inner_text())
        self.assertIn("Removed by filters", self.page.locator("#comparison").inner_text())
        self.assertFalse(self.errors, self.errors)

    def test_request_draft_requires_review_and_does_not_purchase(self):
        self.search_demo()
        self.page.locator("#start-rfq").click()
        self.assertTrue(self.page.locator("#request").is_visible())
        self.page.locator("#rfq-product").fill("Steel Coil")
        self.page.locator("#specs").fill("Grade A steel, exact specification to be confirmed")
        self.page.locator("#rfq-quantity").fill("10")
        self.page.locator("#unit").fill("ton")
        self.page.locator("#currency").fill("INR")
        self.page.locator("#destination").fill("Nagpur, Maharashtra, India")
        self.page.locator("#date").fill("2099-12-31")
        self.page.locator("#zone").fill("Asia/Kolkata")
        self.page.locator("#confirm").check()
        self.page.locator("#rfq-form button[type=submit]").click()
        self.assertTrue(self.page.locator("#preview").is_visible())
        self.assertIn("This is a request, not a purchase order", self.page.locator("#draft").inner_text())
        self.assertFalse(self.errors, self.errors)


if __name__ == "__main__":
    unittest.main()
