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
from simulated_suppliers import load_simulated_catalog, load_simulated_suppliers

PUBLIC_SUPPLIER_META = {
    "source_type": "public",
    "source_label": "Public source",
    "data_kind": "public",
    "source_reference": "UK Contracts Finder, Cabinet Office (Open Government Licence v3.0)",
}

PUBLIC_CATALOG_META = {
    "source_type": "public",
    "source_label": "Public source",
    "data_kind": "public",
    "source_reference": "CATMAT Public Catalog (Brazil procurement reference)",
}


@lru_cache(maxsize=1)
def suppliers():
    path = Path(__file__).with_name("public_supplier_leads.json")
    public_rows = [
        {**PUBLIC_SUPPLIER_META, **row}
        for row in json.loads(path.read_text(encoding="utf-8"))["suppliers"]
    ]
    return public_rows + load_simulated_suppliers()


@lru_cache(maxsize=1)
def catalog():
    path = Path(__file__).with_name("catmat_research_catalog.json")
    public_records = [
        {**PUBLIC_CATALOG_META, **row}
        for row in json.loads(path.read_text(encoding="utf-8"))["records"]
    ]
    return public_records + load_simulated_catalog()


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


def grade_confirmed(row, product, grade):
    """Return True only when one evidence entry mentions both product and grade."""
    if not (product and grade):
        return False
    p = product[:-1] if product.endswith("s") and len(product) > 3 else product
    for entry in row.get("evidence", []):
        title = str(entry.get("title") or "")
        desc = str(entry.get("description") or "")
        text = f"{title} {desc}".casefold()
        if f"no {p}" in text or f"without {p}" in text:
            continue
        if p in text and grade in text:
            return True
    return False


def filter_suppliers(rows, query="", product="", grade="", match="", source="", country=""):
    """Filter the full supplier dataset before pagination."""
    query = query.strip().casefold()
    product = product.strip().casefold()
    grade = grade.strip().casefold()
    source = source.strip().casefold()
    country = country.strip().casefold()
    matches = []
    for row in rows:
        if source and str(row.get("source_type") or "").casefold() != source:
            continue
        if country and str(row.get("country") or "").casefold() != country:
            continue
        if query:
            parts = [str(row.get("name") or ""), str(row.get("country") or ""), str(row.get("category") or "")]
            for item in row.get("evidence", []):
                parts.append(str(item.get("title") or ""))
                parts.append(str(item.get("description") or ""))
            if query not in " ".join(parts).casefold():
                continue
        if match == "confirmed" and not grade_confirmed(row, product, grade):
            continue
        if match == "unconfirmed" and grade_confirmed(row, product, grade):
            continue
        matches.append(row)

    if product:
        p = product[:-1] if product.endswith("s") and len(product) > 3 else product

        def relevance(row):
            confirmed = bool(grade and grade_confirmed(row, product, grade))
            has_prod = any(
                p in f"{e.get('title') or ''} {e.get('description') or ''}".casefold()
                for e in row.get("evidence", [])
            )
            is_sim = row.get("source_type") == "simulated"
            return (0 if confirmed else 1 if has_prod else 2, 0 if is_sim else 1)

        matches.sort(key=relevance)

    return matches


def cors_origin(request_origin):
    """Resolve allowed CORS origin from ALLOWED_ORIGINS env var."""
    configured = os.environ.get("ALLOWED_ORIGINS", "*").strip()
    if not configured or configured == "*":
        return "*", False
    if not request_origin:
        return None, True
    origin = request_origin.strip().rstrip("/")
    allowed = [item.strip().rstrip("/") for item in configured.split(",") if item.strip()]
    for pattern in allowed:
        if pattern == origin:
            return request_origin.strip(), True
        if pattern.startswith("https://*.") and origin.startswith("https://") and origin.endswith(pattern[len("https://*"):]):
            return request_origin.strip(), True
        if pattern.startswith("*.") and origin.endswith(pattern[1:]):
            return request_origin.strip(), True
    return None, True


class Handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        origin, vary = cors_origin(self.headers.get("Origin"))
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        if vary:
            self.send_header("Vary", "Origin")

    def reply(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url = urlsplit(self.path)
        params = parse_qs(url.query)
        if url.path == "/api/suppliers":
            query = params.get("q", [""])[0]
            product = params.get("product", [""])[0]
            grade = params.get("grade", [""])[0]
            match = params.get("match", [""])[0].strip()
            source = params.get("source", [""])[0].strip()
            country = params.get("country", [""])[0].strip()
            if match not in ("", "confirmed", "unconfirmed"):
                return self.reply(400, {"error": "match must be confirmed or unconfirmed"})
            if match and not (product.strip() and grade.strip()):
                return self.reply(400, {"error": "match requires product and grade"})
            if source not in ("", "public", "simulated"):
                return self.reply(400, {"error": "source must be public or simulated"})
            matches = filter_suppliers(suppliers(), query, product, grade, match, source, country)
            try:
                offset = int(params.get("offset", ["0"])[0])
                limit = int(params.get("limit", ["50"])[0])
                if offset < 0 or not 1 <= limit <= 100:
                    raise ValueError
            except ValueError:
                return self.reply(400, {"error": "Expected offset >= 0 and limit 1 to 100"})
            self.reply(200, {"total": len(matches), "suppliers": matches[offset:offset + limit]})
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
    default_host = "0.0.0.0" if ("PORT" in os.environ or "RENDER" in os.environ) else "127.0.0.1"
    ThreadingHTTPServer((os.environ.get("HOST", default_host), int(os.environ.get("PORT", "8765"))), Handler).serve_forever()
