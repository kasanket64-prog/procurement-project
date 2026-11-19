"""Load deterministic simulated supplier and catalog data from existing repository datasets."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT / "dataset"
ML_DIR = Path(__file__).resolve().parent

SIMULATED_SOURCE_META = {
    "source_type": "simulated",
    "source_label": "Simulated",
    "data_kind": "synthetic",
}

_GRADE_NOTES = {
    "SUP-038": "Deep groove ball bearings · Grade 100Cr6 high-volume MRO series (simulated spec).",
    "SUP-039": "Deep groove ball bearings · Grade 100Cr6 maintenance replacement series (simulated spec).",
    "SUP-040": "Deep groove ball bearings · Grade 101Cr7 industrial series (simulated spec).",
}


def _scenario_suppliers():
    """Return 7 realistic scenario suppliers used across bearing and workflow demos."""
    ref = "ProcureAI scenario simulation (synthetic vendor & quotation benchmark)"
    specs = [
        (
            "SIM-201", "Atlas Industrial", "India", "12 days", 50, 100.0, "INR",
            92.4, 7.6, 184, 8.1, "MRO",
            [
                {
                    "title": "Industrial bearings — Deep groove · Grade 100Cr6 datasheet",
                    "description": "ISO 9001 quality management certificate and 100Cr6 chrome steel bearing catalogue (Simulated).",
                    "published_at": "2026-03-10",
                },
                {
                    "title": "Atlas Industrial MRO fulfillment record",
                    "description": "184 simulated historical orders · 92.4% on-time delivery · MOQ 50 units.",
                    "published_at": "2026-04-02",
                },
            ],
        ),
        (
            "SIM-202", "Nova Supply Co.", "Singapore", "9 days", 100, 108.0, "INR",
            95.2, 4.8, 310, 5.2, "MRO",
            [
                {
                    "title": "Industrial bearings · Deep groove Grade 100Cr6 specification sheet",
                    "description": "Precision 100Cr6 bearing tolerances and dispatch schedule from Singapore hub (Simulated).",
                    "published_at": "2026-03-18",
                },
                {
                    "title": "Nova Supply Co. delivery benchmark",
                    "description": "310 simulated historical orders · 95.2% on-time delivery · MOQ 100 units.",
                    "published_at": "2026-04-05",
                },
            ],
        ),
        (
            "SIM-203", "Kinetic Components", "Germany", "14 days", 500, 94.0, "INR",
            88.5, 11.5, 96, 11.6, "MRO",
            [
                {
                    "title": "Industrial bearings · Deep groove · Grade 100Cr6 bulk batch",
                    "description": "High-volume 100Cr6 steel bearing supply requiring 500-unit minimum order quantity (Simulated).",
                    "published_at": "2026-02-22",
                },
            ],
        ),
        (
            "SIM-204", "Precision Motion Ltd.", "United Kingdom", "15 days", 50, 112.0, "INR",
            91.0, 9.0, 142, 9.3, "MRO",
            [
                {
                    "title": "Industrial bearings · Deep groove Grade 101Cr7 catalogue",
                    "description": "Heat-treated 101Cr7 raceway bearings for heavy radial loads (Simulated).",
                    "published_at": "2026-03-27",
                },
            ],
        ),
        (
            "SIM-205", "Bharat Motion Systems", "India", "8 days", 200, 104.0, "INR",
            90.4, 9.6, 215, 9.8, "MRO",
            [
                {
                    "title": "Industrial bearings · Grade 101Cr7 & Grade 100Cr6 dual-grade catalog",
                    "description": "Domestic stock-to-order manufacturing in Grade 100Cr6 and Grade 101Cr7 bearings (Simulated).",
                    "published_at": "2026-04-01",
                },
            ],
        ),
        (
            "SIM-206", "Nippon Bearing Works", "Japan", "11 days", 100, 115.0, "INR",
            94.8, 5.2, 410, 5.5, "MRO",
            [
                {
                    "title": "Standard industrial bearings assembly catalogue",
                    "description": "General deep-groove bearings and assemblies; steel grade requires supplier confirmation (Simulated).",
                    "published_at": "2026-03-04",
                },
            ],
        ),
        (
            "SIM-207", "Nordic Industrial AB", "Sweden", None, 100, None, None,
            89.0, 11.0, 74, 11.2, "MRO",
            [
                {
                    "title": "Precision ground steel shafts · Grade 100Cr6",
                    "description": "Hardened 100Cr6 linear shafts and drive rods (no bearing assembly).",
                    "published_at": "2026-01-19",
                },
                {
                    "title": "Standard industrial bearings housing",
                    "description": "Cast pillow-block housings; alloy grade unspecified.",
                    "published_at": "2026-02-11",
                },
            ],
        ),
    ]
    rows = []
    for sid, name, country, delivery, moq, price, currency, otr, ldr, orders, risk, cat, evidence in specs:
        rows.append({
            **SIMULATED_SOURCE_META,
            "id": sid,
            "name": name,
            "country": country,
            "delivery": delivery,
            "min_order": moq,
            "unit_price": price,
            "currency": currency,
            "on_time_rate": otr,
            "late_delivery_rate": ldr,
            "completed_orders": orders,
            "risk_estimate": risk,
            "category": cat,
            "source_reference": ref,
            "evidence": evidence,
        })
    return rows


def load_simulated_suppliers():
    """Combine scenario suppliers with the 106 dataset/suppliers.csv vendors."""
    items_by_supplier = {}
    items_path = DATASET_DIR / "supplier_items.csv"
    if items_path.exists():
        with items_path.open(encoding="utf-8-sig", newline="") as handle:
            for item in csv.DictReader(handle):
                items_by_supplier.setdefault(item["supplier_id"], []).append(item)

    csv_rows = []
    suppliers_path = DATASET_DIR / "suppliers.csv"
    if suppliers_path.exists():
        with suppliers_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                sid = row["supplier_id"]
                completed = int(float(row["total_orders"]))
                late_rate = float(row["late_delivery_rate"])
                on_time = float(row["on_time_rate"])
                avg_delay = max(0.0, float(row["avg_delivery_delay"]))
                avg_qty = float(row["avg_order_quantity"])
                avg_price = round(float(row["avg_unit_price"]), 2)
                late_orders = round(completed * (late_rate / 100.0))
                smoothed_risk = round((late_orders + 10 * 0.12) / (completed + 10) * 100, 1)
                lead_days = round(10 + min(8.0, avg_delay))
                min_order = 500 if sid == "SUP-038" else (100 if avg_qty >= 50 else 50)

                item_rows = items_by_supplier.get(sid, [])
                evidence = []
                for item in item_rows:
                    item_name = item["item"]
                    extra = f" {_GRADE_NOTES[sid]}" if sid in _GRADE_NOTES and "bearing" in item_name.lower() else ""
                    evidence.append({
                        "title": f"{item_name} — {row['supplier_name']} supply history",
                        "description": (
                            f"{item['historical_orders']} historical orders · Avg unit price ${item['avg_unit_price']} · "
                            f"On-time {item['on_time_rate']}% (Simulated dataset).{extra}"
                        ),
                        "category": item["category"],
                    })
                if not evidence:
                    evidence.append({
                        "title": f"{row['categories']} — {row['items']}",
                        "description": f"{completed} historical orders · {on_time:.1f}% on-time rate (Simulated dataset).",
                        "category": row["categories"],
                    })

                csv_rows.append({
                    **SIMULATED_SOURCE_META,
                    "id": sid,
                    "name": row["supplier_name"],
                    "country": row["supplier_country"],
                    "delivery": f"{lead_days} days",
                    "min_order": min_order,
                    "unit_price": avg_price,
                    "currency": "USD",
                    "on_time_rate": round(on_time, 2),
                    "late_delivery_rate": round(late_rate, 2),
                    "completed_orders": completed,
                    "risk_estimate": smoothed_risk,
                    "category": row["categories"],
                    "source_reference": "ProcureAI deterministic simulation dataset (dataset/suppliers.csv)",
                    "evidence": evidence,
                })

    return _scenario_suppliers() + csv_rows


def load_simulated_catalog():
    """Convert ml/search_catalog.json items into catalog_search-compatible records."""
    path = ML_DIR / "search_catalog.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    provenance = payload.get("provenance", "Simulated procurement catalog reference.")
    records = []
    for idx, entry in enumerate(payload.get("items", []), 1):
        name = str(entry.get("item", "")).strip()
        aliases = [str(a).strip() for a in entry.get("aliases", []) if str(a).strip()]
        code = f"SIM-CAT-{idx:03d}"
        records.append({
            **SIMULATED_SOURCE_META,
            "source_reference": provenance,
            "english_title": name,
            "english_description": f"Aliases: {', '.join(aliases)} (Simulated reference; specifications unverified)." if aliases else "Simulated reference item.",
            "source_record": {
                "codigoItem": code,
                "nomeGrupo": "SIMULATED CATALOG",
                "nomeClasse": "SYNTHETIC PROCUREMENT ITEM",
                "nomePdm": name,
                "descricaoItem": ", ".join([name, *aliases]),
            },
        })
    return records
