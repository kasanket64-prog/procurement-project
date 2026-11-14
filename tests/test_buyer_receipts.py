"""Artificial receipt fixtures only; no buyer data or learned outcomes."""
import copy
import csv
from contextlib import redirect_stdout
from decimal import localcontext
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from buyer_receipts import main, reconcile_folder, reconcile_receipts
from buyer_snapshot_check import TEMPLATES, read_csv
from real_procurement import DataError
from test_buyer_snapshot_check import NOW, ROOT, setup, snapshot


def receipt(key='receipt-1', **changes):
    row = dict(receipt_event_id=key, order_line_id='test-line', destination_id='test-site',
               event_type='accepted', event_at='2026-11-05T00:00:00Z', quantity='4', unit='each',
               reverses_event_id='', pilot_id='test-pilot', data_kind='real', source_ref='test-only-receipt-source',
               known_at='2026-11-06T00:00:00Z', captured_at='2026-11-07T00:00:00Z', reviewer_id='test-reviewer')
    row.update(changes)
    return row


def later(key, **changes):
    return receipt(key, **dict(event_at='2026-11-09T00:00:00Z', known_at='2026-11-10T00:00:00Z',
                               captured_at='2026-11-11T00:00:00Z', **changes))


class BuyerReceiptTests(unittest.TestCase):
    def result(self, receipts, snapshots=None):
        return reconcile_receipts(snapshots or [snapshot()], receipts, setup(), NOW)

    def test_partial_acceptance_and_rejections_do_not_complete(self):
        result = self.result([receipt(), receipt('reject', event_type='rejected', quantity='6')])
        line = result['lines'][0]
        self.assertEqual((line['net_accepted_quantity'], line['rejected_quantity'], line['remaining_quantity']), ('4','6','6'))
        self.assertEqual(line['receipt_status'], 'partial')
        self.assertIsNone(line['ledger_complete_at'])
        self.assertFalse(result['model_ready'])
        self.assertFalse(result['coverage_confirmed'])

    def test_partial_deliveries_reach_full_quantity(self):
        line = self.result([receipt(), later('second', quantity='6')])['lines'][0]
        self.assertEqual(line['receipt_status'], 'quantity_met')
        self.assertEqual(line['remaining_quantity'], '0')
        self.assertEqual(line['ledger_complete_at'], '2026-11-09T00:00:00+00:00')

    def test_header_only_receipts_do_not_imply_ontime(self):
        result = self.result([])
        self.assertEqual(result['lines'][0]['receipt_status'], 'no_receipts')
        self.assertFalse(result['coverage_confirmed'])
        self.assertNotIn('label', result['lines'][0])

    def test_full_reversal_removes_completion(self):
        line = self.result([receipt(quantity='10'), later('undo', event_type='reversal',
                            quantity='10', reverses_event_id='receipt-1')])['lines'][0]
        self.assertEqual((line['net_accepted_quantity'],line['reversed_quantity']), ('0','10'))
        self.assertEqual(line['receipt_status'], 'not_accepted')
        self.assertIsNone(line['ledger_complete_at'])

    def test_multiple_partial_reversals_are_exact_and_capped(self):
        rows = [receipt(quantity='1'), later('undo-a', event_type='reversal', quantity='0.1', reverses_event_id='receipt-1'),
                later('undo-b', event_type='reversal', quantity='0.2', reverses_event_id='receipt-1')]
        with localcontext() as context:
            context.prec = 6
            line = self.result(rows)['lines'][0]
        self.assertEqual(line['net_accepted_quantity'], '0.7')
        self.assertEqual(line['reversed_quantity'], '0.3')
        with localcontext() as context:
            context.prec = 6
            large = self.result([receipt(quantity='999999999999999999.999999'),
                later('tiny-undo',event_type='reversal',quantity='0.000001',reverses_event_id='receipt-1')])['lines'][0]
        self.assertEqual(large['net_accepted_quantity'],'999999999999999999.999998')
        with self.assertRaisesRegex(DataError, 'cumulative reversal'):
            self.result(rows + [later('too-much', event_type='reversal',quantity='0.8',reverses_event_id='receipt-1')])

    def test_reacceptance_after_reversal_uses_latest_restored_completion(self):
        rows = [receipt(quantity='10'), receipt('undo', event_type='reversal', quantity='3', reverses_event_id='receipt-1',
                event_at='2026-11-07T00:00:00Z', known_at='2026-11-07T00:00:00Z', captured_at='2026-11-08T00:00:00Z'),
                later('replacement', quantity='3')]
        line = self.result(rows)['lines'][0]
        self.assertEqual(line['ledger_complete_at'], '2026-11-09T00:00:00+00:00')
        self.assertEqual(line['net_accepted_quantity'], '10')

    def test_same_instant_events_do_not_create_transient_completion(self):
        line = self.result([receipt(quantity='10'), receipt('undo', event_type='reversal', quantity='1',
                            reverses_event_id='receipt-1')])['lines'][0]
        self.assertEqual(line['net_accepted_quantity'], '9')
        self.assertIsNone(line['ledger_complete_at'])

    def test_event_order_and_inputs_are_preserved(self):
        rows = [receipt(quantity='10'), later('undo', event_type='reversal', quantity='2', reverses_event_id='receipt-1')]
        before = copy.deepcopy(rows)
        self.assertEqual(self.result(rows), self.result(list(reversed(rows))))
        self.assertEqual(rows, before)

    def test_accepted_excess_is_flagged_not_truncated(self):
        line = self.result([receipt(quantity='12')])['lines'][0]
        self.assertEqual(line['net_accepted_quantity'], '12')
        self.assertEqual(line['over_accepted_quantity'], '2')
        self.assertTrue(line['needs_quantity_review'])

    def test_active_corrected_snapshot_sets_original_quantity(self):
        rows = [snapshot(), snapshot('corrected', quantity='12', supersedes_id='snapshot-1')]
        line = self.result([receipt(quantity='10')], rows)['lines'][0]
        self.assertEqual(line['ordered_quantity'], '12')
        self.assertEqual(line['remaining_quantity'], '2')

    def test_lines_and_units_are_reconciled_separately(self):
        orders = [snapshot(), snapshot('other', order_line_id='other-line', unit='kg', quantity='2')]
        result = self.result([receipt(), receipt('kg', order_line_id='other-line', unit='kg',quantity='1')], orders)
        self.assertEqual(len(result['lines']), 2)
        self.assertEqual({line['unit']:line['remaining_quantity'] for line in result['lines']}, {'each':'6','kg':'1'})
        self.assertNotIn('total_accepted_quantity', result)

    def test_malformed_quantities_provenance_and_joins_block(self):
        for changes in [dict(quantity='0'), dict(quantity='-1'), dict(quantity='NaN'), dict(unit='kg'),
                        dict(destination_id='other'), dict(order_line_id='unknown'), dict(data_kind='synthetic'),
                        dict(pilot_id='other'), dict(source_ref=''), dict(event_type='returned'),
                        dict(reverses_event_id='unexpected')]:
            with self.subTest(changes=changes), self.assertRaises(DataError):
                self.result([receipt(**changes)])
        with self.assertRaisesRegex(DataError, 'duplicate ID'):
            self.result([receipt(), receipt()])

    def test_bad_times_block(self):
        for changes in [dict(event_at='2026-11-01T00:00:00Z'), dict(event_at='2026-11-07T00:00:00Z'),
                        dict(known_at='2026-11-08T00:00:00Z'), dict(captured_at='2026-11-15T00:00:00Z'),
                        dict(event_at='2026-11-05T00:00:00')]:
            with self.subTest(changes=changes), self.assertRaises(DataError):
                self.result([receipt(**changes)])

    def test_invalid_reversal_targets_and_timing_block(self):
        for target in ['missing', 'rejected', 'undo']:
            with self.subTest(target=target), self.assertRaises(DataError):
                self.result([receipt(), receipt('rejected',event_type='rejected'),
                             later('undo',event_type='reversal',quantity='1',reverses_event_id=target)])
        with self.assertRaisesRegex(DataError, 'cannot precede'):
            self.result([later('accepted'), receipt(event_type='reversal', quantity='1',reverses_event_id='accepted')])
        orders=[snapshot(),snapshot('other',order_line_id='other-line')]
        with self.assertRaisesRegex(DataError, 'same order line'):
            self.result([receipt(),later('undo',order_line_id='other-line',event_type='reversal',quantity='1',reverses_event_id='receipt-1')],orders)

    def test_invalid_snapshot_or_approval_blocks_before_receipts(self):
        with self.assertRaises(DataError):
            reconcile_receipts([snapshot()], [], dict(setup(),permission_status='withdrawn'), NOW)
        with self.assertRaises(DataError):
            self.result([], [snapshot(supersedes_id='missing')])

    def folder(self, path, receipts):
        settings=read_csv(TEMPLATES/'pilot_setup.csv',['field','buyer_value','instruction'])
        for row in settings: row['buyer_value']=setup()[row['field']]
        for name,rows in [('pilot_setup.csv',settings),('order_snapshots.csv',[snapshot()]),('receipt_events.csv',receipts)]:
            with (TEMPLATES/name).open(encoding='utf-8-sig',newline='') as stream: fields=next(csv.reader(stream))
            with (path/name).open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)

    def test_external_folder_roundtrip_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);self.folder(path,[receipt()])
            original={p.name:p.read_bytes() for p in path.iterdir()}
            self.assertEqual(reconcile_folder(path,NOW)['lines'][0]['net_accepted_quantity'],'4')
            output=io.StringIO()
            with patch('buyer_receipts.datetime') as clock, patch.object(sys,'argv',['buyer_receipts',str(path)]), redirect_stdout(output):
                clock.now.return_value=NOW
                self.assertEqual(main(),0)
            self.assertEqual(json.loads(output.getvalue())['lines'][0]['net_accepted_quantity'],'4')
            self.assertNotIn('test-only-receipt-source',output.getvalue())
            self.assertEqual(original,{p.name:p.read_bytes() for p in path.iterdir()})
            (path/'receipt_events.csv').unlink()
            with self.assertRaisesRegex(DataError,'cannot read'):reconcile_folder(path,NOW)

    def test_pending_setup_and_cli_failure_do_not_read_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)
            shutil.copy(TEMPLATES/'pilot_setup.csv',path/'pilot_setup.csv')
            (path/'receipt_events.csv').write_bytes(b'\xff\xff')
            result=subprocess.run([sys.executable,str(ROOT/'ml/buyer_receipts.py'),str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('approved permission',json.loads(result.stdout)['reason'])
            self.assertFalse(result.stderr)


if __name__ == '__main__':
    unittest.main()
