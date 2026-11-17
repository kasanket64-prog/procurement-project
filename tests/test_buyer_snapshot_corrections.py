"""Artificial append-only correction cases spanning all three buyer stages."""
import copy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from buyer_snapshot_check import check_snapshots, check_folder, TEMPLATES
from buyer_receipts import reconcile_receipts, reconcile_folder
from buyer_delay_labels import label_delays, label_folder
from real_procurement import DataError, timestamp
from test_buyer_snapshot_check import snapshot, setup, NOW
from test_buyer_receipts import receipt
from test_buyer_delay_labels import policy, review
import test_buyer_receipts as receipt_fixtures

BUSINESS_ERRORS = [dict(quantity='0'), dict(quantity='NaN'), dict(quantity=''),
                   dict(original_promise_date='bad-date'), dict(needed_by_date='bad-date'),
                   dict(unit_price='NaN'), dict(currency='usd'), dict(on_contract='maybe'),
                   dict(promise_basis='buyer_request_only'), dict(snapshot_status='retrospective_unverified'),
                   dict(decision_timezone='not-a-zone')]


def corrected_rows(**changes):
    return [snapshot(original_promise_date='2026-11-10', **changes),
            snapshot('fixed', original_promise_date='2026-11-10',supersedes_id='snapshot-1',
                     captured_at='2026-11-04T09:00:00Z')]


def stages(rows):
    return [lambda:check_snapshots(rows,setup(),NOW),
            lambda:reconcile_receipts(rows,[receipt()],setup(),NOW),
            lambda:label_delays(rows,[receipt()],[review()],[],setup(),policy(),NOW)]


class BuyerSnapshotCorrectionTests(unittest.TestCase):
    def test_representable_utc_boundaries_and_offsets_still_parse(self):
        for value, expected in [
            ('0001-01-01T00:00:00Z', '0001-01-01T00:00:00+00:00'),
            ('9999-12-31T23:59:59Z', '9999-12-31T23:59:59+00:00'),
            ('2026-11-02T15:30:00+05:30', '2026-11-02T10:00:00+00:00'),
        ]:
            with self.subTest(value=value):
                self.assertEqual(timestamp(value, 'test.time').isoformat(), expected)

    def test_unrepresentable_utc_snapshot_times_block_all_stages(self):
        for value in ('0001-01-01T00:00:00+14:00', '9999-12-31T23:59:59-14:00'):
            rows = [snapshot(original_promise_date='2026-11-10', known_at=value)]
            for index, stage in enumerate(stages(rows)):
                with self.subTest(value=value, stage=index), self.assertRaises(DataError):
                    stage()

    def test_invalid_superseded_business_values_are_repaired_across_stages(self):
        for changes in BUSINESS_ERRORS:
            original=snapshot(original_promise_date='2026-11-10');original.update(changes)
            rows=[original,corrected_rows()[1]]
            before=copy.deepcopy(rows)
            with self.subTest(changes=changes):
                preflight,receipts,labels=[stage() for stage in stages(list(reversed(rows)))]
                self.assertEqual(preflight['active_order_lines'],1)
                self.assertEqual(receipts['lines'][0]['ordered_quantity'],'10')
                self.assertEqual(receipts['lines'][0]['net_accepted_quantity'],'4')
                self.assertEqual(labels['lines'][0]['original_promise_date'],'2026-11-10')
                self.assertEqual(labels['lines'][0]['label'],'late')
                self.assertEqual(rows,before)

    def test_invalid_active_business_values_still_block_all_stages(self):
        for changes in BUSINESS_ERRORS:
            rows=corrected_rows();rows[1].update(changes)
            for index,stage in enumerate(stages(rows)):
                with self.subTest(changes=changes,stage=index),self.assertRaises(DataError):stage()

    def test_superseded_provenance_identity_timing_and_chain_checks_remain(self):
        for changes in [dict(source_ref=''),dict(reviewer_id=''),dict(data_kind='synthetic'),dict(pilot_id='other'),
                        dict(supplier_id=''),dict(product_id=''),dict(destination_id=''),dict(unit=''),
                        dict(known_at='2026-11-03T00:00:00Z'),dict(captured_at='2026-11-15T00:00:00Z')]:
            rows=corrected_rows(quantity='0');rows[0].update(changes)
            for index,stage in enumerate(stages(rows)):
                with self.subTest(changes=changes,stage=index),self.assertRaises(DataError):stage()
        rows=corrected_rows(quantity='0')
        rows.append(snapshot('competing',original_promise_date='2026-11-10',supersedes_id='snapshot-1',captured_at='2026-11-04T09:00:00Z'))
        for stage in stages(rows):
            with self.assertRaisesRegex(DataError,'competing corrections'):stage()

    def test_external_csv_history_is_read_only_through_all_stages(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);receipt_fixtures.BuyerReceiptTests().folder(folder,[receipt()])
            tables={'order_snapshots':corrected_rows(quantity='0'),'outcome_reviews':[review()],'decision_signals':[]}
            for name,rows in tables.items():
                with (TEMPLATES/f'{name}.csv').open(encoding='utf-8-sig',newline='') as stream:fields=next(csv.reader(stream))
                with (folder/f'{name}.csv').open('w',encoding='utf-8',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
            (folder/'label_policy.json').write_text(json.dumps(policy()),encoding='utf-8')
            before={path.name:path.read_bytes() for path in folder.iterdir()}
            self.assertEqual(check_folder(folder,NOW)['correction_rows'],1)
            self.assertEqual(reconcile_folder(folder,NOW)['lines'][0]['ordered_quantity'],'10')
            self.assertEqual(label_folder(folder,NOW)['lines'][0]['label'],'late')
            self.assertEqual(before,{path.name:path.read_bytes() for path in folder.iterdir()})


if __name__ == '__main__':
    unittest.main()
