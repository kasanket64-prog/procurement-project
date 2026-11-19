"""Exercise HTTP parsing, routing and JSON responses without opening a port."""
from datetime import datetime, timezone
from io import BytesIO
import json
import unittest
from urllib.parse import urlencode

from api import Handler, catalog, suppliers
from quotation_demo import build_demo


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


if __name__ == "__main__":
    unittest.main()

