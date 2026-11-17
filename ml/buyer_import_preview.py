"""Read-only fixed-schema preview; never imports, repairs or accepts buyer records."""
import argparse
import csv
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import sys

from buyer_snapshot_check import TEMPLATES, load_pilot_setup
from buyer_readiness import readiness, render_html
from real_procurement import DataError


def preview(folder, as_of):
    report = readiness(folder, as_of)
    report['source_preview'] = []
    try:
        load_pilot_setup(folder, as_of)
    except DataError:
        return report
    for name in ('order_snapshots', 'receipt_events', 'outcome_reviews', 'decision_signals'):
        with (TEMPLATES / f'{name}.csv').open(encoding='utf-8-sig', newline='') as stream:
            expected = next(csv.reader(stream))
        item = dict(file=f'{name}.csv', expected_columns=expected, status='blocked')
        try:
            with (Path(folder) / f'{name}.csv').open(encoding='utf-8-sig', newline='') as stream:
                actual = next(csv.reader(stream), [])
            item.update(missing_columns=[key for key in expected if key not in actual],
                        unexpected_column_count=sum(key not in expected for key in actual),
                        duplicate_column_count=len(actual) - len(set(actual)),
                        exact_order=actual == expected)
            if actual == expected:
                item['status'] = 'passed'
            else:
                item['reason'] = 'Headers must match the current blank template exactly; no mapping is inferred.'
        except (OSError, UnicodeError, csv.Error):
            item['reason'] = 'Cannot read a UTF-8 CSV header.'
        report['source_preview'].append(item)
    if any(item['status'] == 'blocked' for item in report['source_preview']):
        report['status'] = 'blocked'
    return report


def render_preview(report):
    cards = []
    for item in report['source_preview']:
        columns = ''.join(f'<li><code>{escape(key)}</code> → <code>{escape(key)}</code></li>'
                          for key in item['expected_columns'])
        detail = escape(item.get('reason', 'Header names and order match; row validation is shown below.'))
        if 'missing_columns' in item:
            detail += (' Missing: ' + escape(', '.join(item['missing_columns']) or 'none') +
                       f". Unexpected: {item['unexpected_column_count']}; duplicates: {item['duplicate_column_count']}; " +
                       f"exact order: {item['exact_order']}.")
        cards.append(f'<section><h2>{escape(item["file"])}</h2><p class="{item["status"]}">'
                     f'{item["status"].upper()}</p><p>{detail}</p><details><summary>Required source → schema columns'
                     f'</summary><ul>{columns}</ul></details></section>')
    content = ('<section><h2>Fixed-schema source preview</h2><p>Read-only; no batch is accepted or imported. '
               'Only exact existing column mappings are supported. Header matches do not validate rows or units. '
               'Declared permission is checked, not authenticated; source freshness is unverified. '
               'Any validation error blocks the batch; there is no row-level quarantine or partial admission. '
               'Promise events are not consumed by this pipeline.</p></section>' + ''.join(cards))
    if not cards:
        content += '<section><p>Source preview skipped: resolve declared permission or setup first.</p></section>'
    return render_html(report).replace('<title>Buyer data readiness</title>', '<title>Buyer import preview</title>').replace(
        '<h1>Buyer data readiness</h1>', '<h1>Buyer import preview</h1>').replace(
        '<div class="grid">', content + '<div class="grid">')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', help='Approved external pilot folder; source files remain unchanged')
    parser.add_argument('--format', choices=('html', 'json'), default='html')
    args = parser.parse_args()
    report = preview(args.folder, datetime.now(timezone.utc))
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(render_preview(report) if args.format == 'html' else json.dumps(report, indent=2))
    return 2 if report['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
