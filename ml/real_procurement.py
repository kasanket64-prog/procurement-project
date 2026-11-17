"""Local, human-reviewed quotation pilot. No model training or purchase execution.

This deliberately does not import the synthetic recommendation pipeline.
Input provenance is declared by the operator, not independently authenticated.
"""
import argparse
from datetime import datetime, timezone, date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class DataError(ValueError):
    pass


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise DataError(f'{label}: a nonempty string is required')
    return value.strip()


def amount(value, label, *, zero=False):
    # Decimal strings prevent silent binary-float changes to commercial amounts.
    if not isinstance(value, str):
        raise DataError(f'{label}: use a decimal string')
    if not re.fullmatch(r'\d{1,18}(\.\d{1,6})?', value):
        raise DataError(f'{label}: use up to 18 digits and 6 decimal places, without separators')
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise DataError(f'{label}: invalid decimal') from None
    if not result.is_finite() or result < 0 or (not zero and result == 0):
        raise DataError(f'{label}: invalid amount')
    return result


def timestamp(value, label):
    try:
        result = datetime.fromisoformat(text(value, label).replace('Z', '+00:00'))
    except ValueError:
        raise DataError(f'{label}: expected ISO timestamp with timezone') from None
    if result.tzinfo is None:
        raise DataError(f'{label}: timezone required')
    try:
        return result.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise DataError(f'{label}: timestamp is outside the supported UTC range') from None


def day(value, label):
    try:
        return date.fromisoformat(text(value, label))
    except ValueError:
        raise DataError(f'{label}: expected YYYY-MM-DD') from None


def decision_zone(value):
    """Resolve an explicitly supplied destination zone."""
    name = text(value, 'request.decision_timezone')
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        raise DataError('Use a valid destination zone, such as Asia/Kolkata or Europe/London. Install tzdata if the timezone database is missing.') from None


def indexed(rows, name, *, required=True):
    if not isinstance(rows, list) or (required and not rows):
        raise DataError(f'{name}: nonempty list required')
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise DataError(f'{name}: each entry must be an object')
        key = text(row.get('id'), f'{name}.id')
        if key in result:
            raise DataError(f'{name}: duplicate ID')
        result[key] = row
    return result


def brand_review(request, quote):
    """Compare declared identifiers only; never infer brand or equivalence from prose."""
    policy = request.get('brand_policy', 'exact')
    if policy not in ('exact', 'alternatives'):
        raise DataError('brand_policy must be exact or alternatives')
    missing, mismatches = [], []
    details = {}
    for label, required_key, offered_key in (
            ('Brand', 'required_brand', 'offered_brand'),
            ('Model/part number', 'required_model', 'offered_model')):
        required, offered = request.get(required_key), quote.get(offered_key)
        if required is not None:
            required = text(required, required_key)
        if offered is not None:
            offered = text(offered, offered_key)
        details[required_key], details[offered_key] = required, offered
        if required is None:
            continue
        if offered is None:
            missing.append(label + ' not stated in quotation')
        elif ' '.join(required.casefold().split()) != ' '.join(offered.casefold().split()):
            mismatches.append(label + ' differs from requested value')
    constrained = any(details[k] is not None for k in ('required_brand', 'required_model'))
    status = 'not_requested' if not constrained else 'matched'
    reasons = missing + mismatches
    if missing:
        status = 'missing_information'
    elif mismatches:
        status = 'alternative_pending_review' if policy == 'alternatives' else 'mismatch'
        if policy == 'alternatives':
            reasons.append('Alternative requires buyer review; excluded from eligible ranking')
    return dict(details, policy=policy, status=status, reasons=reasons)


def evaluate(bundle, as_of, *, demo=False):
    """Return a fresh quote report, without mutating inputs or using synthetic risk."""
    if as_of.tzinfo is None:
        raise DataError('Decision timestamp must include timezone')
    as_of = as_of.astimezone(timezone.utc)
    if not isinstance(bundle, dict) or bundle.get('schema_version') != '1.0':
        raise DataError('Expected a version 1.0 bundle object')
    sources = indexed(bundle.get('sources'), 'sources')
    products = indexed(bundle.get('products'), 'products')
    suppliers = indexed(bundle.get('suppliers'), 'suppliers')
    quotes = indexed(bundle.get('quotes'), 'quotes')
    request = bundle.get('request')
    if not isinstance(request, dict):
        raise DataError('request must be an object')

    for source in sources.values():
        if demo and source.get('data_kind') != 'synthetic':
            raise DataError('Demo mode requires exclusively synthetic sources')
        if not demo and (source.get('data_kind') != 'real' or source.get('permission_confirmed') is not True):
            raise DataError('Sources must be declared real and authorized for this use')
        text(source.get('reference'), 'source.reference')
        text(source.get('reviewed_by'), 'source.reviewed_by')
        if timestamp(source.get('reviewed_at'), 'source.reviewed_at') > as_of:
            raise DataError('Source review cannot be in the future')

    def provenance(row, label):
        if text(row.get('source_id'), label + '.source_id') not in sources:
            raise DataError(f'{label}: unknown source')
        text(row.get('source_record_id'), label + '.source_record_id')

    for product in products.values():
        provenance(product, 'product')
        text(product.get('name'), 'product.name')
        text(product.get('specification'), 'product.specification')
        text(product.get('unit'), 'product.unit')
    for supplier in suppliers.values():
        provenance(supplier, 'supplier')
        text(supplier.get('name'), 'supplier.name')
        text(supplier.get('country'), 'supplier.country')

    product_id = text(request.get('product_id'), 'request.product_id')
    if product_id not in products:
        raise DataError('Request product is not in the catalog')
    currency = text(request.get('currency'), 'request.currency')
    if not re.fullmatch('[A-Z]{3}', currency):
        raise DataError('Currency must be a three-letter uppercase code; verify it with the source')
    # Only the original India-only format can omit this field.
    legacy_zone = 'decision_timezone' not in request and currency == 'INR'
    destination_zone = decision_zone('Asia/Kolkata' if legacy_zone else request.get('decision_timezone'))
    unit = text(request.get('unit'), 'request.unit')
    if unit != products[product_id]['unit']:
        raise DataError('Request unit must match the catalog; no implicit conversions')
    destination = text(request.get('destination_id'), 'request.destination_id')
    quantity = amount(request.get('quantity'), 'request.quantity')
    budget = amount(request.get('total_budget'), 'request.total_budget')
    needed = day(request.get('needed_by'), 'request.needed_by')
    decision_day_local = as_of.astimezone(destination_zone).date()
    if needed < decision_day_local:
        raise DataError('Requested delivery deadline is in the past')
    country = request.get('supplier_country')
    if country is not None:
        country = text(country, 'request.supplier_country')
    rows = []
    source_quote_ids = set()
    for quote_id, quote in quotes.items():
        provenance(quote, 'quote')
        identity = (quote['source_id'], quote['source_record_id'])
        if identity in source_quote_ids:
            raise DataError('Duplicate quote source record; resolve revisions before comparing')
        source_quote_ids.add(identity)
        supplier_id = text(quote.get('supplier_id'), 'quote.supplier_id')
        quoted_product = text(quote.get('product_id'), 'quote.product_id')
        if supplier_id not in suppliers or quoted_product not in products:
            raise DataError('Quote refers to an unknown supplier or product')
        issued = timestamp(quote.get('issued_at'), 'quote.issued_at')
        received = timestamp(quote.get('received_at'), 'quote.received_at')
        expires = timestamp(quote.get('valid_until'), 'quote.valid_until')
        reviewed = timestamp(quote.get('reviewed_at'), 'quote.reviewed_at')
        text(quote.get('reviewed_by'), 'quote.reviewed_by')
        if not issued <= received <= reviewed or expires < issued:
            raise DataError('Quote timestamps are inconsistent')
        total = amount(quote.get('total_amount'), 'quote.total_amount')
        offered_quantity = amount(quote.get('quantity'), 'quote.quantity')
        quoted_currency = text(quote.get('currency'), 'quote.currency')
        if not re.fullmatch('[A-Z]{3}', quoted_currency):
            raise DataError('Quote currency must be a three-letter uppercase code')
        quoted_unit = text(quote.get('unit'), 'quote.unit')
        text(quote.get('destination_id'), 'quote.destination_id')
        text(quote.get('terms_reference'), 'quote.terms_reference')
        promised = day(quote.get('promised_delivery_date'), 'quote.promised_delivery_date')
        if promised < issued.astimezone(destination_zone).date():
            raise DataError('Quote delivery date precedes issue date')
        reasons = []
        brand = brand_review(request, quote)
        reasons.extend(brand['reasons'])
        if issued > as_of or received > as_of or reviewed > as_of:
            reasons.append('Quote or review not available at decision time')
        if expires <= as_of:
            reasons.append('Quote expired')
        if quoted_product != product_id:
            reasons.append('Different product ID')
        if quote.get('specification_confirmed') is not True:
            reasons.append('Exact specifications not confirmed')
        if quoted_unit != unit:
            reasons.append('Different purchasing unit; conversion not verified')
        if offered_quantity != quantity:
            reasons.append('Quote must cover the exact requested quantity; obtain a revised quote')
        if quoted_currency != currency:
            reasons.append('Different currency; no exchange-rate conversion applied')
        if quote['destination_id'] != destination:
            reasons.append('Different delivery destination')
        if quote.get('all_costs_included') is not True:
            reasons.append('Complete taxes, freight and applicable duties not confirmed')
        if country and suppliers[supplier_id]['country'].casefold() != country.casefold():
            reasons.append('Supplier country does not match')
        if promised > needed:
            reasons.append('Delivery commitment misses requested deadline')
        if promised < decision_day_local:
            reasons.append('Delivery commitment is in the past; obtain a revised quote')
        if quoted_currency == currency and total > budget:
            reasons.append('Total exceeds budget')
        rows.append({'quote_id': quote_id, 'supplier_id': supplier_id,
                     'eligible': not reasons, 'reasons': reasons,
                     'currency': quoted_currency, 'quoted_total': str(total),
                     'cost_rank': None, 'risk_estimate': None})
        rows[-1]['brand_review'] = brand
    eligible = sorted((r for r in rows if r['eligible']), key=lambda r: (Decimal(r['quoted_total']), r['quote_id']))
    previous, rank = None, None
    for position, row in enumerate(eligible, 1):
        value = Decimal(row['quoted_total'])
        if value != previous:
            rank = position
        row['cost_rank'] = rank
        previous = value
    return {'schema_version': '1.0', 'decision_at': as_of.isoformat(),
            'status': 'SYNTHETIC_DEMONSTRATION' if demo else 'QUOTATION_REVIEW_ONLY', 'purchase_authorized': False,
            'risk_status': 'Unavailable: real delivery history has not been validated',
            'provenance_status': 'Fictional suppliers and quotations for demonstration only' if demo else 'Operator declarations; authenticity not independently verified',
            'ranking_basis': 'Lowest documented total among eligible quotes; not overall supplier quality',
            'currency': currency, 'decision_timezone': destination_zone.key,
            'timezone_basis': 'Legacy India input: Asia/Kolkata' if legacy_zone else 'Explicit destination timezone',
            'eligible_quotes': len(eligible), 'quotes': rows}


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DataError('Duplicate JSON key')
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        bundle = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=no_duplicate_keys)
        report = evaluate(bundle, datetime.now(timezone.utc))
        report['input_sha256'] = hashlib.sha256(raw).hexdigest()
        report['engine_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        # Exclusive creation preserves earlier decision evidence.
        with args.output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2)
        print(f"Quote review saved. Eligible quotes: {report['eligible_quotes']}. Human approval required.")
        return 0
    except (DataError, OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f'Cannot create quote review: {error}')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
