"""One entry point for demo recommendations, public leads and request drafts."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
import pandas as pd


def terms(value):
    value = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold()) if not unicodedata.combining(c))
    return set(re.findall(r'[a-z0-9]+', value))


def public_matches(data, query):
    wanted = terms(query)
    if not wanted:
        return []
    result = []
    for supplier in data['suppliers']:
        evidence = []
        for award in supplier['evidence']:
            searchable = terms(' '.join([supplier['name'], award.get('title') or '',
                                         award.get('description') or '', json.dumps(award.get('classification'))]))
            if wanted <= searchable:
                evidence.append(award)
        if evidence:
            result.append(dict(supplier, evidence=evidence))
    return result


def rank_demo(frame, product, country=None, budget=None, quantity=None):
    """Original matcher's weighting; historical quantities are observations only."""
    matches = frame.loc[frame['item'] == product].copy()
    if country:
        matches = matches.loc[matches['supplier_country'].str.casefold() == country.casefold()].copy()
    if budget is not None:
        if budget <= 0:
            raise ValueError('Budget must be positive')
        matches = matches.loc[matches['avg_unit_price'] <= budget].copy()
    if matches.empty:
        return matches
    max_orders = matches['historical_orders'].max()
    experience = matches['historical_orders'] / max_orders * 100 if max_orders > 0 else 0
    prices = ((budget - matches['avg_unit_price']) / budget * 100).clip(0, 100) if budget else matches['avg_unit_price'].min() / matches['avg_unit_price'] * 100
    matches['match_score'] = matches['on_time_rate'] * .4 + (100 - matches['rejection_rate']) * .3 + experience * .2 + prices * .1
    matches['quantity_note'] = matches['max_historical_quantity'].apply(
        lambda maximum: 'Not requested' if quantity is None else
        ('Within observed order size' if quantity <= maximum else 'Above largest observed order; capacity unknown'))
    return matches.sort_values(['match_score', 'supplier_id'], ascending=[False, True])


def optional_number(label, ask):
    from real_procurement import amount, DataError
    while True:
        value = ask(label).strip()
        if not value:
            return None
        if value.casefold() == 'cancel':
            raise KeyboardInterrupt
        try:
            return float(amount(value, label))
        except DataError as error:
            print(error)


def show_results(demo, leads, product, query, data):
    print('\nA. REAL PUBLIC SUPPLIER LEADS — current availability unconfirmed')
    print(f"Source: {data['source']} | Captured: {data['retrieved_at'][:10]}")
    print('Search:', query, '| Matching historical supplier identities:', len(leads))
    print('Country, budget, quantity and delivery capability are NOT verified for these leads.')
    for index, supplier in enumerate(leads[:10], 1):
        print(f"\nL{index}. {supplier['name']}")
        for evidence in supplier['evidence'][:2]:
            print('  Award:', evidence['title'])
            print('  Award date:', evidence.get('award_date'))
            for url in evidence['notice_urls']:
                print('  Official source:', url)
    if len(leads) > 10:
        print('Showing first 10 leads alphabetically; export includes all matches.')
    if not leads:
        print('No lead in this limited UK award sample. This does not mean no real suppliers exist.')
    print('\nB. SYNTHETIC DEMO RECOMMENDATIONS — fictional suppliers and performance')
    if product is None:
        print('This product is not in the demo catalog. Public leads remain searchable.')
        return
    print('Selected demo product:', product, '| Eligible demo records:', len(demo))
    print('Demo price figures have no verified currency. Do not interpret them as INR or live quotes.')
    print('Weights: delivery 40%, quality 30%, experience 20%, price 10%. Scores are not probabilities.')
    for index, (_, row) in enumerate(demo.head(10).iterrows(), 1):
        print(f"\nD{index}. {row['supplier_name']} | {row['supplier_country']} | Score {row['match_score']:.2f}%")
        print(f"  Historical average unit price: {row['avg_unit_price']} | On-time: {row['on_time_rate']}% | Rejection: {row['rejection_rate']}%")
        print(f"  Experience: {row['historical_orders']} orders | Largest observed order: {row['max_historical_quantity']}")
        print('  Quantity:', row['quantity_note'])
    print('Historical order size is not supplier capacity. No live delivery-risk estimate is provided here.')


def show_catalog(hits):
    print('\nC. REAL PUBLIC CATALOG — product descriptions, not supplier offers')
    print('Keyword matches only. Five entries have English drafts; independent translation review is pending.')
    print('Country, price, stock and brand availability are not established by catalog matches.')
    if not hits:
        print('No matching entry in the 40-record CATMAT sample.')
    for index, (score, code, record) in enumerate(hits, 1):
        source = record['source_record']
        print(f"\nC{index}. CATMAT {code} | {record.get('english_title') or source['nomePdm']}")
        print(f'  Query words matched: {score:.0%} (not specification confidence)')
        print('  Original:', source['descricaoItem'])
        if record.get('english_description'):
            print('  English draft:', record['english_description'])
        print('  Source evidence:', ', '.join(record['evidence_files']))
    print('Local research catalog; dataset-specific reuse terms remain unverified.')


def draft_request(product, quantity, root, ask, catalog_entry=None):
    from real_intake import collect_request, rfq_text, save_session, yes, Cancelled
    try:
        print('\nPrepare a request for any supplier. No company is assumed to stock this product.')
        details = collect_request(ask=ask, product_defaults={'name': product, 'quantity': quantity}, catalog_entry=catalog_entry)
        print(rfq_text(details))
        if yes('Save this request draft locally', ask=ask):
            folder = save_session(root / 'supplier-request-drafts', details=details)
            print('Saved:', folder / 'supplier_request.md')
            print('Nothing sent. No purchase authorized.')
    except Cancelled:
        print('Request cancelled. Returning to your results.')
    except OSError as error:
        print('Could not save; check for partial files:', error)


def main(*, ask=input, root=None):
    root = Path(root) if root else Path(__file__).resolve().parent.parent
    frame = pd.read_csv(root / 'dataset/supplier_items.csv')
    data = json.loads((root / 'ml/public_supplier_leads.json').read_text(encoding='utf-8'))
    from catalog_search import search as catalog_search
    catalog = json.loads((root / 'ml/catmat_research_catalog.json').read_text(encoding='utf-8'))['records']
    catalog_codes = {str(r['source_record']['codigoItem']) for r in catalog}
    products = sorted(frame['item'].dropna().unique().tolist())
    print('\nPROCUREMENT PLATFORM — FIND SUPPLIERS')
    print('One search: real historical supplier leads, synthetic demo recommendations and real CATMAT product descriptions.')
    print('Search beyond the demo list too: try washer, microscope, or CATMAT code 275035.')
    print('Type cancel at an input to exit. For advanced semantic matching and what-if, choose 5 after a search.')
    while True:
        print('\nAVAILABLE DEMO PRODUCTS (you may also type a different product)')
        for number, name in enumerate(products, 1):
            print(f'{number:2}. {name}')
        query = ask('\nProduct name, keywords or list number: ').strip()
        if query.casefold() in ('cancel', 'exit'):
            return
        if not terms(query):
            print('Enter a product before searching.')
            continue
        product = None
        if query.isdigit() and query not in catalog_codes:
            if not 1 <= int(query) <= len(products):
                print('Choose a listed number.')
                continue
            product = products[int(query) - 1]
            query = product.split('(')[0].strip()
        else:
            choices = [p for p in products if terms(query) <= terms(p)]
            if len(choices) == 1:
                product = choices[0]
            elif len(choices) > 1:
                print('Several demo products match. Enter the exact product or its list number.')
                continue
        country = ask('Supplier country for demo filtering (Enter for any): ').strip()
        if country.casefold() == 'cancel':
            return
        budget = optional_number('Maximum DEMO unit-price figure (Enter to skip; currency unverified): ', ask)
        quantity = optional_number('Required quantity (Enter to skip): ', ask)
        demo = rank_demo(frame, product, country, budget, quantity)
        leads = public_matches(data, query)
        show_results(demo, leads, product, query, data)
        catalog_hits = catalog_search(catalog, query)
        show_catalog(catalog_hits)
        while True:
            choice = ask('\n1 Prepare quotation request  2 New search  3 Export public leads  4 Exit  5 Advanced AI demo  6 Request a catalog item\nChoose: ').strip()
            if choice == '1':
                draft_request(product or query, quantity, root, ask)
            elif choice == '2':
                break
            elif choice in ('4', 'cancel', 'exit'):
                return
            elif choice == '3':
                if not leads:
                    print('No matching public leads to export.')
                    continue
                import uuid
                folder = root / 'supplier-shortlists'
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                    path = folder / (uuid.uuid4().hex + '.json')
                    with path.open('x', encoding='utf-8') as stream:
                        json.dump({'query': query, 'created_at': datetime.now(timezone.utc).isoformat(),
                                   'source': data['source'], 'retrieved_at': data['retrieved_at'], 'license': data['license'],
                                   'availability': 'Unconfirmed', 'record_kind': 'Historical public leads, not quotations',
                                   'suppliers': leads}, stream, indent=2)
                    print('Saved public leads:', path)
                except OSError as error:
                    print('Export failed:', error)
            elif choice == '5':
                import subprocess, sys
                print('Opening the existing advanced synthetic demo; it will ask you to confirm its own requirements.')
                subprocess.run([sys.executable, str(root / 'ml/procurement_ai.py')], cwd=root, check=False)
            elif choice == '6':
                if not catalog_hits:
                    print('No catalog result selected. Run a new search or use option 1 for a custom request.')
                    continue
                selected = ask('Catalog result number (for C1 enter 1), or cancel: ').strip()
                if selected.casefold() == 'cancel':
                    continue
                if not selected.isdigit() or not 1 <= int(selected) <= len(catalog_hits):
                    print('Choose one of the displayed catalog result numbers.')
                    continue
                record = catalog_hits[int(selected)-1][2]
                draft_request(product or query, quantity, root, ask, catalog_entry=record)
            else:
                print('Choose 1, 2, 3, 4, 5 or 6.')


if __name__ == '__main__':
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print('\nSession ended.')
