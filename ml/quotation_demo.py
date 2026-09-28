"""Run an explicitly fictional quotation comparison without supplier documents."""
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import json
from pathlib import Path
import tempfile

from real_procurement import DataError, amount, day, evaluate


def build_demo(now):
    """Dates are relative to the decision so the example remains repeatable."""
    now = now.astimezone(timezone.utc)
    stamp = lambda days: (now + timedelta(days=days)).isoformat()
    date = lambda days: (now + timedelta(days=days)).date().isoformat()
    source = {'id': 'demo', 'data_kind': 'synthetic', 'source_type': 'synthetic',
              'reference': 'Generated fictional demonstration; no supplier document',
              'reviewed_by': 'demo generator', 'reviewed_at': stamp(-1)}
    product = {'id': 'chair', 'source_id': 'demo', 'source_record_id': 'product',
               'name': 'Office chair', 'specification': 'Adjustable height, fabric seat, five-star base',
               'unit': 'each'}
    suppliers, quotes = [], []
    for index, (total, delivery, expiry, complete) in enumerate([
            ('10000.00', 5, 3, True), ('9000.00', 4, -1, True),
            ('9500.00', 6, 3, False)], 1):
        supplier_id = f'demo-{index}'
        suppliers.append({'id': supplier_id, 'source_id': 'demo',
                          'source_record_id': supplier_id,
                          'name': f'Fictional Supplier {index}', 'country': 'India'})
        quotes.append({'id': f'quote-{index}', 'supplier_id': supplier_id,
                       'source_id': 'demo', 'source_record_id': f'quote-{index}',
                       'product_id': 'chair', 'currency': 'INR', 'unit': 'each',
                       'quantity': '10', 'total_amount': total, 'destination_id': 'Demo office',
                       'issued_at': stamp(-3), 'received_at': stamp(-2),
                       'reviewed_at': stamp(-1), 'reviewed_by': 'demo generator',
                       'valid_until': stamp(expiry), 'promised_delivery_date': date(delivery),
                       'specification_confirmed': True, 'all_costs_included': complete,
                       'terms_reference': 'Fictional terms for teaching only'})
    return {'schema_version': '1.0', 'sources': [source], 'products': [product],
            'suppliers': suppliers, 'quotes': quotes,
            'request': {'product_id': 'chair', 'currency': 'INR', 'unit': 'each',
                        'quantity': '10', 'total_budget': '12000', 'needed_by': date(7),
                        'destination_id': 'Demo office', 'supplier_country': None,
                        'decision_timezone': 'Asia/Kolkata'}}


def show_report(bundle, report):
    print('\nSYNTHETIC QUOTATION DEMONSTRATION')
    print('All suppliers, prices and quotations below are fictional.\n')
    print('Request: 10 office chairs | Total budget: INR', bundle['request']['total_budget'])
    print('Specifications:', bundle['products'][0]['specification'])
    print('Required delivery:', bundle['request']['needed_by'])
    print('Destination: Demo office | Timezone: Asia/Kolkata\n')
    for supplier, quote, result in zip(bundle['suppliers'], bundle['quotes'], report['quotes']):
        print(supplier['name'])
        print(f"  Quoted total: INR {quote['total_amount']}")
        print(f"  Delivery: {quote['promised_delivery_date']} | Valid until: {quote['valid_until']}")
        print('  All costs confirmed:', 'Yes' if quote['all_costs_included'] else 'No; final payable total unconfirmed')
        if result['eligible']:
            print(f"  ELIGIBLE | Cost rank: {result['cost_rank']}")
        else:
            print('  EXCLUDED | ' + '; '.join(result['reasons']))
        print()
    print('Eligible quotations:', report['eligible_quotes'])
    print('The cheapest listed offer is expired; the next cheapest has unconfirmed costs.')
    print('Only eligible quotations receive a cost rank. Delivery risk is unavailable.')
    print('DEMO ONLY: no purchase authorized and no genuine session saved.')


def simulate(original, now, field, value):
    """Change one request field against the original, never alter supplier offers."""
    if field == 'total_budget':
        amount(value, 'Total budget')
    elif field == 'needed_by':
        day(value, 'Delivery deadline')
    else:
        raise DataError('Unsupported scenario field')
    scenario = deepcopy(original)
    scenario['request'][field] = value
    return scenario, evaluate(scenario, now, demo=True)


def save_demo(original, baseline, scenarios, output_root):
    """Keep fictional reports in their own directory, with unique exports."""
    lines = ['SYNTHETIC QUOTATION DEMONSTRATION',
             'All suppliers and quotations are fictional. No purchase authorized.',
             'Delivery risk is unavailable. Cost ranks apply only to eligible offers.',
             'Decision time: ' + baseline['decision_at'],
             'Each scenario changes one field from the original; changes do not accumulate.', '']
    names = {s['id']: s['name'] for s in original['suppliers']}
    for title, bundle, report in [('ORIGINAL', original, baseline)] + [
            (f"WHAT-IF {i}: {s['field']} = {s['value']}", s['bundle'], s['report'])
            for i, s in enumerate(scenarios, 1)]:
        lines.extend([title, 'Request: ' + json.dumps(bundle['request']),
                      f"Eligible quotations: {report['eligible_quotes']}"])
        for row, quote, before in zip(report['quotes'], bundle['quotes'], baseline['quotes']):
            lines.append(f"{names[row['supplier_id']]} | {row['currency']} {row['quoted_total']} | "
                         f"Delivery: {quote['promised_delivery_date']} | Valid until: {quote['valid_until']}")
            lines.append(f"  Original rank: {before['cost_rank'] or 'N/A'} | "
                         f"Scenario rank: {row['cost_rank'] or 'N/A'} | "
                         + ('ELIGIBLE' if row['eligible'] else 'EXCLUDED: ' + '; '.join(row['reasons'])))
        lines.append('')
    payload = {'data_kind': 'synthetic', 'purchase_authorized': False,
               'original': original, 'baseline': baseline, 'scenarios': scenarios}
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix='synthetic-demo-', dir=output_root))
    try:
        (folder / 'comparison.txt').write_text('\n'.join(lines), encoding='utf-8')
        (folder / 'evidence.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    except OSError as error:
        raise OSError(f'Export incomplete in {folder}: {error}') from error
    return folder


def main(*, ask=input, output_root=None):
    now = datetime.now(timezone.utc)
    original = build_demo(now)
    baseline = evaluate(original, now, demo=True)
    scenarios = []
    if output_root is None:
        output_root = Path(__file__).resolve().parent / 'demo-reports'
    show_report(original, baseline)
    print('\nEach change starts from the original request; changes do not accumulate.')
    print('Quotation details and the decision time stay fixed during this demo.')
    while True:
        print('\n1 Change total budget\n2 Change delivery deadline\n3 Show original\n4 Exit\n5 Save demo report')
        try:
            choice = ask('Choose: ').strip()
            if choice.casefold() in ('4', 'exit', 'cancel'):
                break
            if choice == '3':
                show_report(original, baseline)
                continue
            if choice == '5':
                folder = save_demo(original, baseline, scenarios, output_root)
                print(f'Demo report saved: {folder / "comparison.txt"}')
                print('Supporting fictional inputs and results saved as evidence.json.')
                continue
            if choice not in ('1', '2'):
                print('Please choose 1, 2, 3, 4 or 5.')
                continue
            field = 'total_budget' if choice == '1' else 'needed_by'
            prompt = 'Total budget in INR (no commas): ' if choice == '1' else 'Delivery deadline (YYYY-MM-DD): '
            value = ask(prompt).strip()
            if value.casefold() == 'cancel':
                continue
            scenario, result = simulate(original, now, field, value)
            scenarios.append({'field': field, 'value': value, 'bundle': scenario, 'report': result})
            print('\nORIGINAL vs WHAT-IF — SYNTHETIC DEMO')
            print(f"{field}: {original['request'][field]} -> {value}")
            for supplier, before, after in zip(original['suppliers'], baseline['quotes'], result['quotes']):
                old = f"Eligible, rank {before['cost_rank']}" if before['eligible'] else 'Excluded'
                new = f"Eligible, rank {after['cost_rank']}" if after['eligible'] else 'Excluded'
                print(f"{supplier['name']}: {old} -> {new}")
                if after['reasons']:
                    print('  What-if reasons: ' + '; '.join(after['reasons']))
            print(f"Eligible quotations: {baseline['eligible_quotes']} -> {result['eligible_quotes']}")
            if not result['eligible_quotes']:
                print('No quotation meets this scenario. No supplier is recommended.')
        except DataError as error:
            print(f'Please correct the input: {error}')
        except OSError as error:
            print(f'Could not save the demo report: {error}')
        except (EOFError, KeyboardInterrupt):
            break
    print('\nDemo closed. No genuine session saved.')


if __name__ == '__main__':
    main()
