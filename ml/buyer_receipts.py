"""Read-only reconciliation of supplied acceptance/rejection/reversal events."""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from itertools import groupby
import json
from pathlib import Path

from buyer_snapshot_check import TEMPLATES, active_snapshots, check_approval, load_pilot_snapshots, read_csv
from real_procurement import DataError, amount, text, timestamp


def reconcile_receipts(snapshots, receipts, setup, as_of):
    orders = active_snapshots(snapshots, setup, as_of)
    approval_start = check_approval(setup, as_of)
    events, by_line = {}, {key: [] for key in orders}
    for number, row in enumerate(receipts, 2):
        label = f'receipt_events row {number}'
        for field in ('receipt_event_id', 'order_line_id', 'destination_id', 'event_type', 'event_at',
                      'quantity', 'unit', 'pilot_id', 'data_kind', 'source_ref', 'known_at', 'captured_at', 'reviewer_id'):
            if text(row.get(field), f'{label}.{field}') != row[field]:
                raise DataError(f'{label}.{field}: remove surrounding whitespace explicitly')
        if row['receipt_event_id'] in events:
            raise DataError(f'{label}.receipt_event_id: duplicate ID')
        if row['pilot_id'] != setup['pilot_id'] or row['data_kind'] != 'real':
            raise DataError(f'{label}: wrong pilot or data kind; do not mix sources')
        order = orders.get(row['order_line_id'])
        if order is None:
            raise DataError(f'{label}.order_line_id: unknown active order line')
        if row['destination_id'] != order['destination_id'] or row['unit'] != order['unit']:
            raise DataError(f'{label}: destination and unit must match the active original order')
        kind = row['event_type']
        if kind not in ('accepted', 'rejected', 'reversal'):
            raise DataError(f'{label}.event_type: expected accepted, rejected or reversal')
        happened = timestamp(row['event_at'], f'{label}.event_at')
        known = timestamp(row['known_at'], f'{label}.known_at')
        captured = timestamp(row['captured_at'], f'{label}.captured_at')
        placed = timestamp(order['order_placed_at'], f'{label}.order_placed_at')
        if not placed <= happened <= known <= captured <= as_of or captured < approval_start:
            raise DataError(f'{label}: require placement <= event <= known <= capture <= check time, with capture inside approval')
        quantity = amount(row['quantity'], f'{label}.quantity')
        parent = row.get('reverses_event_id', '')
        if not isinstance(parent, str) or parent != parent.strip():
            raise DataError(f'{label}.reverses_event_id: use an exact ID or blank')
        if (kind == 'reversal') != bool(parent):
            raise DataError(f'{label}.reverses_event_id: required only for reversals')
        event = dict(row=row, kind=kind, happened=happened, known=known,
                     quantity=quantity, parent=parent, number=number)
        events[row['receipt_event_id']] = event
        by_line[row['order_line_id']].append(event)

    # Each input has <=24 decimal digits; allow exact batch sums without context rounding.
    with localcontext() as context:
        context.prec = max(28, 25 + len(str(max(1, len(receipts)))))
        reversed_by_parent = {}
        for event in events.values():
            if event['kind'] != 'reversal':
                continue
            original = events.get(event['parent'])
            label = f"receipt_events row {event['number']}"
            if original is None or original['kind'] != 'accepted':
                raise DataError(f'{label}.reverses_event_id: must reference an accepted receipt')
            if original['row']['order_line_id'] != event['row']['order_line_id']:
                raise DataError(f'{label}: reversal must reference the same order line')
            if event['happened'] < original['happened'] or event['known'] < original['known']:
                raise DataError(f'{label}: reversal cannot precede its acceptance or its availability')
            total = reversed_by_parent.get(event['parent'], Decimal(0)) + event['quantity']
            if total > original['quantity']:
                raise DataError(f'{label}.quantity: cumulative reversal exceeds referenced acceptance')
            reversed_by_parent[event['parent']] = total

        lines = []
        for key, order in sorted(orders.items()):
            entries = sorted(by_line[key], key=lambda event: event['happened'])
            ordered = amount(order['quantity'], 'order.quantity')
            accepted = rejected = reversed_quantity = balance = Decimal(0)
            complete_at = None
            for happened, simultaneous in groupby(entries, key=lambda event: event['happened']):
                delta = Decimal(0)
                for event in simultaneous:
                    quantity = event['quantity']
                    if event['kind'] == 'accepted':
                        accepted += quantity
                        delta += quantity
                    elif event['kind'] == 'rejected':
                        rejected += quantity
                    else:
                        reversed_quantity += quantity
                        delta -= quantity
                balance += delta
                if balance < ordered:
                    complete_at = None
                elif complete_at is None:
                    complete_at = happened
            excess = max(balance - ordered, Decimal(0))
            status = 'no_receipts' if not entries else 'not_accepted' if balance == 0 else 'partial' if balance < ordered else 'quantity_met'
            lines.append({'order_line_id': key, 'unit': order['unit'], 'ordered_quantity': format(ordered, 'f'),
                          'gross_accepted_quantity': format(accepted, 'f'), 'rejected_quantity': format(rejected, 'f'),
                          'reversed_quantity': format(reversed_quantity, 'f'), 'net_accepted_quantity': format(balance, 'f'),
                          'remaining_quantity': format(max(ordered - balance, Decimal(0)), 'f'),
                          'over_accepted_quantity': format(excess, 'f'), 'needs_quantity_review': excess > 0,
                          'receipt_status': status, 'ledger_complete_at': complete_at.isoformat() if complete_at else None})
    return {'status': 'supplied_receipts_reconciled', 'as_of': as_of.astimezone(timezone.utc).isoformat(),
            'receipt_events': len(receipts), 'active_order_lines': len(lines), 'lines': lines,
            'coverage_confirmed': False, 'model_ready': False, 'purchase_authorized': False,
            'limitations': ['supplied events only; source authenticity and receipt-register coverage require review',
                            'ledger_complete_at is derived from the net event ledger, not a reviewed delivery outcome',
                            'promise, cancellation and scope-change review remain required; no delay labels assigned']}


def reconcile_folder(folder, as_of):
    setup, snapshots = load_pilot_snapshots(folder, as_of)
    # Validate snapshots before reading potentially sensitive receipt rows.
    active_snapshots(snapshots, setup, as_of)
    with (TEMPLATES / 'receipt_events.csv').open(encoding='utf-8-sig', newline='') as stream:
        headers = next(csv.reader(stream))
    receipts = read_csv(Path(folder).resolve() / 'receipt_events.csv', headers)
    return reconcile_receipts(snapshots, receipts, setup, as_of)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', help='Approved external folder containing pilot setup, snapshots and receipt CSVs')
    args = parser.parse_args()
    try:
        report = reconcile_folder(args.folder, datetime.now(timezone.utc))
    except DataError as error:
        print(json.dumps({'status': 'blocked', 'reason': str(error), 'model_ready': False}))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
