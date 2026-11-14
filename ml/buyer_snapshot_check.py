"""Read-only preflight for declared buyer approval and release snapshots, not outcomes."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from real_procurement import DataError, amount, day, decision_zone, text, timestamp

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'real-pilot/buyer-data-collection/csv-templates'


def read_csv(path, expected):
    """Reject malformed shape without echoing buyer values or source references."""
    try:
        with Path(path).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != expected:
                raise DataError(f'{Path(path).name}: headers must match the current blank template')
            rows = []
            for number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise DataError(f'{Path(path).name}: row {number} has the wrong field count')
                if any(value.strip() for value in row.values()):
                    rows.append(row)
            return rows
    except (OSError, UnicodeError, csv.Error):
        raise DataError(f'{Path(path).name}: cannot read a UTF-8 CSV file') from None


def check_approval(setup, as_of):
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise DataError('as_of: timezone required')
    if setup.get('permission_status') != 'approved' or setup.get('data_kind') != 'real':
        raise DataError('pilot_setup: declared real data and approved permission are required')
    for field in ('pilot_id', 'buyer_id', 'approval_ref', 'sponsor_role', 'data_owner',
                  'receipt_reviewer', 'permitted_use', 'site_and_products', 'history_window',
                  'decision_rule', 'target_version', 'timezone', 'grace_and_scope_rules',
                  'review_capacity', 'approved_storage', 'access_roles', 'retention_delete',
                  'withdrawal_procedure', 'backup_restore'):
        if text(setup.get(field), f'pilot_setup.{field}') != setup[field]:
            raise DataError(f'pilot_setup.{field}: remove surrounding whitespace explicitly')
    decision_zone(setup['timezone'])
    start = timestamp(setup.get('valid_from'), 'pilot_setup.valid_from')
    end = timestamp(setup.get('valid_until'), 'pilot_setup.valid_until')
    if not start <= as_of < end:
        raise DataError('pilot_setup: permission must be active at the check time')
    return start


def check_snapshots(rows, setup, as_of):
    """Fail the whole batch on unresolved records; never create model-ready output."""
    approval_start = check_approval(setup, as_of)
    if not rows:
        raise DataError('order_snapshots: no records supplied')
    required = ('snapshot_id', 'order_line_id', 'supplier_id', 'product_id', 'destination_id',
                'decision_at', 'order_placed_at', 'original_promise_date', 'promise_basis',
                'decision_timezone', 'quantity', 'unit', 'snapshot_status', 'pilot_id',
                'data_kind', 'source_ref', 'known_at', 'captured_at', 'reviewer_id')
    nodes, lines = {}, {}
    for number, row in enumerate(rows, 2):
        label = f'order_snapshots row {number}'
        for field in required:
            value = text(row.get(field), f'{label}.{field}')
            if value != row[field]:
                raise DataError(f'{label}.{field}: remove surrounding whitespace explicitly')
        if row['snapshot_id'] in nodes:
            raise DataError(f'{label}.snapshot_id: duplicate ID')
        if row['pilot_id'] != setup['pilot_id'] or row['data_kind'] != 'real':
            raise DataError(f'{label}: wrong pilot or data kind; do not mix sources')
        if row['snapshot_status'] != 'verified_as_of':
            raise DataError(f'{label}.snapshot_status: verified_as_of required; retain unresolved evidence separately')
        if row['promise_basis'] not in ('supplier_quotation', 'supplier_acknowledgement', 'contract_schedule'):
            raise DataError(f'{label}.promise_basis: a documented supplier commitment is required')
        placed = timestamp(row['order_placed_at'], f'{label}.order_placed_at')
        decision = timestamp(row['decision_at'], f'{label}.decision_at')
        known = timestamp(row['known_at'], f'{label}.known_at')
        captured = timestamp(row['captured_at'], f'{label}.captured_at')
        if decision != placed or known > decision or captured < decision or captured < approval_start or captured > as_of:
            raise DataError(f'{label}: require known <= decision = placement <= capture <= check time, with capture inside approval')
        if row['decision_timezone'] != setup['timezone']:
            raise DataError(f'{label}.decision_timezone: must match the approved one-site pilot')
        decision_zone(row['decision_timezone'])
        for field in ('original_promise_date', 'needed_by_date'):
            if row.get(field):
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', row[field]):
                    raise DataError(f'{label}.{field}: expected YYYY-MM-DD')
                day(row[field], f'{label}.{field}')
        amount(row['quantity'], f'{label}.quantity')
        if row.get('unit_price'):
            amount(row['unit_price'], f'{label}.unit_price', zero=True)
            text(row.get('currency'), f'{label}.currency')
        if row.get('currency') and not re.fullmatch('[A-Z]{3}', row['currency']):
            raise DataError(f'{label}.currency: three uppercase letters required')
        if row.get('on_contract', '') not in ('', 'yes', 'no', 'unknown'):
            raise DataError(f'{label}.on_contract: expected yes, no, unknown or blank')
        predecessor = row.get('supersedes_id', '')
        if not isinstance(predecessor, str) or predecessor != predecessor.strip():
            raise DataError(f'{label}.supersedes_id: use an exact snapshot ID or blank')
        nodes[row['snapshot_id']] = (row, decision, captured, predecessor, number)
        lines.setdefault(row['order_line_id'], []).append(row['snapshot_id'])
    children = {}
    for key, (row, decision, captured, parent, number) in nodes.items():
        if not parent:
            continue
        if parent not in nodes:
            raise DataError(f'order_snapshots row {number}.supersedes_id: missing predecessor')
        old, old_decision, old_capture, _, _ = nodes[parent]
        if old['order_line_id'] != row['order_line_id'] or decision != old_decision or captured < old_capture:
            raise DataError(f'order_snapshots row {number}: correction must preserve line/decision and follow predecessor capture')
        if parent in children:
            raise DataError('order_snapshots: competing corrections require review')
        children[parent] = key
    for keys in lines.values():
        roots = [key for key in keys if not nodes[key][3]]
        if len(roots) != 1:
            raise DataError('order_snapshots: each line needs one original snapshot; resolve multiple roots or cycles')
        visited, key = set(), roots[0]
        while key is not None and key not in visited:
            visited.add(key)
            key = children.get(key)
        if key is not None or len(visited) != len(keys):
            raise DataError('order_snapshots: cyclic or disconnected correction chain')
    return {'status': 'snapshot_preflight_passed', 'snapshot_rows': len(rows),
            'active_order_lines': len(lines), 'correction_rows': len(rows) - len(lines),
            'model_ready': False, 'purchase_authorized': False,
            'remaining': ['source/approval authenticity and permitted-use review',
                          'promise, cancellation, receipt and outcome reconciliation',
                          'reviewed modelling mapping and chronological evaluation']}


def active_snapshots(rows, setup, as_of):
    """Resolve leaves only after validating every snapshot and correction chain."""
    check_snapshots(rows, setup, as_of)
    replaced = {row['supersedes_id'] for row in rows if row.get('supersedes_id')}
    return {row['order_line_id']: row for row in rows if row['snapshot_id'] not in replaced}


def load_pilot_snapshots(folder, as_of):
    """Share external-folder/approval/schema checks with receipt reconciliation."""
    folder = Path(folder).resolve()
    if folder.is_relative_to(ROOT.resolve()):
        raise DataError('Use a buyer-approved working folder outside the repository; keep tracked templates blank')
    expected_setup = read_csv(TEMPLATES / 'pilot_setup.csv', ['field', 'buyer_value', 'instruction'])
    setup_rows = read_csv(folder / 'pilot_setup.csv', ['field', 'buyer_value', 'instruction'])
    fields = [row['field'] for row in setup_rows]
    if len(fields) != len(set(fields)) or set(fields) != {row['field'] for row in expected_setup}:
        raise DataError('pilot_setup: missing, duplicate or unexpected setup fields')
    setup = {row['field']: row['buyer_value'] for row in setup_rows}
    check_approval(setup, as_of)
    with (TEMPLATES / 'order_snapshots.csv').open(encoding='utf-8-sig', newline='') as stream:
        headers = next(csv.reader(stream))
    return setup, read_csv(folder / 'order_snapshots.csv', headers)


def check_folder(folder, as_of):
    setup, rows = load_pilot_snapshots(folder, as_of)
    return check_snapshots(rows, setup, as_of)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path, help='Approved external folder containing pilot_setup.csv and order_snapshots.csv')
    args = parser.parse_args()
    try:
        report = check_folder(args.folder, datetime.now(timezone.utc))
    except DataError as error:
        print(json.dumps({'status': 'blocked', 'reason': str(error), 'model_ready': False}))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
