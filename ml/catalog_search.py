"""Local CATMAT research search; catalog records are not supplier quotations."""
import json
from pathlib import Path
import re
import unicodedata


def words(value):
    plain = ''.join(c for c in unicodedata.normalize('NFKD', value.casefold())
                    if not unicodedata.combining(c))
    return set(re.findall(r'\w+', plain))


def search(records, query, limit=5):
    tokens = words(query)
    if not tokens:
        return []
    results = []
    for record in records:
        source = record['source_record']
        text = ' '.join(str(source.get(k, '')) for k in (
            'codigoItem', 'nomeGrupo', 'nomeClasse', 'nomePdm', 'descricaoItem'))
        text += ' ' + record.get('english_title', '') + ' ' + record.get('english_description', '')
        matched = tokens & words(text)
        if matched:
            results.append((len(matched) / len(tokens), str(source['codigoItem']), record))
    results.sort(key=lambda row: (-row[0], row[1]))
    return results[:limit]


def prepare_request(record, *, ask=input, output_root=None):
    from real_intake import Cancelled, collect_request, rfq_text, save_session, yes
    try:
        details = collect_request(ask=ask, catalog_entry=record)
        print('\n' + rfq_text(details))
        if not yes('Save this quotation-request draft locally', ask=ask):
            print('Draft not saved. Returning to catalog search.')
            return
        root = Path(output_root) if output_root else Path(__file__).resolve().parent / 'catalog-rfq-drafts'
        session = save_session(root, details=details)
        print(f'Saved draft: {session / "supplier_request.md"}')
        print('Nothing sent. This is a request draft, not a supplier quotation.')
    except (Cancelled, EOFError, KeyboardInterrupt):
        print('Request cancelled. Returning to catalog search.')
    except OSError as error:
        print(f'Could not save draft: {error}. Check the output folder for partial files.')


def main(*, ask=input, data_path=None):
    path = Path(data_path) if data_path else Path(__file__).with_name('catmat_research_catalog.json')
    try:
        records = json.loads(path.read_text(encoding='utf-8'))['records']
    except (OSError, ValueError, KeyError) as error:
        print(f'Could not load the research catalog: {error}')
        return 1
    print('\nCATMAT PUBLIC CATALOG — LOCAL RESEARCH PILOT')
    print(f'{len(records)} unique catalog entries. No supplier offers, prices or delivery-risk predictions.')
    print('Original descriptions: Portuguese. English drafts exist for five entries only.')
    print('Translations need independent review; dataset-specific reuse terms remain unverified.')
    print('Search by code or keywords, e.g. office chair, washer, cadeira, or 206504.')
    print('Results use keyword overlap, not semantic or specification verification.')
    print('To prepare a quotation-request draft, enter rfq followed by an exact item code, e.g. rfq 275035.')
    while True:
        try:
            query = ask('\nSearch (or exit): ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if query.casefold() in ('exit', 'cancel'):
            break
        if query.casefold().startswith('rfq '):
            code = query.split(maxsplit=1)[1].strip()
            record = next((r for r in records if str(r['source_record']['codigoItem']) == code), None)
            if record is None:
                print('That exact CATMAT item code is not in this sample.')
            else:
                prepare_request(record, ask=ask)
            continue
        if not words(query):
            print('Enter a product keyword or CATMAT item code.')
            continue
        hits = search(records, query)
        if not hits:
            print('No keyword match in this small sample. Try Portuguese or a CATMAT code.')
        for score, code, record in hits:
            source = record['source_record']
            print(f"\nCATMAT {code} | {source['nomePdm']} | Query words matched: {score:.0%}")
            print('Original:', source['descricaoItem'])
            if record.get('english_description'):
                print('English draft:', record['english_description'])
                print('Translation:', record['translation_status'])
            print(f"Source classification: group {source['codigoGrupo']} / class {source['codigoClasse']} / PDM {source['codigoPdm']}")
            print('Evidence:', ', '.join(record['evidence_files']))
            print('Purchasing unit and exact specifications require confirmation. Not a quotation.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
