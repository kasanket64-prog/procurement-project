"""Read-only buyer pipeline readiness report; no training or purchase approval."""
import argparse
from datetime import datetime, timezone
from html import escape
import json

from buyer_snapshot_check import check_folder
from buyer_receipts import reconcile_folder
from buyer_delay_labels import label_folder
from real_procurement import DataError


def readiness(folder, as_of):
    stages = []
    blocked = False
    checks = [('snapshots', 'Order snapshots', check_folder),
              ('receipts', 'Receipt reconciliation', reconcile_folder),
              ('labels', 'Delay label proposals', label_folder)]
    for key, title, check in checks:
        if blocked:
            stages.append(dict(key=key, title=title, status='skipped',
                               reason='Resolve the earlier blocked stage, then rerun.'))
            continue
        try:
            result = check(folder, as_of)
        except DataError as error:
            stages.append(dict(key=key, title=title, status='blocked', reason=str(error)))
            blocked = True
            continue
        summary = {}
        for field in ('snapshot_rows', 'active_order_lines', 'correction_rows', 'receipt_events', 'label_counts'):
            if field in result:
                summary[field] = result[field]
        stages.append(dict(key=key, title=title, status='passed', summary=summary))
    return dict(status='blocked' if blocked else 'checks_complete',
                checked_at=as_of.astimezone(timezone.utc).isoformat(), stages=stages,
                model_ready=False, purchase_authorized=False, human_review_required=True,
                next_action=('Correct the reported input or policy issue and rerun all checks.' if blocked else
                             'Review source authenticity, permission scope, receipt coverage and each proposed label. '
                             'Human label acceptance and a reviewed cohort adapter are still required before training.'),
                limitations=['Passed means structural checks passed, not authentic consent or source truth.',
                             'Unknown, pending and cancelled outcomes are not successful deliveries.',
                             'Stages read local files in sequence; do not edit inputs during a run. Rerun after changes.',
                             'This report does not train, rank suppliers, contact anyone or authorise a purchase.'])


def render_html(report):
    def safe(value):
        return escape(str(value), quote=True)

    cards = []
    for stage in report['stages']:
        details = []
        for key, value in stage.get('summary', {}).items():
            if isinstance(value, dict):
                value = ', '.join(f'{name.capitalize()}: {count}' for name, count in value.items())
            details.append(f'<dt>{safe(key.replace("_", " ").capitalize())}</dt><dd>{safe(value)}</dd>')
        reason = f'<p>{safe(stage["reason"])}</p>' if 'reason' in stage else ''
        cards.append(f'<section><h2>{safe(stage["title"])}</h2>'
                     f'<p class="{safe(stage["status"])}">{safe(stage["status"].upper())}</p>'
                     f'{reason}<dl>{"".join(details)}</dl></section>')
    heading = 'Input checks blocked' if report['status'] == 'blocked' else 'Checks passed — human review required'
    limits = ''.join(f'<li>{safe(item)}</li>' for item in report['limitations'])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Buyer data readiness</title><style>
body{{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f5f7f6;color:#172e36}}
main{{max-width:960px;margin:auto;padding:32px 20px}}h1{{line-height:1.2}}h2{{font-size:1.2rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr));gap:16px}}
section,.notice{{background:white;border:1px solid #dce5e4;border-radius:12px;padding:20px;margin:16px 0}}
.notice{{border-left:4px solid #a67b1f;background:#fff9eb}}
.passed,.blocked,.skipped{{display:inline-block;padding:4px 10px;border-radius:5px;font-size:12px;font-weight:bold;letter-spacing:.05em}}
.passed{{color:#116338;background:#e4f2e9}}.blocked{{color:#a12020;background:#fce9e7}}.skipped{{color:#535b65;background:#edf0f2}}
dd{{margin:0 0 10px;overflow-wrap:anywhere}}dt{{font-weight:600}}p,li{{overflow-wrap:anywhere}}
</style></head><body><main>
<p>Buyer pilot · read-only review</p><h1>Buyer data readiness</h1>
<p><strong>{safe(heading)}</strong></p><p>Checked at {safe(report['checked_at'])}</p>
<div class="notice"><strong>Not ready for training or purchasing.</strong>
<p>Every proposed label still needs human acceptance. A passed check is not proof of permission or delivery.</p></div>
<div class="grid">{''.join(cards)}</div>
<section><h2>Next action</h2><p>{safe(report['next_action'])}</p></section>
<section><h2>Evidence limits</h2><ul>{limits}</ul>
<p>Keep reports from genuine inputs in buyer-approved private storage, outside GitHub.</p></section>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', help='Approved external pilot folder; never use tracked templates as working records')
    parser.add_argument('--format', choices=('html', 'json'), default='html')
    args = parser.parse_args()
    report = readiness(args.folder, datetime.now(timezone.utc))
    output = render_html(report) if args.format == 'html' else json.dumps(report, indent=2)
    # Keep redirected reports UTF-8 on Windows as well as the terminal.
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print(output)
    return 2 if report['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
