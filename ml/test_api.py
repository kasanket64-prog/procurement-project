"""Exercise HTTP parsing, routing and JSON responses without opening a port."""
from datetime import datetime, timezone
from io import BytesIO
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

from api import Handler, catalog, suppliers
from quotation_demo import build_demo
from test_fixtures import get_test_suppliers


class StreamSocket:
    def __init__(self, raw):
        self.input = BytesIO(raw)
        self.output = BytesIO()

    def makefile(self, *args):
        return self.input

    def sendall(self, data):
        self.output.write(data)


def request(path, data=None):
    body = json.dumps(data).encode() if data is not None else b""
    method = "POST" if data is not None else "GET"
    head = f"{method} {path} HTTP/1.0\r\nContent-Length: {len(body)}\r\n\r\n"
    stream = StreamSocket(head.encode() + body)
    Handler(stream, ("localhost", 0), None)
    headers, payload = stream.output.getvalue().split(b"\r\n\r\n", 1)
    return int(headers.split()[1]), json.loads(payload)


class ApiTests(unittest.TestCase):
    def test_discovery(self):
        self.assertEqual(request("/api/health")[0], 200)
        rows = suppliers()
        self.assertEqual(request("/api/suppliers?offset=1&limit=1")[1]["suppliers"], rows[1:2])
        self.assertEqual(request("/api/suppliers?q=___absent___")[1]["total"], 0)
        self.assertEqual(request("/api/suppliers?limit=-1")[0], 400)
        ids = urlencode([("id", row["id"]) for row in rows[:2]])
        self.assertEqual(request("/api/compare?" + ids)[1]["suppliers"], rows[:2])
        self.assertEqual(request("/api/compare?id=unknown")[0], 400)
        code = str(catalog()[0]["source_record"]["codigoItem"])
        self.assertIn(code, [row["code"] for row in request("/api/catalog?q="+code)[1]["items"]])

    def test_totals(self):
        for price, freight, expected in [("100","1500","11500"),("108","0","10800"),
                                         ("100","500","10500"),("100",None,None)]:
            data = dict(quantity="100", unit_price=price, freight=freight, tax="0", other_costs="0")
            self.assertEqual(request("/api/quotes/total", data)[1]["total"], expected)

    def test_review(self):
        self.assertEqual(request("/api/quotes/demo")[1]["eligible_quotes"], 1)
        fixture = build_demo(datetime.now(timezone.utc))
        self.assertEqual(request("/api/quotes/review", fixture)[0], 400)
        # Exercise the operator-declared input contract using a test fixture only.
        fixture["sources"][0].update(data_kind="real", permission_confirmed=True)
        status, report = request("/api/quotes/review", fixture)
        self.assertEqual(status, 200)
        self.assertEqual(report["eligible_quotes"], 1)
        self.assertFalse(report["purchase_authorized"])
        self.assertEqual(request("/api/quotes/review", {})[0], 400)

    def test_fixture_isolation_and_grade_filtering(self):
        fixture_ids = {"SUP-GRADE-100Cr6", "SUP-NOGRADE", "SUP-MIN500"}
        seen_ids = set()
        offset = 0
        while True:
            status, body = request(f"/api/suppliers?offset={offset}&limit=100")
            self.assertEqual(status, 200)
            seen_ids.update(row["id"] for row in body["suppliers"])
            offset += 100
            if offset >= body["total"]:
                break
        self.assertTrue(seen_ids.isdisjoint(fixture_ids))
        self.assertEqual(request("/api/suppliers?limit=1000")[0], 400)

        with patch("api.suppliers", return_value=get_test_suppliers()):
            s0, page0 = request("/api/suppliers?product=bearing&grade=100Cr6&match=confirmed&limit=1&offset=0")
            s1, page1 = request("/api/suppliers?product=bearing&grade=100Cr6&match=confirmed&limit=1&offset=1")
            self.assertEqual((s0, s1), (200, 200))
            self.assertEqual(page0["total"], 2)
            self.assertEqual(page1["total"], 2)
            id0 = page0["suppliers"][0]["id"]
            id1 = page1["suppliers"][0]["id"]
            self.assertNotEqual(id0, id1)
            self.assertEqual({id0, id1}, {"SUP-GRADE-100Cr6", "SUP-MIN500"})

            su, unconfirmed = request("/api/suppliers?product=bearing&grade=100Cr6&match=unconfirmed")
            self.assertEqual(su, 200)
            self.assertEqual([row["id"] for row in unconfirmed["suppliers"]], ["SUP-NOGRADE"])

    def test_public_and_simulated_integration(self):
        sp, pub = request("/api/suppliers?source=public&limit=5")
        ss, sim = request("/api/suppliers?source=simulated&limit=5")
        self.assertEqual((sp, ss), (200, 200))
        self.assertEqual(pub["total"], 248)
        self.assertEqual(sim["total"], 113)
        self.assertTrue(all(row["source_label"] == "Public source" for row in pub["suppliers"]))
        self.assertTrue(all(row["source_label"] == "Simulated" for row in sim["suppliers"]))
        self.assertEqual(request("/api/suppliers?source=unknown")[0], 400)

        sc, confirmed = request("/api/suppliers?product=bearing&grade=100Cr6&match=confirmed&limit=50")
        self.assertEqual(sc, 200)
        confirmed_ids = {row["id"] for row in confirmed["suppliers"]}
        self.assertIn("SIM-201", confirmed_ids)
        self.assertIn("SIM-203", confirmed_ids)
        self.assertIn("SUP-038", confirmed_ids)
        self.assertNotIn("SIM-207", confirmed_ids)  # split shaft/bearing evidence must not qualify

        # Combined compare across one public and one simulated supplier
        cid_pub = pub["suppliers"][0]["id"]
        status_cmp, cmp_body = request("/api/compare?" + urlencode([("id", cid_pub), ("id", "SIM-201")]))
        self.assertEqual(status_cmp, 200)
        self.assertEqual([r["source_label"] for r in cmp_body["suppliers"]], ["Public source", "Simulated"])

        # Catalog search spans both public CATMAT and simulated items
        s_sim, sim_cat = request("/api/catalog?q=bearing")
        s_pub, pub_cat = request("/api/catalog?q=207085")
        self.assertEqual((s_sim, s_pub), (200, 200))
        self.assertTrue(any(item["record"].get("source_label") == "Simulated" for item in sim_cat["items"]))
        self.assertTrue(any(item["record"].get("source_label") == "Public source" for item in pub_cat["items"]))


if __name__ == "__main__":
    unittest.main()

