"""Local demo API. Run python ml/api.py and proxy /api from your frontend."""
from datetime import datetime, timezone
from decimal import localcontext
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from catalog_search import search
from quotation_demo import build_demo
from real_procurement import amount, evaluate, no_duplicate_keys


@lru_cache(maxsize=1)
def suppliers():
    path = Path(__file__).with_name("public_supplier_leads.json")
    return json.loads(path.read_text(encoding="utf-8"))["suppliers"]


@lru_cache(maxsize=1)
def catalog():
    path = Path(__file__).with_name("catmat_research_catalog.json")
    return json.loads(path.read_text(encoding="utf-8"))["records"]


def quote_total(data):
    quantity = amount(data.get("quantity"), "quantity")
    price = amount(data.get("unit_price"), "unit_price", zero=True)
    costs = {}
    for key in ("freight", "tax", "other_costs"):
        value = data.get(key)
        costs[key] = None if value is None else amount(value, key, zero=True)
    missing = [key for key, value in costs.items() if value is None]
    with localcontext() as context:
        context.prec = 64
        subtotal = quantity * price
        total = None if missing else str(subtotal + sum(costs.values()))
    return {"subtotal": str(subtotal), "total": total, "missing": missing}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url = urlsplit(self.path)
        params = parse_qs(url.query)
        if url.path == "/api/suppliers":
            query = params.get("q", [""])[0].strip().casefold()
            matches = []
            for row in suppliers():
                titles = [item["title"] for item in row["evidence"]]
                if query in " ".join([row["name"], *titles]).casefold():
                    matches.append(row)
            try:
                offset = int(params.get("offset", ["0"])[0])
                limit = int(params.get("limit", ["50"])[0])
                if offset < 0 or not 1 <= limit <= 100:
                    raise ValueError
            except ValueError:
                return self.reply(400, {"error": "Expected offset >= 0 and limit 1 to 100"})
            self.reply(200, {"total": len(matches), "suppliers": matches[offset:offset+limit]})
        elif url.path == "/api/catalog":
            hits = search(catalog(), params.get("q", [""])[0], limit=50)
            self.reply(200, {"items": [dict(score=score, code=code, record=record)
                                       for score, code, record in hits]})
        elif url.path == "/api/health":
            self.reply(200, {"status": "ok"})
        elif url.path == "/api/compare":
            ids = list(dict.fromkeys(params.get("id", [])))
            indexed = {row["id"]: row for row in suppliers()}
            if not 2 <= len(ids) <= 5 or any(key not in indexed for key in ids):
                return self.reply(400, {"error": "Supply 2 to 5 distinct known id parameters"})
            self.reply(200, {"suppliers": [indexed[key] for key in ids]})
        elif url.path == "/api/quotes/demo":
            now = datetime.now(timezone.utc)
            self.reply(200, evaluate(build_demo(now), now, demo=True))
        else:
            self.reply(404, {"error": "Unknown route"})

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in ("/api/quotes/review", "/api/quotes/total"):
            return self.reply(404, {"error": "Unknown route"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1048576:
                return self.reply(400, {"error": "Expected JSON body up to 1 MiB"})
            bundle = json.loads(self.rfile.read(size).decode(), object_pairs_hook=no_duplicate_keys)
            if not isinstance(bundle, dict):
                raise ValueError("Expected a quotation bundle object")
            report = quote_total(bundle) if route.endswith("/total") else evaluate(bundle, datetime.now(timezone.utc))
        except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
            return self.reply(400, {"error": str(exc)})
        self.reply(200, report)


if __name__ == "__main__":
    ThreadingHTTPServer((os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8765"))), Handler).serve_forever()


