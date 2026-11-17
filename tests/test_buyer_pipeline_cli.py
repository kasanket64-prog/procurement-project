"""Artificial CSV-to-CLI integration regressions; no real buyer records.

Run: python -m unittest discover -s tests -p test_buyer_pipeline_cli.py -v
"""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_buyer_snapshot_check import setup, snapshot
from test_buyer_receipts import receipt
from test_buyer_delay_labels import policy, review, signal

# Freeze only the subprocess clock so fixture approvals do not expire in CI.
CLI_RUNNER = """
import datetime
import runpy
import sys
from pathlib import Path
class FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        fixed = cls(2026, 11, 14, 12, tzinfo=datetime.timezone.utc)
        return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
datetime.datetime = FixedDateTime
script, folder = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
sys.argv = [script, folder]
runpy.run_path(script, run_name='__main__')
"""
TEMPLATES = ROOT / 'real-pilot/buyer-data-collection/csv-templates'
cases = []


def add(name, *, orders=None, receipts=None, reviews=None, signals=None, settings=None,
        rules=None, exits=(0,0,0), label='late', net='4'):
    cases.append(dict(name=name, orders=orders if orders is not None else [snapshot(original_promise_date='2026-11-10')],
                      receipts=receipts if receipts is not None else [receipt()],
                      reviews=reviews if reviews is not None else [review()], signals=signals or [],
                      settings=settings or setup(), rules=rules or policy(), exits=exits, label=label, net=net))


add('partial_overdue_confirmed')
add('full_on_time', receipts=[receipt(quantity='10')], reviews=[review(delivery_status='completed',complete_accepted_at='2026-11-05T00:00:00Z')],label='on_time',net='10')
late=receipt(quantity='10',event_at='2026-11-11T10:00:00Z',known_at='2026-11-11T11:00:00Z',captured_at='2026-11-12T00:00:00Z')
add('full_late',receipts=[late],reviews=[review(delivery_status='completed',complete_accepted_at=late['event_at'])],net='10')
add('open_overdue_confirmed',receipts=[],reviews=[review(delivery_status='open')],net='0')
add('missing_coverage',reviews=[review(coverage_confirmed='no',register_coverage_through='')],label='unknown')
early=review(reviewed_at='2026-11-09T12:00:00Z',known_at='2026-11-09T12:00:00Z',captured_at='2026-11-09T13:00:00Z',register_coverage_through='2026-11-09T00:00:00Z')
add('open_before_deadline',reviews=[early],label='pending')
add('rejected_not_accepted',receipts=[receipt(quantity='10',event_type='rejected')],net='0')
undo=receipt('undo',event_type='reversal',quantity='3',reverses_event_id='receipt-1',event_at='2026-11-09T00:00:00Z',known_at='2026-11-09T01:00:00Z',captured_at='2026-11-10T00:00:00Z')
add('partial_reversal',receipts=[receipt(quantity='10'),undo],net='7')
add('pre_deadline_cancel',signals=[signal()],reviews=[review(delivery_status='cancelled',exclusion_or_dispute='cancel-1')],label='cancelled')
cancel=signal(event_at='2026-11-11T00:00:00Z',known_at='2026-11-11T01:00:00Z',captured_at='2026-11-11T02:00:00Z')
add('post_deadline_cancel_preserves_late',signals=[cancel],reviews=[review(delivery_status='cancelled',exclusion_or_dispute='cancel-1')])
stock=signal('stock',signal_type='stock_commitment',event_at='2026-11-01T12:00:00Z',known_at='2026-11-01T13:00:00Z',captured_at='2026-11-01T14:00:00Z')
add('pre_release_enrichment',signals=[stock])
add('corrected_snapshot',orders=[snapshot(original_promise_date='2026-11-10'),snapshot('corrected',original_promise_date='2026-11-10',quantity='12',supersedes_id='snapshot-1')])
add('pending_approval',settings=dict(setup(),permission_status='pending'),exits=(2,2,2),label=None)
add('broken_snapshot_link',orders=[snapshot(original_promise_date='2026-11-10',supersedes_id='missing')],exits=(2,2,2),label=None)
add('invalid_receipt_unit',receipts=[receipt(unit='kg')],exits=(0,2,2),label=None)
add('excessive_reversal',receipts=[receipt(),dict(undo,quantity='5')],exits=(0,2,2),label=None)
add('unapproved_policy',rules=dict(policy(),approval_confirmed=False),exits=(0,0,2),label=None)
old_invalid=snapshot(original_promise_date='2026-11-10',quantity='0')
fixed=snapshot('fixed',original_promise_date='2026-11-10',supersedes_id='snapshot-1',captured_at='2026-11-04T09:00:00Z')
add('invalid_old_quantity_repaired',orders=[old_invalid,fixed])
add('invalid_active_quantity_blocked',orders=[snapshot(original_promise_date='2026-11-10'),dict(fixed,quantity='0')],exits=(2,2,2),label=None)
add('superseded_bad_provenance_blocked',orders=[dict(old_invalid,source_ref=''),fixed],exits=(2,2,2),label=None)
fork=dict(fixed,snapshot_id='fork')
add('competing_corrections_with_old_error_blocked',orders=[old_invalid,fixed,fork],exits=(2,2,2),label=None)
for name, value in [('utc_underflow', '0001-01-01T00:00:00+14:00'),
                    ('utc_overflow', '9999-12-31T23:59:59-14:00')]:
    add(name, orders=[snapshot(original_promise_date='2026-11-10', known_at=value)],
        exits=(2,2,2), label=None)


class BuyerPipelineCliTests(unittest.TestCase):
    def test_artificial_scenarios_through_all_three_cli_stages(self):
        commands = ['buyer_snapshot_check.py', 'buyer_receipts.py', 'buyer_delay_labels.py']
        for case in cases:
            with self.subTest(scenario=case['name']), tempfile.TemporaryDirectory(prefix='artificial-buyer-e2e-') as temp:
                folder = Path(temp)
                with (TEMPLATES / 'pilot_setup.csv').open(encoding='utf-8-sig', newline='') as stream:
                    settings = list(csv.DictReader(stream))
                for row in settings:
                    row['buyer_value'] = case['settings'][row['field']]
                tables = {'pilot_setup': settings, 'order_snapshots': case['orders'],
                          'receipt_events': case['receipts'], 'outcome_reviews': case['reviews'],
                          'decision_signals': case['signals']}
                for name, rows in tables.items():
                    with (TEMPLATES / f'{name}.csv').open(encoding='utf-8-sig', newline='') as stream:
                        fields = next(csv.reader(stream))
                    with (folder / f'{name}.csv').open('w', encoding='utf-8', newline='') as stream:
                        writer = csv.DictWriter(stream, fieldnames=fields)
                        writer.writeheader()
                        writer.writerows(rows)
                (folder / 'label_policy.json').write_text(json.dumps(case['rules']), encoding='utf-8')
                before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
                for command, expected in zip(commands, case['exits']):
                    with self.subTest(command=command):
                        completed = subprocess.run(
                            [sys.executable, '-c', CLI_RUNNER, str(ROOT / 'ml' / command), str(folder)],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
                        self.assertEqual(completed.returncode, expected, completed.stderr)
                        self.assertEqual(completed.stderr, '')
                        report = json.loads(completed.stdout)
                        self.assertIs(report['model_ready'], False)
                        self.assertNotIn('test-only-source', completed.stdout)
                        if expected == 2:
                            self.assertEqual(report['status'], 'blocked')
                        else:
                            self.assertIs(report['purchase_authorized'], False)
                            if command == 'buyer_receipts.py':
                                self.assertEqual(report['lines'][0]['net_accepted_quantity'], case['net'])
                            elif command == 'buyer_delay_labels.py':
                                row = report['lines'][0]
                                self.assertEqual(row['label'], case['label'])
                                self.assertIs(row['human_label_review_required'], True)
                                self.assertIsNone(row['label_known_at'])
                after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
                self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
