"""Evidence-aware supplier replacement proposals; no prediction, training or purchasing."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from html import escape
import hashlib
import json
from pathlib import Path
import sys

from real_procurement import DataError, amount, evaluate, indexed, no_duplicate_keys, text, timestamp


def recover(bundle, as_of, *, demo=False):
    review = evaluate(bundle, as_of, demo=demo)
    sources = indexed(bundle['sources'], 'sources')
    suppliers = indexed(bundle['suppliers'], 'suppliers')
    quotes = indexed(bundle['quotes'], 'quotes')
    event = bundle.get('recovery_event')
    if not isinstance(event, dict) or event.get('type') != 'supplier_unavailable' or event.get('confirmed') is not True:
        raise DataError('recovery_event: confirmed supplier_unavailable declaration required')
    failed = text(event.get('supplier_id'), 'recovery_event.supplier_id')
    event_source = text(event.get('source_id'), 'recovery_event.source_id')
    if failed not in suppliers or event_source not in sources:
        raise DataError('recovery_event: unknown supplier or source')
    text(event.get('source_record_id'), 'recovery_event.source_record_id')
    happened = timestamp(event.get('event_at'), 'recovery_event.event_at')
    known = timestamp(event.get('known_at'), 'recovery_event.known_at')
    if not happened <= known <= as_of:
        raise DataError('recovery_event: require event <= known <= decision time')
    supplied = bundle.get('capacity_evidence', [])
    if not isinstance(supplied, list):
        raise DataError('capacity_evidence: list required')
    capacity, identities = {}, set()
    for row in supplied:
        if not isinstance(row, dict): raise DataError('capacity_evidence: object required')
        key = text(row.get('quote_id'), 'capacity.quote_id')
        identity = (text(row.get('source_id'), 'capacity.source_id'),
                    text(row.get('source_record_id'), 'capacity.source_record_id'))
        if key not in quotes or key in capacity or identity in identities or identity[0] not in sources:
            raise DataError('capacity_evidence: unknown/duplicate quote or source record')
        identities.add(identity)
        quantity = amount(row.get('quantity'), 'capacity.quantity', zero=True)
        unit = text(row.get('unit'), 'capacity.unit')
        available = timestamp(row.get('known_at'), 'capacity.known_at')
        expires = timestamp(row.get('valid_until'), 'capacity.valid_until')
        if expires <= available or type(row.get('confirmed')) is not bool:
            raise DataError('capacity_evidence: invalid validity interval or confirmation')
        capacity[key] = (row, quantity, unit, available, expires)
    request = bundle['request']
    options = []
    for result in review['quotes']:
        key = result['quote_id']; quote = quotes[key]
        reasons = list(result['reasons'])
        status = 'infeasible' if reasons else 'feasible'
        if result['brand_review']['status'] in ('missing_information', 'alternative_pending_review') or any(word in reason.lower() for reason in reasons for word in ('not confirmed', 'not available', 'not verified', 'expired', 'in the past')):
            status = 'unavailable'
        evidence = capacity.get(key)
        if result['supplier_id'] == failed:
            status, reasons = 'excluded', ['Disrupted supplier excluded']
        elif evidence is None:
            status = 'unavailable'; reasons.append('Capacity evidence missing')
        else:
            row, quantity, unit, available, expires = evidence
            if not row['confirmed'] or not available <= as_of < expires:
                status = 'unavailable'; reasons.append('Capacity evidence unconfirmed, future-known or expired')
            elif unit != request['unit']:
                status = 'unavailable'; reasons.append('Capacity unit mapping unverified')
            elif quantity < amount(request['quantity'], 'request.quantity'):
                if status == 'feasible': status = 'infeasible'
                reasons.append('Documented available quantity is insufficient')
        options.append(dict(quote_id=key, supplier_id=result['supplier_id'], status=status, reasons=reasons,
                            quoted_total=result['quoted_total'], currency=result['currency'],
                            promised_delivery_date=quote['promised_delivery_date'], source_id=quote['source_id'],
                            source_record_id=quote['source_record_id'],
                            capacity_source_record_id=evidence[0]['source_record_id'] if evidence else None,
                            capacity_evidence={field:evidence[0][field] for field in ('source_id','source_record_id','quantity','unit','known_at','valid_until','confirmed')} if evidence else None,
                            cost_rank=None, risk_estimate=None))
    feasible = sorted((row for row in options if row['status'] == 'feasible'),
                      key=lambda row: (Decimal(row['quoted_total']), row['quote_id']))
    previous, rank = None, None
    for position, row in enumerate(feasible, 1):
        total = Decimal(row['quoted_total'])
        if total != previous: rank = position
        row['cost_rank'], previous = rank, total
    return dict(schema_version='1.0', report_kind='supplier_replacement',
                status='options_available' if feasible else 'needs_review' if any(r['status']=='unavailable' for r in options) else 'infeasible',
                decision_at=as_of.isoformat(), evidence_kind='synthetic' if demo else 'declared_real',
                request=deepcopy(request), disruption=deepcopy(event), options=options,
                proposed_quote_ids=[row['quote_id'] for row in feasible if row['cost_rank'] == 1],
                input_sha256=hashlib.sha256(json.dumps(bundle, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                purchase_authorized=False, model_ready=False, human_review_required=True,
                limitations=['Deterministic quote/capacity checks, not AI prediction or a causal recovery guarantee.',
                             'Sources, permission and capacity are declarations, not authenticated or reserved inventory.',
                             'One supplier replaces the full quantity; no split sourcing, conversions, live detection or stock reservation.',
                             'Lowest documented total among feasible offers is not overall supplier quality. Risk is unavailable.'])


def render_html(report):
    safe = lambda value: escape(str(value), quote=True)
    cards = []
    for row in report.get('options', []):
        fields = {key: row[key] for key in ('quoted_total','currency','promised_delivery_date','cost_rank','source_id',
                                           'source_record_id','capacity_source_record_id')}
        detail = ''.join(f'<dt>{safe(k.replace("_"," "))}</dt><dd>{safe(v if v is not None else "Unavailable")}</dd>' for k,v in fields.items())
        for key,value in (row['capacity_evidence'] or {}).items():
            detail += f'<dt>Capacity {safe(key.replace("_"," "))}</dt><dd>{safe(value)}</dd>'
        reasons = ''.join(f'<li>{safe(reason)}</li>' for reason in row['reasons'])
        cards.append(f'<article><p class="badge">{safe(row["status"].upper())}</p><h2>{safe(row["supplier_id"])} · '
                     f'{safe(row["quote_id"])}</h2><ul>{reasons}</ul><details><summary>Offer and evidence details</summary><dl>{detail}</dl></details></article>')
    status = safe(report.get('reason', report['status'].replace('_', ' ')))
    proposed = ', '.join(report.get('proposed_quote_ids', [])) or 'None — resolve evidence or constraints'
    context = ''
    if 'request' in report:
        fields = {key:report['request'].get(key) for key in ('product_id','quantity','unit','currency','total_budget','needed_by','destination_id')}
        fields.update({'disruption '+key:report['disruption'][key] for key in ('supplier_id','source_id','source_record_id','event_at','known_at')})
        context = '<details><summary>Original request and disruption evidence</summary><dl>' + ''.join(
            f'<dt>{safe(k.replace("_"," "))}</dt><dd>{safe(v)}</dd>' for k,v in fields.items()) + '</dl></details>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>Supplier replacement review</title><style>body{{font:16px/1.6 system-ui;background:#f5f7f6;color:#172e36;margin:0}}main{{max-width:1000px;margin:auto;padding:24px}}
article,.notice{{background:white;border:1px solid #dce5e4;border-radius:12px;padding:20px;margin:16px 0}}.notice{{border-left:4px solid #a67b1f}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:16px}}h2{{font-size:1.15rem}}dt{{font-weight:bold}}dd{{margin:0 0 10px}}p,li,dd,h2{{overflow-wrap:anywhere}}.badge{{font-weight:bold}}summary{{cursor:pointer}}summary:focus-visible{{outline:3px solid #dfac42}}</style></head>
<body><main><p>Local decision support · {safe(report.get('evidence_kind','blocked input'))}</p><h1>Supplier replacement review</h1>
<div class="notice"><strong>Human review required. Training and purchasing remain unauthorized.</strong><p>Proposals use declared documented offers and capacity, not validated AI predictions. Sources and available inventory are unverified; nothing is reserved or sent. Keep genuine reports private.</p></div>
<p role="status">{status}</p><p>Decision time: {safe(report.get('decision_at','Unavailable'))}</p><p>Lowest-cost feasible proposal: {safe(proposed)}</p>{context}<p>One alternative must cover the full requested quantity and original constraints. Missing/stale evidence is unavailable, not a promise of recovery. Risk remains unavailable.</p>
<div class="grid">{''.join(cards)}</div></main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--demo', action='store_true', help='Require exclusively synthetic source declarations')
    parser.add_argument('--format', choices=('html','json'), default='html')
    args = parser.parse_args()
    try:
        bundle = json.loads(args.input.read_text(encoding='utf-8-sig'), object_pairs_hook=no_duplicate_keys)
        report = recover(bundle, datetime.now(timezone.utc), demo=args.demo)
    except (DataError, OSError, UnicodeError, json.JSONDecodeError) as error:
        reason = str(error) if isinstance(error, DataError) else 'Cannot read a valid UTF-8 JSON input bundle'
        report = dict(status='blocked', reason=reason, options=[], purchase_authorized=False,
                      model_ready=False, human_review_required=True)
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    print(render_html(report) if args.format=='html' else json.dumps(report,indent=2))
    return 0 if report['status']=='options_available' else 2


if __name__ == '__main__': raise SystemExit(main())
