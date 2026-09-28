"""Adapter from the real-pilot JSON bundle to Quotation Schema v1.

The adapter preserves the existing intake format and deliberately does not
invent missing commercial facts. It is intended for validation and audit
output; the existing real_procurement evaluator remains the decision engine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List

from quotation_schema import (
    CategoryMappingConfidence, CommitmentType, Costs, Delivery, EntityLinkStatus,
    IdentifierScheme, Product, Provenance, QuotationRecord, RealOrSynthetic,
    SourceType, Supplier, TaxStatus, Validity, ValidityStatus,
    Review, UnresolvedItem, assert_usable_for_comparison,
)


class MappingError(ValueError):
    """A source value cannot be represented without making an assumption."""



def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise MappingError('Source timestamp must include timezone')
    return parsed


def _source_type(source) -> SourceType:
    try:
        result = SourceType(source['source_type'])
    except (KeyError, ValueError):
        raise MappingError('Explicit source_type required; real does not imply quotation') from None
    if source.get('data_kind') not in ('real', 'synthetic'):
        raise MappingError('Unknown data kind')
    if (result == SourceType.SYNTHETIC) != (source['data_kind'] == 'synthetic'):
        raise MappingError('Source labels disagree')
    return result


def _money(value):
    if not isinstance(value, str):
        raise MappingError('Decimal string required')
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise MappingError('Finite nonnegative amount required')
    return result


COUNTRY_NAME_TO_ISO = {
    "india": "IN",
    "united states": "US",
    "germany": "DE",
    "japan": "JP",
    "canada": "CA",
    "mexico": "MX",
    "denmark": "DK",
}


def resolve_country_code(value: str) -> str:
    """Convert only explicitly supported names or ISO alpha-2 values.

    No slicing, fuzzy matching or inference is allowed. Unknown values must
    be corrected by the operator before a record enters the frozen schema.
    """
    normalized = str(value).strip()
    if len(normalized) == 2 and normalized.isalpha() and normalized.isupper():
        return normalized
    code = COUNTRY_NAME_TO_ISO.get(normalized.casefold())
    if code:
        return code
    raise MappingError(
        f"country is not an accepted ISO alpha-2 code or supported exact name: {value!r}"
    )


def _supplier_id_scheme(supplier: Dict[str, Any]) -> IdentifierScheme:
    raw = supplier.get("id_scheme") or supplier.get("supplier_id_scheme")
    if raw:
        return IdentifierScheme(raw)
    return IdentifierScheme.NONE


def _tax_status(quote: Dict[str, Any]) -> TaxStatus:
    if quote.get("tax_status") in TaxStatus._value2member_map_:
        return TaxStatus(quote["tax_status"])
    included = quote.get("all_costs_included")
    if included is True:
        return TaxStatus.INCLUDED
    return TaxStatus.UNKNOWN


def _validity(quote: Dict[str, Any], now: datetime) -> Validity:
    issued = _dt(quote["issued_at"])
    expires = _dt(quote["valid_until"]) if quote.get("valid_until") else None
    status = ValidityStatus.NO_EXPIRY_STATED if expires is None else (
        ValidityStatus.ACTIVE if now < expires else ValidityStatus.EXPIRED
    )
    return Validity(issued_at=issued, expires_at=expires,
                    revision_number=quote.get("revision_number"), status=status)


def map_bundle(bundle: Dict[str, Any], *, delivery_country: str,
               as_of: datetime | None = None) -> List[QuotationRecord]:
    """Map each quote in an intake bundle to a validated schema record."""
    as_of = as_of or datetime.now(timezone.utc)
    if as_of.utcoffset() is None:
        raise MappingError('Decision timestamp requires timezone')
    if not (isinstance(delivery_country, str) and len(delivery_country) == 2
            and delivery_country.isascii() and delivery_country.isalpha() and delivery_country.isupper()):
        raise MappingError('Delivery country requires two uppercase ASCII letters')
    products = {p["id"]: p for p in bundle["products"]}
    suppliers = {s["id"]: s for s in bundle["suppliers"]}
    request = bundle["request"]
    records: List[QuotationRecord] = []
    for quote in bundle["quotes"]:
        supplier_data = suppliers[quote["supplier_id"]]
        product_data = products[quote["product_id"]]
        source_type = _source_type(next(
            s for s in bundle["sources"] if s["id"] == quote["source_id"]
        ))
        supplier = Supplier(
            name_raw=supplier_data["name"], country=resolve_country_code(supplier_data["country"]),
            id_scheme=_supplier_id_scheme(supplier_data), id=supplier_data.get("supplier_id"),
            entity_link_status=EntityLinkStatus.UNLINKED,
        )
        product = Product(
            description_raw=quote['description_raw'], quantity=_money(quote["quantity"]),
            unit_of_measure=quote["unit"], unit_scheme="source-native",
            internal_category='',
            category_mapping_confidence=CategoryMappingConfidence.UNMAPPED,
        )
        tax_status = _tax_status(quote)
        if quote.get('goods_amount') is None:
            raise MappingError('Missing goods amount; total cannot substitute for goods amount')
        costs = Costs(currency=quote["currency"], goods_amount=_money(quote['goods_amount']),
                      tax_status=tax_status, total_payable_amount=_money(quote["total_amount"]),
                      total_payable_is_computed=False,
                      excluded_charges=list(quote.get('excluded_charges', [])))
        delivery = Delivery(
            delivery_country=delivery_country,
            delivery_destination=quote["destination_id"],
            commitment_type=CommitmentType.FIXED_DATE,
            commitment_date=datetime.fromisoformat(quote["promised_delivery_date"]).date(),
            commitment_timezone=request["decision_timezone"],
            conditions_raw=quote.get('delivery_conditions_raw'),
        )
        source = next(s for s in bundle["sources"] if s["id"] == quote["source_id"])
        provenance = Provenance(
            record_id=quote["id"], source_document=source["reference"],
            source_type=source_type, source_organization=supplier.name_raw,
            retrieved_at=_dt(quote["received_at"]),
            real_or_synthetic=RealOrSynthetic.SYNTHETIC if source_type is SourceType.SYNTHETIC else RealOrSynthetic.REAL,
        )
        record = QuotationRecord(provenance, supplier, product, costs, delivery, _validity(quote, as_of))
        assert_usable_for_comparison(record)
        issues = record.collect_unresolved_from_costs()
        issues.append(UnresolvedItem('category', 'No reviewed category mapping supplied'))
        for field, ok in [('complete_costs', quote.get('all_costs_included') is True),
                          ('specifications', quote.get('specification_confirmed') is True),
                          ('destination', quote['destination_id'] == request['destination_id'])]:
            if not ok:
                issues.append(UnresolvedItem(field, 'Not confirmed against requirement'))
        record.review = Review(request.get('id', request['product_id']), unresolved=issues)
        records.append(record)
    return records
