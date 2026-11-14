"""Artificial fixtures only; no buyer records are collected or persisted."""
import copy
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ml'))
from buyer_snapshot_check import TEMPLATES, check_folder, check_snapshots, read_csv
from real_procurement import DataError

NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)


def setup():
    rows = read_csv(TEMPLATES / 'pilot_setup.csv', ['field', 'buyer_value', 'instruction'])
    result = {row['field']: 'test-only' for row in rows}
    result.update(pilot_id='test-pilot', data_kind='real', permission_status='approved',
                  timezone='UTC', valid_from='2026-11-01T00:00:00Z', valid_until='2026-12-01T00:00:00Z')
    return result


def snapshot(key='snapshot-1', **changes):
    with (TEMPLATES / 'order_snapshots.csv').open(encoding='utf-8-sig', newline='') as stream:
        fields = next(csv.reader(stream))
    result = dict.fromkeys(fields, '')
    result.update(snapshot_id=key, order_line_id='test-line', supplier_id='test-supplier',
                  product_id='test-product', destination_id='test-site',
                  decision_at='2026-11-02T10:00:00Z', order_placed_at='2026-11-02T10:00:00Z',
                  original_promise_date='2026-11-20', promise_basis='supplier_quotation',
                  decision_timezone='UTC', quantity='10', unit='each', snapshot_status='verified_as_of',
                  pilot_id='test-pilot', data_kind='real', source_ref='test-only-source',
                  known_at='2026-11-02T09:00:00Z', captured_at='2026-11-03T09:00:00Z', reviewer_id='test-reviewer')
    result.update(changes)
    return result


class BuyerSnapshotCheckTests(unittest.TestCase):
    def test_valid_chain_counts_one_line_and_does_not_mutate(self):
        rows = [snapshot(), snapshot('snapshot-2', supersedes_id='snapshot-1', quantity='12',
                                     captured_at='2026-11-04T09:00:00Z')]
        original = copy.deepcopy(rows)
        report = check_snapshots(list(reversed(rows)), setup(), NOW)
        self.assertEqual((report['snapshot_rows'], report['active_order_lines'], report['correction_rows']), (2, 1, 1))
        self.assertFalse(report['model_ready'])
        self.assertFalse(report['purchase_authorized'])
        self.assertEqual(rows, original)

    def test_pending_expired_future_and_wrong_kind_approval_block(self):
        for changes in [dict(permission_status='pending'), dict(data_kind='synthetic'),
                        dict(valid_until=NOW.isoformat()), dict(valid_from='2026-11-15T00:00:00Z'),
                        dict(approval_ref=''), dict(permitted_use='')]:
            with self.subTest(changes=changes), self.assertRaises(DataError):
                check_snapshots([snapshot()], dict(setup(), **changes), NOW)

    def test_wrong_pilot_synthetic_and_unverified_snapshots_block(self):
        for changes in [dict(pilot_id='other'), dict(data_kind='synthetic'),
                        dict(snapshot_status='retrospective_unverified'), dict(promise_basis='buyer_request_only')]:
            with self.subTest(changes=changes), self.assertRaises(DataError):
                check_snapshots([snapshot(**changes)], setup(), NOW)

    def test_invalid_fields_are_reported_without_values(self):
        for changes, field in [({'quantity':'0'}, 'quantity'), ({'quantity':'NaN'}, 'quantity'),
                               ({'original_promise_date':'20261120'}, 'original_promise_date'),
                               ({'original_promise_date':'2026-02-30'}, 'original_promise_date'),
                               ({'unit_price':'1','currency':''}, 'currency'),
                               ({'currency':'usd'}, 'currency'), ({'supplier_id':''}, 'supplier_id'),
                               ({'snapshot_id':' padded '}, 'snapshot_id')]:
            with self.subTest(changes=changes), self.assertRaisesRegex(DataError, field):
                check_snapshots([snapshot(**changes)], setup(), NOW)

    def test_invalid_times_and_site_zone_block(self):
        for changes in [dict(known_at='2026-11-03T00:00:00Z'), dict(decision_at='2026-11-02T11:00:00Z'),
                        dict(captured_at='2026-11-15T00:00:00Z'), dict(captured_at='2026-10-31T00:00:00Z'),
                        dict(decision_at='2026-11-02T10:00:00'), dict(decision_timezone='Europe/London')]:
            with self.subTest(changes=changes), self.assertRaises(DataError):
                check_snapshots([snapshot(**changes)], setup(), NOW)

    def test_duplicate_missing_cross_line_and_competing_links_block(self):
        batches = [[snapshot(), snapshot()],
                   [snapshot(supersedes_id='missing')],
                   [snapshot(), snapshot('b', order_line_id='other', supersedes_id='snapshot-1')],
                   [snapshot(), snapshot('b', supersedes_id='snapshot-1'), snapshot('c', supersedes_id='snapshot-1')],
                   [snapshot(), snapshot('b')],
                   [snapshot(), snapshot('b', supersedes_id='snapshot-1', decision_at='2026-11-02T11:00:00Z',
                                         order_placed_at='2026-11-02T11:00:00Z')]]
        for rows in batches:
            with self.subTest(rows=len(rows)), self.assertRaises(DataError):
                check_snapshots(rows, setup(), NOW)

    def test_cycles_disconnected_chains_and_earlier_corrections_block(self):
        batches = [[snapshot(supersedes_id='snapshot-1')],
                   [snapshot(supersedes_id='b'), snapshot('b', supersedes_id='snapshot-1')],
                   [snapshot(), snapshot('b', supersedes_id='c'), snapshot('c', supersedes_id='b')],
                   [snapshot(), snapshot('b', supersedes_id='snapshot-1', captured_at='2026-11-02T12:00:00Z')]]
        for rows in batches:
            with self.subTest(rows=len(rows)), self.assertRaises(DataError):
                check_snapshots(rows, setup(), NOW)

    def write_folder(self, folder):
        shutil.copy(TEMPLATES / 'pilot_setup.csv', folder / 'pilot_setup.csv')
        shutil.copy(TEMPLATES / 'order_snapshots.csv', folder / 'order_snapshots.csv')

    def test_blank_setup_blocks_before_order_data_is_read(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.write_folder(folder)
            (folder / 'order_snapshots.csv').write_bytes(b'\xff\xff')
            with self.assertRaisesRegex(DataError, 'approved permission'):
                check_folder(folder, NOW)

    def test_folder_rejects_repository_and_bad_headers_or_duplicate_setup_fields(self):
        with self.assertRaisesRegex(DataError, 'outside the repository'):
            check_folder(TEMPLATES, NOW)
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.write_folder(folder)
            with (folder / 'pilot_setup.csv').open('a', encoding='utf-8') as stream:
                stream.write('pilot_id,test,duplicate\n')
            with self.assertRaisesRegex(DataError, 'duplicate'):
                check_folder(folder, NOW)
            (folder / 'pilot_setup.csv').write_text('field,field,instruction\n', encoding='utf-8')
            with self.assertRaisesRegex(DataError, 'headers'):
                check_folder(folder, NOW)

    def test_valid_external_csv_round_trip_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            settings = read_csv(TEMPLATES / 'pilot_setup.csv', ['field', 'buyer_value', 'instruction'])
            for row in settings:
                row['buyer_value'] = setup()[row['field']]
            for filename, rows in [('pilot_setup.csv', settings), ('order_snapshots.csv', [snapshot()])]:
                with (folder / filename).open('w', encoding='utf-8', newline='') as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            before = {p.name:p.read_bytes() for p in folder.iterdir()}
            self.assertEqual(check_folder(folder, NOW)['active_order_lines'], 1)
            self.assertEqual(before, {p.name:p.read_bytes() for p in folder.iterdir()})

    def test_cli_blocked_output_does_not_expose_input_or_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.write_folder(folder)
            result = subprocess.run([sys.executable, str(ROOT/'ml/buyer_snapshot_check.py'), str(folder)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
            self.assertFalse(result.stderr)
            self.assertNotIn(str(folder), result.stdout)


if __name__ == '__main__':
    unittest.main()
