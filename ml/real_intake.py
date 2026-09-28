"""Guided local intake for a multi-country quotation pilot; nothing is sent."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
from dataclasses import asdict
from quotation_mapping import map_bundle

from real_procurement import DataError, amount, day, decision_zone, evaluate, brand_review


class Cancelled(Exception):
    pass


def menu_choice(value):
    if value not in ('1', '2'):
        raise ValueError('Choose 1 or 2.')


def currency_code(value):
    if len(value) != 3 or not value.isascii() or not value.isalpha() or not value.isupper():
        raise ValueError('Enter three uppercase letters, for example INR.')


def iso_country_code(value):
    """Syntax validation only; no claim of ISO registry membership."""
    if len(value) != 2 or not value.isascii() or not value.isalpha() or not value.isupper():
        raise ValueError('Enter two uppercase country-code letters, for example IN or GB.')


def read(label, validate=None, *, ask=input, tell=print, default=None):
    while True:
        value = ask(label + (f' [{default}]' if default is not None else '') + ': ').strip()
        if value.casefold() == 'cancel':
            raise Cancelled()
        value = value or default
        if value is None or value == '':
            tell('Please enter a value, or type cancel.')
            continue
        try:
            if validate:
                validate(value)
            return value
        except (DataError, ValueError) as error:
            tell(str(error))


def yes(label, *, ask=input, tell=print):
    def check(value):
        if value.lower() not in ('yes', 'no'):
            raise ValueError('Enter yes or no.')
    return read(label + ' (yes/no)', check, ask=ask, tell=tell).lower() == 'yes'


def event(label, timezone_name, *, ask=input, tell=print):
    def check(value):
        local_timestamp(value, timezone_name)
    return local_timestamp(read(label + f' (YYYY-MM-DD HH:MM in {timezone_name}, or ISO timestamp with offset)', check, ask=ask, tell=tell), timezone_name)


def local_timestamp(value, timezone_name='UTC'):
    zone = decision_zone(timezone_name)
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if 'T' not in value and ' ' not in value:
            raise ValueError('Time required')
    except ValueError:
        raise DataError('Enter a date and time, for example YYYY-MM-DD HH:MM, optionally with an explicit UTC offset.') from None
    if parsed.tzinfo is not None:
        return parsed.astimezone(zone).isoformat()
    candidates = []
    for fold in (0, 1):
        candidate = parsed.replace(tzinfo=zone, fold=fold)
        restored = candidate.astimezone(timezone.utc).astimezone(zone)
        if restored.replace(tzinfo=None) == parsed:
            candidates.append(candidate)
    if not candidates:
        raise DataError('This local time does not exist during a clock change. Check the source timestamp.')
    if len({c.utcoffset() for c in candidates}) > 1:
        raise DataError('This local time occurs twice during a clock change. Enter the source UTC offset explicitly.')
    return candidates[0].isoformat()


def collect_request(*, ask=input, tell=print, clock=lambda: datetime.now(timezone.utc), catalog_entry=None, product_defaults=None):
    r = lambda label, check=None, **kw: read(label, check, ask=ask, tell=tell, **kw)
    zone_name = r('IANA destination timezone (for example Asia/Kolkata or Europe/London)',
                  lambda v: decision_zone(v))
    zone = decision_zone(zone_name)
    def future_date(value):
        if day(value, 'Delivery date') < clock().astimezone(zone).date():
            raise DataError('Choose today or a future delivery date.')
    product_defaults = product_defaults or {}
    name_default = product_defaults.get('name')
    specification_default = None
    if catalog_entry is not None:
        source = catalog_entry['source_record']
        tell('Catalog reference only. Confirm or edit the proposed name and specifications; English drafts need review.')
        tell('Original description: ' + source['descricaoItem'])
        name_default = catalog_entry.get('english_title') or source['nomePdm']
        specification_default = catalog_entry.get('english_description') or source['descricaoItem']
    name = r('Product name', default=name_default)
    specification = r('Exact specifications (model, material, size, grade, etc.)', default=specification_default)
    brand = r('Required brand, or any', default='any')
    model = r('Required model/part number, or any', default='any')
    brand = None if brand.casefold() == 'any' else brand
    model = None if model.casefold() == 'any' else model
    policy = 'exact'
    if brand is not None or model is not None:
        def check_policy(value):
            if value not in ('exact', 'alternatives'):
                raise ValueError('Enter exact or alternatives.')
        policy = r('Brand/model policy: exact or alternatives (alternatives need buyer review)', check_policy, default='exact')
    unit = r('Purchasing unit (for example each, kg, or a specified pack)')
    initial_quantity = product_defaults.get('quantity')
    quantity = r('Required quantity, without commas', lambda v: amount(v, 'Quantity'),
                 default=format(initial_quantity, 'f').rstrip('0').rstrip('.') if isinstance(initial_quantity, float) else initial_quantity)
    destination = r('Delivery country, city and postal code if applicable')
    delivery_country = r('Two-letter delivery country code (for example IN or GB)', iso_country_code)
    needed = r('Required delivery date (YYYY-MM-DD)', future_date)
    currency = r('Three-letter budget currency (for example INR, USD or EUR)', currency_code)
    budget = r(f'Your internal total budget in {currency}, without commas', lambda v: amount(v, 'Budget'))
    country = r('Required supplier country, or any', default='any')
    if catalog_entry is not None and not yes('Have you checked the specifications, purchasing unit and quantity for this request', ask=ask, tell=tell):
        raise Cancelled()
    details = {'product': {'id': 'product-1', 'name': name, 'specification': specification, 'unit': unit},
            'request': {'product_id': 'product-1', 'unit': unit, 'quantity': quantity,
                        'currency': currency, 'total_budget': budget, 'needed_by': needed,
                        'decision_timezone': zone_name,
                        'delivery_country': delivery_country,
                        'required_brand': brand, 'required_model': model, 'brand_policy': policy,
                        'destination_id': destination, 'supplier_country': None if country.lower() == 'any' else country}}
    if catalog_entry is not None:
        from copy import deepcopy
        details['catalog_reference'] = deepcopy(catalog_entry)
        details['product']['source_classification'] = {'scheme': 'CATMAT', 'code': str(source['codigoItem'])}
    return details


def rfq_text(details):
    p, r = details['product'], details['request']
    classification = p.get('source_classification')
    reference = (f"- Catalog reference: {classification['scheme']} {classification['code']} (reference only; specifications below govern)\n"
                 if classification else '')
    brand_terms = ''
    if r.get('required_brand') or r.get('required_model'):
        brand_terms = (f"- Required brand: {r.get('required_brand') or 'Any'}\n"
                       f"- Required model/part number: {r.get('required_model') or 'Any'}\n"
                       '- Substitution policy: ' + ('Alternatives may be submitted separately for buyer review; not automatically accepted.'
                       if r.get('brand_policy') == 'alternatives' else 'Exact requested brand/model only.') + '\n'
                       '- State the offered brand and model/part number explicitly in your quotation.\n')
    return f'''# Request for quotation — {p['name']}

Hello,

Please provide a written quotation for the following requirement:

- Product: {p['name']}
{reference}- Exact specifications: {p['specification']}
{brand_terms}- Quantity: {r['quantity']}
- Purchasing unit: {r['unit']}
- Delivery location: {r['destination_id']}
- Required delivery date: {r['needed_by']}
- Destination timezone: {r['decision_timezone']}

Please include your supplier/company name, quotation number and revision, issue date/time,
validity expiry date/time in the destination timezone, exact offered product/specifications, quantity and
purchasing unit, and committed delivery date to this location.

Please quote in {r['currency']}. Show the goods amount, applicable taxes, freight and other charges,
and the final total payable. State whether the total includes all applicable costs.
Please also state payment terms, warranty, delivery conditions, exclusions and any
differences from the requested specifications. Do not substitute a product without
identifying the differences.

This is a quotation request, not a purchase order or commitment to buy.

Thank you.
'''


def collect_bundle(details, *, ask=input, tell=print, clock=lambda: datetime.now(timezone.utc)):
    r = lambda label, check=None, **kw: read(label, check, ask=ask, tell=tell, **kw)
    y = lambda label: yes(label, ask=ask, tell=tell)
    e = lambda label: event(label, bundle['request']['decision_timezone'], ask=ask, tell=tell)
    if not y('Are the requirement and quotations genuine, and are you authorized to use them'):
        raise Cancelled()
    reviewer = r('Reviewer name or internal ID')
    reference = r('Reference to the buyer requirement/specification document')
    sources = [{'id': 'requirement-source', 'data_kind': 'real', 'permission_confirmed': True,
                'reference': reference, 'reviewed_by': reviewer, 'reviewed_at': clock().isoformat()}]
    product = dict(details['product'], source_id='requirement-source', source_record_id='requirement-product-1')
    bundle = {'schema_version': '1.0', 'sources': sources, 'products': [product],
              'suppliers': [], 'quotes': [], 'request': dict(details['request'])}
    while True:
        number = len(bundle['quotes']) + 1
        tell(f'\nQuotation {number}. Copy values from the actual document; do not guess missing terms.')
        reference = r('Quotation document reference (filename or internal record reference)')
        supplier_id = r('Stable supplier ID (reuse the same ID for the same supplier)')
        supplier = next((s for s in bundle['suppliers'] if s['id'] == supplier_id), None)
        new_supplier = supplier is None
        if new_supplier:
            supplier = {'id': supplier_id, 'name': r('Supplier company name'), 'country': r('Supplier country')}
        else:
            tell(f"Using supplier: {supplier['name']}")
        quote = {'id': f'quote-{number}', 'supplier_id': supplier_id, 'product_id': product['id'],
                 'source_id': f'quote-source-{number}', 'source_record_id': r('Supplier quotation number and revision')}
        quote['description_raw'] = r('Exact offered product description from quotation')
        if bundle['request'].get('required_brand') or bundle['request'].get('required_model'):
            for key, label in [('offered_brand', 'Offered brand'), ('offered_model', 'Offered model/part number')]:
                value = r(label + ' as written in quotation, or unknown')
                quote[key] = None if value.casefold() == 'unknown' else value
        quote['quantity'] = r('Quoted quantity', lambda v: amount(v, 'Quantity'))
        quote['unit'] = r('Quoted purchasing unit')
        quote['currency'] = r(f"Quoted currency code (requested {bundle['request']['currency']})", currency_code)
        quote['total_amount'] = r('Quoted total payable, without commas', lambda v: amount(v, 'Total'))
        goods = r('Goods-only amount, or unknown', lambda v: None if v == 'unknown' else amount(v, 'Goods', zero=True))
        quote['goods_amount'] = None if goods == 'unknown' else goods
        same_destination = y('Does the quote explicitly cover the requested delivery location')
        quote['destination_id'] = bundle['request']['destination_id'] if same_destination else '__destination_not_confirmed__'
        quote['issued_at'] = e('Quotation issue time')
        quote['received_at'] = e('Time you received the quotation')
        quote['valid_until'] = e('Quotation expiry time')
        quote['promised_delivery_date'] = r('Promised delivery date (YYYY-MM-DD)', lambda v: day(v, 'Delivery date'))
        quote['specification_confirmed'] = y('Have you checked that every requested specification matches')
        quote['all_costs_included'] = y('Does the documented total include all applicable tax, freight and duties')
        quote['terms_reference'] = r('Reference to payment, warranty and delivery terms')
        quote['reviewed_by'] = reviewer
        quote['reviewed_at'] = clock().isoformat()
        source = {'id': quote['source_id'], 'data_kind': 'real', 'source_type': 'genuine_quotation', 'permission_confirmed': True,
                  'reference': reference, 'reviewed_by': reviewer, 'reviewed_at': quote['reviewed_at']}
        candidate = dict(bundle, sources=bundle['sources'] + [source], quotes=bundle['quotes'] + [quote],
                         suppliers=bundle['suppliers'] + [dict(supplier, source_id=source['id'], source_record_id=supplier_id)] if new_supplier else list(bundle['suppliers']))
        try:
            report = evaluate(candidate, clock())
        except DataError as error:
            tell(f'Cannot accept this entry: {error}')
            if y('Re-enter this quotation'):
                continue
            raise Cancelled()
        bundle = candidate
        result = report['quotes'][-1]
        prefix = 'ALTERNATIVE - BUYER REVIEW REQUIRED: ' if result['brand_review']['status'] == 'alternative_pending_review' else 'Excluded: '
        tell('Eligible for cost comparison.' if result['eligible'] else prefix + '; '.join(result['reasons']))
        if not y('Add another quotation'):
            return bundle


def schema_review(bundle, now):
    """Report every mapping failure explicitly; never replace the cost engine."""
    results = []
    for quote in bundle['quotes']:
        try:
            records = map_bundle(dict(bundle, quotes=[quote]),
                                 delivery_country=bundle['request'].get('delivery_country'), as_of=now)
            results.append({'quote_id': quote['id'], 'status': 'mapped', 'record': asdict(records[0]),
                            'brand_review': brand_review(bundle['request'], quote)})
        except (ValueError, KeyError, TypeError, StopIteration) as error:
            results.append({'quote_id': quote['id'], 'status': 'rejected', 'reason': str(error) or 'Missing source'})
    return results


def save_session(folder, *, details=None, bundle=None, clock=lambda: datetime.now(timezone.utc)):
    # Each save gets a new directory; no prior evidence is overwritten.
    now = clock()
    session = folder / (now.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8])
    report = evaluate(bundle, now) if bundle is not None else None
    if report is not None:
        report['schema_mapping'] = schema_review(bundle, now)
    session.mkdir(parents=True, exist_ok=False)
    if bundle is None:
        (session / 'supplier_request.md').write_text(rfq_text(details), encoding='utf-8')
        (session / 'requirement.json').write_text(json.dumps(details, indent=2), encoding='utf-8')
    else:
        raw = json.dumps(bundle, indent=2, ensure_ascii=False).encode('utf-8')
        (session / 'input.json').write_bytes(raw)
        report['input_sha256'] = hashlib.sha256(raw).hexdigest()
        report['engine_sha256'] = hashlib.sha256(Path(__file__).with_name('real_procurement.py').read_bytes()).hexdigest()
        report['intake_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (session / 'review.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
        lines = ['QUOTATION REVIEW — HUMAN DECISION REQUIRED', report['decision_at'],
                 f"Destination timezone: {report['decision_timezone']}", report['ranking_basis'], '']
        names = {s['id']: s['name'] for s in bundle['suppliers']}
        for row in report['quotes']:
            status = f"Cost rank {row['cost_rank']}" if row['eligible'] else 'EXCLUDED: ' + '; '.join(row['reasons'])
            lines.append(f"{row['quote_id']} | {names[row['supplier_id']]} | {row['currency']} {row['quoted_total']} | {status}")
            brand = row['brand_review']
            if brand['status'] != 'not_requested':
                lines.append(f"  Brand/model: {brand['status']} | Required: {brand['required_brand']} / {brand['required_model']} | Offered: {brand['offered_brand']} / {brand['offered_model']}")
        lines.extend(['', report['risk_status'], 'No purchase has been authorized.'])
        lines.append('Schema audit is separate from cost eligibility:')
        for mapped in report['schema_mapping']:
            lines.append(f"{mapped['quote_id']}: {mapped['status']}" + (': ' + mapped['reason'] if mapped['status'] == 'rejected' else ''))
            if mapped['status'] == 'mapped':
                for issue in mapped['record']['review']['unresolved']:
                    lines.append(f"  Unresolved {issue['field']}: {issue['reason']}")
        (session / 'comparison.txt').write_text('\n'.join(lines), encoding='utf-8')
    return session


def main():
    print('MULTI-COUNTRY PROCUREMENT PILOT — type cancel at any question to stop.')
    print('1 Prepare a supplier quotation request\n2 Enter genuine quotations and compare')
    try:
        choice = read('Choose 1 or 2', menu_choice)
        details = collect_request()
        bundle = collect_bundle(details) if choice == '2' else None
        if choice == '1':
            print('\n' + rfq_text(details))
        if not yes('Save these records locally'):
            raise Cancelled()
        root = Path(__file__).resolve().parent
        if root.name == 'ml':
            root = root.parent
        session = save_session(root / 'real-pilot' / 'sessions', details=details, bundle=bundle)
        print(f'Saved in: {session}')
        print('Nothing has been sent to suppliers. No purchase has been authorized.')
        return 0
    except (Cancelled, EOFError, KeyboardInterrupt):
        print('\nCancelled. No session saved.')
        return 0
    except (OSError, DataError) as error:
        print(f'Could not finish saving: {error}. Check for a partial session folder before retrying.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
