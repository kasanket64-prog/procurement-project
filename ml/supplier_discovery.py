"""Build an offline supplier discovery page from attributed public award records."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import webbrowser


def notice_url(value):
    parsed = urlparse(value)
    return value if parsed.scheme == 'https' and parsed.hostname == 'www.contractsfinder.service.gov.uk' else None


def prepare(records, manifest):
    # Only latest captured release per process; not a claim of the latest live notice.
    latest = {}
    for record in records:
        key = record['process_id']
        if key not in latest or record['published_at'] > latest[key]['published_at']:
            latest[key] = record
    suppliers = {}
    for record in latest.values():
        for award in record['awards']:
            if award.get('status') != 'active':
                continue
            for index, supplier in enumerate(award['suppliers']):
                if not supplier.get('name'):
                    continue
                # Never merge two companies on name alone.
                identity = supplier.get('id') or f"unlinked:{record['id']}:{award['award_id']}:{index}"
                entry = suppliers.setdefault(identity, {'id': identity, 'name': supplier['name'], 'evidence': []})
                links = [notice_url(u) for u in record['source_notice_urls']]
                entry['evidence'].append({
                    'title': record['title'], 'description': record['description'],
                    'published_at': record['published_at'], 'award_date': award.get('award_date'),
                    'classification': record.get('classification'), 'category': record.get('procurement_category'),
                    'buyer': (record.get('buyer') or {}).get('name'),
                    'notice_urls': list(dict.fromkeys(u for u in links if u)),
                    'release_id': record['release_id'], 'award_id': award['award_id'],
                })
    return {'source': manifest['source'], 'retrieved_at': manifest['retrieved_at_utc'],
            'license': manifest['declared_license'], 'sampling': manifest['sampling'],
            'raw_sha256': manifest['sha256'], 'processes': len(latest),
            'suppliers': sorted(suppliers.values(), key=lambda s: (s['name'].casefold(), s['id']))}


def build_page(data, template):
    # JSON is data only. Escape HTML-sensitive characters even inside script blocks.
    encoded = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return template.replace('__SUPPLIER_DATA__', encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    data = json.loads((root / 'public_supplier_leads.json').read_text(encoding='utf-8'))
    page = build_page(data, (root / 'supplier_discovery_template.html').read_text(encoding='utf-8'))
    destination = root / 'supplier_discovery.html'
    destination.write_text(page, encoding='utf-8')
    print(f"Public supplier discovery: {len(data['suppliers'])} historical supplier identities")
    print(destination)
    if not args.no_open:
        webbrowser.open(destination.as_uri())


if __name__ == '__main__':
    main()
