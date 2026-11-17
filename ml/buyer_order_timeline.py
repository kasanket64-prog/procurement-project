"""Private, read-only order evidence timeline; no label acceptance or purchase authority."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
import sys

from buyer_delay_labels import label_delays, load_pilot_evidence
from real_procurement import DataError, timestamp


def timeline(snapshots, receipts, reviews, signals, setup, policy, as_of, order_line_id):
    # Validate the same loaded rows that will be displayed, including historical lineage.
    labels = label_delays(snapshots, receipts, reviews, signals, setup, policy, as_of)
    if not any(row['order_line_id'] == order_line_id for row in labels['lines']):
        raise DataError('order_line_id: no validated matching line')
    events = []
    tables = [
        ('snapshot', snapshots, 'snapshot_id', 'order_placed_at',
         ('quantity', 'unit', 'original_promise_date', 'snapshot_status')),
        ('receipt', receipts, 'receipt_event_id', 'event_at', ('quantity', 'unit')),
        ('signal', signals, 'signal_id', 'event_at', ('verification',)),
        ('review', reviews, 'review_id', 'reviewed_at', ('delivery_status', 'label', 'coverage_confirmed')),
    ]
    for kind, rows, identity, event_clock, fields in tables:
        replaced = {row['supersedes_id'] for row in rows if row.get('supersedes_id')}
        for row in rows:
            if row['order_line_id'] != order_line_id:
                continue
            event_kind = kind
            if kind == 'receipt': event_kind += ':' + row['event_type']
            if kind == 'signal': event_kind += ':' + row['signal_type']
            events.append(dict(kind=event_kind, record_id=row[identity],
                               event_at=row[event_clock], known_at=row['known_at'], captured_at=row['captured_at'],
                               source_ref=row['source_ref'], supersedes_id=row.get('supersedes_id', ''),
                               reverses_event_id=row.get('reverses_event_id', ''),
                               superseded=row[identity] in replaced,
                               details={key: row[key] for key in fields}))
    events.sort(key=lambda row: (timestamp(row['event_at'], 'event_at'), timestamp(row['known_at'], 'known_at'),
                                timestamp(row['captured_at'], 'captured_at'), row['kind'], row['record_id']))
    return dict(schema_version='1.0', report_kind='order_timeline', status='timeline_available', order_line_id=order_line_id,
                checked_at=as_of.astimezone(timezone.utc).isoformat(), events=events,
                model_ready=False, purchase_authorized=False, human_review_required=True)


def render_timeline(report):
    safe = lambda value: escape(str(value), quote=True)
    cards = []
    for event in report.get('events', []):
        details = dict(event['details'])
        details.update(event_at=event['event_at'], known_at=event['known_at'], captured_at=event['captured_at'],
                       source_ref=event['source_ref'], supersedes_id=event['supersedes_id'] or 'none',
                       reverses_event_id=event['reverses_event_id'] or 'none',
                       version='Superseded — preserved history' if event['superseded'] else 'Not superseded')
        items = ''.join(f'<dt>{safe(key.replace("_", " "))}</dt><dd>{safe(value)}</dd>' for key, value in details.items())
        cards.append(f'<li><article><h2>{safe(event["kind"])} · {safe(event["record_id"])}</h2><dl>{items}</dl></article></li>')
    result = (f'<p>Order line: {safe(report["order_line_id"])}</p><p>Checked at {safe(report["checked_at"])}</p>'
              if report['status'] == 'timeline_available' else f'<p role="alert">Blocked: {safe(report["reason"])}</p>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Order evidence timeline</title><style>
body{{font:16px/1.6 system-ui;background:#f5f7f6;color:#172e36;margin:0}}main{{max-width:960px;margin:auto;padding:24px}}
article,.notice{{background:white;border:1px solid #dce5e4;border-radius:12px;padding:20px;margin:16px 0}}
ol{{padding-left:24px}}h1,h2{{line-height:1.3}}h2{{font-size:1.2rem}}dt{{font-weight:bold}}dd{{margin:0 0 10px}}
p,h2,dd{{overflow-wrap:anywhere}}.notice{{border-left:4px solid #a67b1f}}
</style></head><body><main><h1>Order evidence timeline</h1>
<div class="notice"><strong>Private source review — not ready for training or purchasing.</strong>
<p>Sources and permission are declared, not authenticated. Historical errors and corrections are preserved;
superseded business values are not endorsed. Receipt reversals retain their acceptance link; “not superseded”
does not mean a receipt remains accepted. Review labels are declarations, not accepted training labels.</p>
<p>Sorted by event time, then known/capture time and stable identity; equal-time order does not imply causation.
Snapshot event time is original order placement, including transcription corrections; capture time records the later capture.
Promise-event changes are not supported. No links are followed, records changed or messages sent.
Keep genuine reports in approved private storage outside GitHub.</p></div>{result}<ol>{''.join(cards)}</ol>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', help='Approved external pilot folder')
    parser.add_argument('order_line_id', help='Exact pseudonymous order line key')
    parser.add_argument('--format', choices=('html', 'json'), default='html')
    args = parser.parse_args()
    as_of = datetime.now(timezone.utc)
    try:
        report = timeline(*load_pilot_evidence(args.folder, as_of), as_of, args.order_line_id)
    except DataError as error:
        report = dict(schema_version='1.0', report_kind='order_timeline', status='blocked', reason=str(error), events=[], model_ready=False,
                      purchase_authorized=False, human_review_required=True)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(render_timeline(report) if args.format == 'html' else json.dumps(report, indent=2))
    return 2 if report['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
