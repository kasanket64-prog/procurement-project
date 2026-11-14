"""Propose original-promise delay labels from reviewed coverage; never train or write records."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path

from buyer_receipts import reconcile_receipts
from buyer_snapshot_check import TEMPLATES, active_snapshots, check_approval, load_pilot_snapshots, read_csv
from real_procurement import DataError, day, decision_zone, no_duplicate_keys, text, timestamp

POLICY_FIELDS = {'schema_version', 'policy_id', 'pilot_id', 'target_version', 'approval_ref',
                 'approval_confirmed', 'approved_at', 'grace_days', 'target_rule', 'cancellation_rule'}
SIGNAL_TYPES = {'acknowledgement', 'stock_commitment', 'capacity_commitment', 'dispatch_milestone',
                'disruption', 'quantity_change', 'specification_change', 'cancellation'}
LABELS = {'pending', 'unknown', 'on_time', 'late', 'cancelled', 'excluded'}


def check_policy(policy, setup, as_of):
    if not isinstance(policy, dict) or set(policy) != POLICY_FIELDS:
        raise DataError('label_policy: use the exact version 1.0 policy fields')
    if (policy['schema_version'] != '1.0' or policy['approval_confirmed'] is not True
            or type(policy['grace_days']) is not int or policy['grace_days'] != 0
            or policy['target_rule'] != 'net_accepted_at_original_date_end'
            or policy['cancellation_rule'] != 'pre_deadline_cancelled_post_deadline_preserve_outcome'):
        raise DataError('label_policy: explicit approved original-date/no-grace policy is required; other rules are unsupported')
    text(policy['policy_id'], 'label_policy.policy_id')
    for field in ('pilot_id', 'target_version', 'approval_ref'):
        if policy[field] != setup[field]:
            raise DataError(f'label_policy.{field}: must match approved pilot setup')
    approved = timestamp(policy['approved_at'], 'label_policy.approved_at')
    if approved > as_of:
        raise DataError('label_policy: approval cannot be in the future')
    return approved


def deadline(order):
    """Exclusive next-local-day boundary, rather than an invented 23:59:59 promise."""
    zone = decision_zone(order['decision_timezone'])
    promised = day(order['original_promise_date'], 'original_promise_date')
    try:
        tomorrow = promised + timedelta(days=1)
        if datetime.combine(promised, time(12), zone).astimezone(timezone.utc).astimezone(zone).date() != promised:
            raise ValueError('Skipped local date')
        boundary = datetime.combine(tomorrow, time.min, zone).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise DataError('original_promise_date: unsupported calendar boundary') from None
    if boundary.astimezone(zone).date() != tomorrow:
        raise DataError('original_promise_date: unusual timezone boundary needs manual review')
    return boundary


def records(rows, setup, orders, as_of, *, signals):
    """Validate review/signal provenance and correction links before resolving versions."""
    key_field = 'signal_id' if signals else 'review_id'
    clock_field = 'event_at' if signals else 'reviewed_at'
    approval_start = check_approval(setup, as_of)
    indexed, children = {}, {}
    for number, row in enumerate(rows, 2):
        label = f'{"decision_signals" if signals else "outcome_reviews"} row {number}'
        for field in (key_field, 'order_line_id', clock_field, 'known_at', 'captured_at',
                      'pilot_id', 'data_kind', 'source_ref', 'reviewer_id'):
            if text(row.get(field), f'{label}.{field}') != row[field]:
                raise DataError(f'{label}.{field}: remove surrounding whitespace explicitly')
        if row[key_field] in indexed:
            raise DataError(f'{label}: duplicate record ID')
        if row['pilot_id'] != setup['pilot_id'] or row['data_kind'] != 'real' or row['order_line_id'] not in orders:
            raise DataError(f'{label}: unknown order line or mismatched pilot/data kind')
        event = timestamp(row[clock_field], f'{label}.{clock_field}')
        known = timestamp(row['known_at'], f'{label}.known_at')
        capture = timestamp(row['captured_at'], f'{label}.captured_at')
        placed = timestamp(orders[row['order_line_id']]['order_placed_at'], 'order_placed_at')
        if not event <= known <= capture <= as_of or capture < approval_start:
            raise DataError(f'{label}: require event/review <= known <= capture <= check time, within capture approval')
        lifecycle = not signals or row.get('signal_type') in ('cancellation', 'quantity_change', 'specification_change')
        if lifecycle and event < placed:
            raise DataError(f'{label}: lifecycle event/review cannot precede order placement')
        parent = row.get('supersedes_id', '')
        if not isinstance(parent, str) or parent != parent.strip():
            raise DataError(f'{label}.supersedes_id: use an exact ID or blank')
        if signals:
            if row.get('signal_type') not in SIGNAL_TYPES or row.get('verification') not in (
                    'unverified', 'supplier_claim', 'buyer_verified', 'independent_source'):
                raise DataError(f'{label}: invalid signal type/verification')
            if row['signal_type'] == 'cancellation':
                text(row.get('value_text'), f'{label}.value_text')
        else:
            if (row.get('target_version') != setup['target_version'] or row.get('label') not in LABELS
                    or row.get('delivery_status') not in ('open', 'partial', 'completed', 'cancelled', 'disputed')
                    or row.get('coverage_confirmed') not in ('yes', 'no', 'unknown')):
                raise DataError(f'{label}: invalid target, status, label or coverage declaration')
            if row['reviewer_id'] != setup['receipt_reviewer']:
                raise DataError(f'{label}.reviewer_id: must match the approved receiving reviewer')
            if row.get('register_coverage_through'):
                if timestamp(row['register_coverage_through'], 'register_coverage_through') > event:
                    raise DataError(f'{label}: coverage cannot extend beyond the actual review time')
            elif row['coverage_confirmed'] == 'yes':
                raise DataError(f'{label}: confirmed coverage requires register_coverage_through')
            if row.get('complete_accepted_at'):
                if timestamp(row['complete_accepted_at'], 'complete_accepted_at') > event:
                    raise DataError(f'{label}: completion cannot be after review')
        indexed[row[key_field]] = row
    for key, row in indexed.items():
        parent = row.get('supersedes_id', '')
        if not parent:
            continue
        previous = indexed.get(parent)
        if previous is None or previous['order_line_id'] != row['order_line_id']:
            raise DataError('review/signal correction: missing or cross-line predecessor')
        if signals and previous['signal_type'] != row['signal_type']:
            raise DataError('signal correction: type must match predecessor')
        if parent in children:
            raise DataError('review/signal correction: competing successors')
        for field in ('known_at', 'captured_at') + (() if signals else ('reviewed_at',)):
            if timestamp(row[field], field) < timestamp(previous[field], field):
                raise DataError('review/signal correction: availability/capture cannot precede predecessor')
        children[parent] = key
    seen = set()
    for root in (key for key, row in indexed.items() if not row.get('supersedes_id')):
        key = root
        while key is not None and key not in seen:
            seen.add(key)
            key = children.get(key)
    if len(seen) != len(indexed):
        raise DataError('review/signal correction: cyclic chain')
    return indexed


def active_versions(indexed, cutoff):
    visible = {key: row for key, row in indexed.items() if timestamp(row['known_at'], 'known_at') <= cutoff}
    superseded = {row['supersedes_id'] for row in visible.values() if row.get('supersedes_id')}
    return [row for key, row in visible.items() if key not in superseded]


def label_delays(snapshots, receipts, reviews, signals, setup, policy, as_of):
    orders = active_snapshots(snapshots, setup, as_of)
    approved_at = check_policy(policy, setup, as_of)
    reconcile_receipts(snapshots, receipts, setup, as_of)
    review_records = records(reviews, setup, orders, as_of, signals=False)
    signal_records = records(signals, setup, orders, as_of, signals=True)
    by_review, by_receipt, by_snapshot = defaultdict(list), defaultdict(list), defaultdict(list)
    by_signal = defaultdict(dict)
    for row in active_versions(review_records, as_of):
        by_review[row['order_line_id']].append(row)
    for row in receipts:
        by_receipt[row['order_line_id']].append(row)
    for row in snapshots:
        by_snapshot[row['order_line_id']].append(row)
    for identity, row in signal_records.items():
        by_signal[row['order_line_id']][identity] = row
    output = []
    for key, order in sorted(orders.items()):
        boundary = deadline(order)
        if timestamp(order['order_placed_at'], 'order_placed_at') >= boundary:
            raise DataError('original_promise_date: precedes order placement in destination timezone')
        result = {'order_line_id': key, 'original_promise_date': order['original_promise_date'],
                  'deadline_exclusive_utc': boundary.isoformat(), 'label': 'unknown',
                  'reason': 'no_outcome_review', 'label_known_at': None, 'human_label_review_required': True}
        candidates = sorted(by_review[key], key=lambda row: timestamp(row['reviewed_at'], 'reviewed_at'))
        if not candidates:
            output.append(result)
            continue
        review = candidates[-1]
        at = timestamp(review['reviewed_at'], 'reviewed_at')
        if len(candidates) > 1 and timestamp(candidates[-2]['reviewed_at'], 'reviewed_at') == at:
            raise DataError('outcome_reviews: competing active reviews at the same review time')
        visible_receipts = [r for r in by_receipt[key] if timestamp(r['known_at'], 'known_at') <= at]
        visible_signals = [r for r in active_versions(by_signal[key], at)
                           if r['signal_type'] in ('cancellation', 'quantity_change', 'specification_change')]
        line = reconcile_receipts(by_snapshot[key], visible_receipts, setup, as_of)['lines'][0]
        original_day = [r for r in visible_receipts if timestamp(r['event_at'], 'event_at') < boundary]
        at_deadline = reconcile_receipts(by_snapshot[key], original_day, setup, as_of)['lines'][0]
        result.update(review_id=review['review_id'], delivery_status=review['delivery_status'],
                      reviewed_at=at.isoformat(), coverage_confirmed=review['coverage_confirmed'] == 'yes',
                      register_coverage_through=review['register_coverage_through'] or None,
                      review_known_at=timestamp(review['known_at'], 'known_at').isoformat(),
                      label_evidence_available_at=timestamp(review['known_at'], 'known_at').isoformat(),
                      net_accepted_at_review=line['net_accepted_quantity'],
                      net_accepted_at_deadline=at_deadline['net_accepted_quantity'])
        cancellations = [r for r in visible_signals if r['signal_type'] == 'cancellation']
        cancelled_times = {timestamp(r['event_at'], 'event_at') for r in cancellations}
        covered = (review['coverage_confirmed'] == 'yes' and
                   timestamp(review['register_coverage_through'], 'register_coverage_through') >= boundary)
        if (approved_at > at or timestamp(order['captured_at'], 'captured_at') > at
                or any(timestamp(r['captured_at'], 'captured_at') > at for r in visible_receipts + visible_signals)):
            reason = 'policy_or_evidence_requires_new_review'
        elif review['delivery_status'] == 'disputed' or line['needs_quantity_review'] or at_deadline['needs_quantity_review']:
            reason = 'dispute_or_quantity_excess'
        elif any(r['signal_type'] in ('quantity_change', 'specification_change') for r in visible_signals):
            reason = 'material_scope_change_requires_review'
        elif cancellations and (len(cancelled_times) != 1 or any(r['verification'] not in ('buyer_verified','independent_source') for r in cancellations)):
            reason = 'cancellation_evidence_unresolved'
        elif bool(cancellations) != (review['delivery_status'] == 'cancelled'):
            reason = 'cancellation_status_requires_matching_signal'
        elif cancellations and not all(r['signal_id'] in review.get('exclusion_or_dispute','').split() for r in cancellations):
            reason = 'cancellation_signal_link_missing_from_review'
        elif cancellations and next(iter(cancelled_times)) < boundary:
            result['label'], reason = 'cancelled', 'approved_pre_deadline_cancellation'
        elif review['delivery_status'] == 'completed' and (
                line['receipt_status'] != 'quantity_met' or not review.get('complete_accepted_at')
                or timestamp(review['complete_accepted_at'], 'complete_accepted_at') != timestamp(line['ledger_complete_at'], 'ledger_complete_at')):
            reason = 'completion_review_conflicts_with_receipts'
        elif review['delivery_status'] in ('open','partial') and line['receipt_status'] == 'quantity_met':
            reason = 'open_status_conflicts_with_full_acceptance'
        elif at < boundary:
            result['label'], reason = 'pending', 'original_deadline_not_closed'
        elif not covered:
            reason = 'receipt_coverage_not_confirmed_through_deadline'
        else:
            result['label'] = 'on_time' if at_deadline['receipt_status'] == 'quantity_met' else 'late'
            reason = 'confirmed_original_deadline_balance'
        if review['label'] not in ('pending','unknown',result['label']):
            result['calculation_reason'] = reason
            result['candidate_label'] = result['label']
            result['label'], reason = 'unknown', 'existing_review_label_conflicts_with_calculation'
        result['reason'] = reason
        if result['label'] == 'unknown':
            result['label_evidence_available_at'] = None
        output.append(result)
    return {'status': 'delay_labels_proposed', 'policy_id': policy['policy_id'],
            'policy_sha256': hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(',',':')).encode()).hexdigest(),
            'target_version': policy['target_version'], 'generated_at': as_of.astimezone(timezone.utc).isoformat(),
            'label_counts': dict(Counter(row['label'] for row in output)), 'lines': output,
            'model_ready': False, 'purchase_authorized': False,
            'limitations': ['coverage and source authenticity are declared by the reviewer, not independently verified',
                            'labels require human acceptance; nonzero grace and material scope changes are unsupported']}


def label_folder(folder, as_of):
    setup, snapshots = load_pilot_snapshots(folder, as_of)
    active_snapshots(snapshots, setup, as_of)
    folder = Path(folder).resolve()
    try:
        policy = json.loads((folder / 'label_policy.json').read_text(encoding='utf-8-sig'), object_pairs_hook=no_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise DataError('label_policy.json: cannot read valid UTF-8 JSON') from None
    check_policy(policy, setup, as_of)
    tables = []
    for name in ('receipt_events', 'outcome_reviews', 'decision_signals'):
        with (TEMPLATES / f'{name}.csv').open(encoding='utf-8-sig', newline='') as stream:
            headers = next(csv.reader(stream))
        tables.append(read_csv(folder / f'{name}.csv', headers))
    return label_delays(snapshots, *tables, setup, policy, as_of)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', help='Approved external pilot folder with CSVs and label_policy.json')
    args = parser.parse_args()
    try:
        report = label_folder(args.folder, datetime.now(timezone.utc))
    except DataError as error:
        print(json.dumps({'status': 'blocked', 'reason': str(error), 'model_ready': False}))
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
