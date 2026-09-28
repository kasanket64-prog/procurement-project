"""Launch the unified offline procurement interface; no server or account required."""
import argparse
import csv
import json
from pathlib import Path
import webbrowser


def build(root, destination):
    root = Path(root)
    ml = root / 'ml'
    with (root / 'dataset/supplier_items.csv').open(encoding='utf-8-sig', newline='') as stream:
        demo = list(csv.DictReader(stream))
    data = {'demo': demo,
            'public': json.loads((ml / 'public_supplier_leads.json').read_text(encoding='utf-8')),
            'catalog': json.loads((ml / 'catmat_research_catalog.json').read_text(encoding='utf-8'))['records']}
    encoded = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = Path(__file__).with_name('procurement_platform_template.html').read_text(encoding='utf-8')
    Path(destination).write_text(template.replace('__DATA__', encoded), encoding='utf-8')
    return Path(destination).resolve()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    page = build(args.root, Path(__file__).with_name('procurement_platform.html'))
    print('Procurement platform:', page)
    if not args.no_open:
        webbrowser.open(page.as_uri())


if __name__ == '__main__':
    main()
