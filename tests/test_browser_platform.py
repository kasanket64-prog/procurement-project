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
        self.assertIn("Demo data", baseline)
        self.assertFalse(self.errors, self.errors)

    def test_customer_labels_and_public_source_separation(self):
        self.search_demo()
        self.assertNotIn("synthetic", self.page.locator("body").inner_text().lower())
        self.assertIn("generated supplier identities", self.page.locator("#demo").inner_text())
        self.assertIn("Illustrative on-time", self.page.locator("#demo-cards").inner_text())
        self.page.locator("#product").fill("caprolactam")
        self.page.locator("#search-form button[type=submit]").click()
        leads = self.page.locator("#researched-cards")
        self.assertGreater(leads.locator("article").count(), 0)
        self.assertNotIn("Demo data", leads.inner_text())
        leads.locator("summary").first.click()
        source = leads.get_by_role("link", name="Read source").first
        self.assertTrue(source.is_visible())
        self.assertTrue(source.get_attribute("href").startswith("https://"))
        self.assertIn("No quotation received", leads.inner_text())
        self.assertFalse(self.errors, self.errors)

    def test_checked_in_pages_match_their_templates(self):
        self.assertEqual(self.path.read_text(encoding="utf-8"),
                         (ROOT / "ml/procurement_platform.html").read_text(encoding="utf-8"))
        from supplier_discovery import build_page
        import json
        ml = ROOT / "ml"
        discovery = build_page(json.loads((ml / "public_supplier_leads.json").read_text(encoding="utf-8")),
                               (ml / "supplier_discovery_template.html").read_text(encoding="utf-8"))
        self.assertEqual(discovery, (ml / "supplier_discovery.html").read_text(encoding="utf-8"))

    def test_public_records_are_searchable_and_separate_from_demo_scores(self):
        self.assertEqual(self.page.evaluate("data.awards.length"), 296)
        self.assertTrue(self.page.evaluate("new Set(data.awards.map(r => r.source + r.record_id)).size === data.awards.length"))
        self.page.locator("#product").fill("supervision")
        self.page.locator("#search-form button[type=submit]").click()
        cards = self.page.locator("#public-record-cards")
        self.assertGreater(cards.locator("article").count(), 0)
        self.assertLessEqual(cards.locator("article").count(), 20)
        self.assertTrue(cards.get_by_role("link", name="Official procurement record").first.is_visible())
        self.assertNotIn("weighted match score", cards.inner_text())
        self.assertNotIn("Demo data", cards.inner_text())
        self.page.locator("#product").fill("zzzz-no-public-record-match")
        self.page.locator("#search-form button[type=submit]").click()
        self.assertEqual(cards.locator("article").count(), 0)
        self.assertIn("No matching record", cards.inner_text())
        self.assertFalse(self.errors, self.errors)

    def test_dashboard_counts_and_small_screen_layout(self):
        self.assertEqual(self.page.locator("#record-count").inner_text(), "296")
        self.assertEqual(self.page.locator("#source-count").inner_text(), "3")
        self.assertEqual(self.page.locator("#catalog-count").inner_text(), "40")
        for width in (1440, 390, 320):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 900})
                self.search_demo()
                self.assertTrue(self.page.evaluate(
                    "document.documentElement.scrollWidth <= window.innerWidth"
                ))
                self.assertTrue(self.page.locator("#product").is_visible())
                self.assertIn("generated supplier identities", self.page.locator("#demo").inner_text())
        self.assertFalse(self.errors, self.errors)

    def test_budget_filters_and_comparison_records_removals(self):
        self.search_demo()
        self.page.locator("#save-baseline").click()
        self.page.locator("#budget").fill("0.000001")
        self.page.locator("#search-form button[type=submit]").click()
        self.assertIn("0 eligible demo suppliers", self.page.locator("#summary").inner_text())
        self.assertIn("Removed by filters", self.page.locator("#comparison").inner_text())
        self.assertFalse(self.errors, self.errors)


    def test_budget_filter_does_not_renormalize_experience(self):
        # Controlled synthetic fixture: only the budget changes. A supplier's
        # historical experience must not jump when another supplier drops out.
        self.page.evaluate("""() => {
          const sample = data.demo.find(r => r.item === 'Steel Coil (per ton)');
          const rows = [
            {id:'A',price:100,orders:100},
            {id:'B',price:10,orders:10},
            {id:'C',price:20,orders:15}
          ].map(x => ({...sample, supplier_id:'fixture-'+x.id,
            supplier_name:'Fixture '+x.id,
            avg_unit_price:String(x.price), historical_orders:String(x.orders)}));
          data.demo.splice(0, data.demo.length, ...rows);
        }""")
        self.search_demo()
        before = self.page.evaluate(
            "() => currentDemo.find(r => r.supplier_id === 'fixture-B').parts[2]"
        )
        self.page.locator("#budget").fill("25")
        self.page.locator("#search-form button[type=submit]").click()
        after = self.page.evaluate(
            "() => currentDemo.find(r => r.supplier_id === 'fixture-B').parts[2]"
        )
        self.assertAlmostEqual(before, after, places=7)
        self.assertFalse(self.errors, self.errors)

    def fill_rfq(self, *, zone="Asia/Kolkata", date="2099-12-31"):
        self.search_demo()
        self.page.locator("#start-rfq").click()
        self.assertTrue(self.page.locator("#request").is_visible())
        self.page.locator("#rfq-product").fill("Steel Coil")
        self.page.locator("#specs").fill("Grade A steel, exact specification to be confirmed")
        self.page.locator("#rfq-quantity").fill("10")
        self.page.locator("#unit").fill("ton")
        self.page.locator("#currency").fill("INR")
        self.page.locator("#destination").fill("Nagpur, Maharashtra, India")
        self.page.locator("#date").fill(date)
        self.page.locator("#zone").fill(zone)
        self.page.locator("#confirm").check()

    def test_request_draft_requires_review_and_does_not_purchase(self):
        self.fill_rfq()
        sent = []
        self.page.on("request", lambda request: sent.append(request.url)
                     if request.method != "GET" else None)
        self.page.locator("#rfq-form button[type=submit]").click()
        self.assertTrue(self.page.locator("#preview").is_visible())
        self.assertIn("This is a request, not a purchase order", self.page.locator("#draft").inner_text())
        self.assertEqual(sent, [], "RFQ preview must not send requests to a server")
        self.assertFalse(self.errors, self.errors)

    def test_invalid_destination_timezone_does_not_generate_request(self):
        self.fill_rfq(zone="Invalid/TimeZone")
        self.page.locator("#rfq-form button[type=submit]").click()
        self.assertIn("valid destination timezone", self.page.locator("#rfq-error").inner_text())
        self.assertFalse(self.page.locator("#preview").is_visible())
        self.assertFalse(self.errors, self.errors)

    def test_past_delivery_deadline_does_not_generate_request(self):
        self.fill_rfq(date="2000-01-01")
        self.page.locator("#rfq-form button[type=submit]").click()
        self.assertIn("future delivery date", self.page.locator("#rfq-error").inner_text())
        self.assertFalse(self.page.locator("#preview").is_visible())
        self.assertFalse(self.errors, self.errors)

    def test_editing_after_preview_invalidates_earlier_request(self):
        self.fill_rfq()
        self.page.locator("#rfq-form button[type=submit]").click()
        self.assertTrue(self.page.locator("#preview").is_visible())
        self.page.locator("#rfq-quantity").fill("20")
        self.assertFalse(self.page.locator("#preview").is_visible())
        self.assertFalse(self.errors, self.errors)


if __name__ == "__main__":
    unittest.main()
