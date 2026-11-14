"""Artificial fixtures; no buyer records, approval or real delivery validation."""
import copy
import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from buyer_delay_labels import deadline, label_delays, label_folder, main
from buyer_snapshot_check import TEMPLATES
from real_procurement import DataError
import test_buyer_receipts as receipt_fixtures
from test_buyer_receipts import receipt
from test_buyer_snapshot_check import NOW, setup, snapshot


def policy():
    return dict(schema_version='1.0', policy_id='test-policy',pilot_id='test-pilot',
                target_version='test-only',approval_ref='test-only',approval_confirmed=True,
                approved_at='2026-11-02T00:00:00Z',grace_days=0,
                target_rule='net_accepted_at_original_date_end',
                cancellation_rule='pre_deadline_cancelled_post_deadline_preserve_outcome')


def review(key='review-1', **changes):
    row=dict(review_id=key,order_line_id='test-line',target_version='test-only',delivery_status='partial',
             label='pending',complete_accepted_at='',register_coverage_through='2026-11-11T00:00:00Z',
             coverage_confirmed='yes',reviewed_at='2026-11-12T12:00:00Z',exclusion_or_dispute='',supersedes_id='',
             pilot_id='test-pilot',data_kind='real',source_ref='test-only-coverage-source',
             known_at='2026-11-12T12:00:00Z',captured_at='2026-11-13T00:00:00Z',reviewer_id='test-only')
    row.update(changes)
    return row


def signal(key='cancel-1', **changes):
    row=dict(signal_id=key,order_line_id='test-line',signal_type='cancellation',event_at='2026-11-08T00:00:00Z',
             value_number='',value_text='test-only reason',value_unit='',valid_until='',verification='buyer_verified',
             supersedes_id='',pilot_id='test-pilot',data_kind='real',source_ref='test-only-signal-source',
             known_at='2026-11-08T01:00:00Z',captured_at='2026-11-08T02:00:00Z',reviewer_id='test-reviewer')
    row.update(changes)
    return row


class BuyerDelayLabelTests(unittest.TestCase):
    def result(self, receipts=None, reviews=None, signals=None, order=None, rules=None):
        return label_delays([order or snapshot(original_promise_date='2026-11-10')],
                            [receipt()] if receipts is None else receipts,
                            [review()] if reviews is None else reviews,signals or [],setup(),rules or policy(),NOW)

    def label(self, **kwargs):
        return self.result(**kwargs)['lines'][0]

    def test_on_time_full_acceptance_requires_confirmed_deadline_coverage(self):
        receipts=[receipt(quantity='10')]
        reviews=[review(delivery_status='completed',complete_accepted_at='2026-11-05T00:00:00Z')]
        result=self.result(receipts=receipts,reviews=reviews)
        self.assertEqual(result['lines'][0]['label'],'on_time')
        self.assertFalse(result['model_ready'])
        self.assertFalse(result['purchase_authorized'])
        self.assertTrue(result['lines'][0]['human_label_review_required'])
        self.assertIsNone(result['lines'][0]['label_known_at'])
        self.assertEqual(result['lines'][0]['label_evidence_available_at'],'2026-11-12T12:00:00+00:00')
        self.assertEqual(self.label(receipts=receipts,reviews=[dict(reviews[0],coverage_confirmed='no')])['label'],'unknown')

    def test_completed_after_promise_is_late(self):
        receipts=[receipt(quantity='10',event_at='2026-11-11T10:00:00Z',known_at='2026-11-11T11:00:00Z',captured_at='2026-11-12T00:00:00Z')]
        self.assertEqual(self.label(receipts=receipts,reviews=[review(delivery_status='completed',complete_accepted_at='2026-11-11T10:00:00Z')])['label'],'late')

    def test_partial_and_open_overdue_require_coverage(self):
        self.assertEqual(self.label()['label'],'late')
        self.assertEqual(self.label(receipts=[],reviews=[review(delivery_status='open')])['label'],'late')
        for status in ('no','unknown'):
            self.assertEqual(self.label(reviews=[review(coverage_confirmed=status,register_coverage_through='')])['label'],'unknown')
        self.assertEqual(self.label(reviews=[review(register_coverage_through='2026-11-10T23:59:59Z')])['label'],'unknown')

    def test_before_deadline_is_pending_even_if_early_quantity_met(self):
        early=review(delivery_status='completed',complete_accepted_at='2026-11-05T00:00:00Z',
                     reviewed_at='2026-11-09T12:00:00Z',known_at='2026-11-09T12:00:00Z',
                     register_coverage_through='2026-11-09T00:00:00Z')
        self.assertEqual(self.label(receipts=[receipt(quantity='10')],reviews=[early])['label'],'pending')

    def test_no_review_is_unknown_not_success(self):
        self.assertEqual(self.label(reviews=[])['reason'],'no_outcome_review')

    def test_rejected_quantity_does_not_make_order_ontime(self):
        self.assertEqual(self.label(receipts=[receipt(quantity='10',event_type='rejected')])['label'],'late')

    def test_reversal_before_deadline_removes_acceptance(self):
        rows=[receipt(quantity='10'),receipt('undo',event_type='reversal',quantity='1',reverses_event_id='receipt-1',
              event_at='2026-11-09T00:00:00Z',known_at='2026-11-09T01:00:00Z',captured_at='2026-11-10T00:00:00Z')]
        self.assertEqual(self.label(receipts=rows)['label'],'late')

    def test_return_after_deadline_does_not_rewrite_original_date_balance(self):
        rows=[receipt(quantity='10'),receipt('undo',event_type='reversal',quantity='1',reverses_event_id='receipt-1',
              event_at='2026-11-11T00:00:00Z',known_at='2026-11-11T01:00:00Z',captured_at='2026-11-11T02:00:00Z')]
        self.assertEqual(self.label(receipts=rows)['label'],'on_time')

    def test_predeadline_cancellation_is_not_binary_success(self):
        self.assertEqual(self.label(signals=[signal()],reviews=[review(delivery_status='cancelled',exclusion_or_dispute='cancel-1')])['label'],'cancelled')

    def test_postdeadline_cancellation_preserves_proven_late_or_ontime(self):
        cancellation=signal(event_at='2026-11-11T00:00:00Z',known_at='2026-11-11T01:00:00Z',captured_at='2026-11-11T02:00:00Z')
        reviews=[review(delivery_status='cancelled',exclusion_or_dispute='cancel-1')]
        self.assertEqual(self.label(signals=[cancellation],reviews=reviews)['label'],'late')
        self.assertEqual(self.label(receipts=[receipt(quantity='10')],signals=[cancellation],reviews=reviews)['label'],'on_time')
        self.assertEqual(self.label(signals=[cancellation],reviews=[dict(reviews[0],coverage_confirmed='no')])['label'],'unknown')

    def test_missing_unverified_unlinked_or_conflicting_cancellation_is_unknown(self):
        cancelled=review(delivery_status='cancelled',exclusion_or_dispute='cancel-1')
        for signals,reviews in [([], [cancelled]),([signal(verification='supplier_claim')],[cancelled]),
                                ([signal()],[dict(cancelled,exclusion_or_dispute='')]),([signal()],[review()]),
                                ([signal(),signal('cancel-2',event_at='2026-11-09T00:00:00Z',known_at='2026-11-09T01:00:00Z',captured_at='2026-11-09T02:00:00Z')],[cancelled])]:
            with self.subTest(signals=len(signals)):
                self.assertEqual(self.label(signals=signals,reviews=reviews)['label'],'unknown')

    def test_future_known_receipts_and_signals_cannot_change_earlier_review(self):
        before=self.result()
        future=receipt('future',quantity='6',event_at='2026-11-13T00:00:00Z',known_at='2026-11-13T01:00:00Z',captured_at='2026-11-13T02:00:00Z')
        cancellation=signal(event_at='2026-11-13T00:00:00Z',known_at='2026-11-13T01:00:00Z',captured_at='2026-11-13T02:00:00Z')
        self.assertEqual(before,self.result(receipts=[receipt(),future],signals=[cancellation]))
        unrelated=signal('stock',signal_type='stock_commitment',captured_at='2026-11-13T02:00:00Z')
        self.assertEqual(before,self.result(signals=[unrelated]))

    def test_future_signal_correction_does_not_hide_past_version(self):
        original=signal()
        corrected=signal('cancel-2',supersedes_id='cancel-1',event_at='2026-11-13T00:00:00Z',known_at='2026-11-13T01:00:00Z',captured_at='2026-11-13T02:00:00Z')
        row=review(delivery_status='cancelled',exclusion_or_dispute='cancel-1')
        self.assertEqual(self.result(signals=[original],reviews=[row]),self.result(signals=[corrected,original],reviews=[row]))

    def test_original_promise_ignores_buyer_requested_date(self):
        self.assertEqual(self.result(),self.result(order=snapshot(original_promise_date='2026-11-10',needed_by_date='2026-12-01')))

    def test_policy_must_be_explicit_approved_and_bound_to_pilot(self):
        blank=json.loads((TEMPLATES.parent/'label_policy_template.json').read_text(encoding='utf-8'))
        self.assertFalse(blank['approval_confirmed'])
        with self.assertRaises(DataError):self.result(rules=blank)
        for changes in [dict(approval_confirmed=False),dict(grace_days=1),dict(grace_days=False),
                        dict(pilot_id='other'),dict(target_version='other'),dict(approval_ref=''),
                        dict(cancellation_rule='guess'),dict(approved_at='2026-11-15T00:00:00Z')]:
            with self.subTest(changes=changes),self.assertRaises(DataError):self.result(rules=dict(policy(),**changes))
        self.assertEqual(self.label(rules=dict(policy(),approved_at='2026-11-13T00:00:00Z'))['label'],'unknown')

    def test_invalid_reviews_and_signal_provenance_block(self):
        for changes in [dict(coverage_confirmed='yes',register_coverage_through=''),
                        dict(register_coverage_through='2026-11-13T00:00:00Z'),dict(reviewer_id='unapproved'),
                        dict(target_version='other'),dict(data_kind='synthetic'),dict(known_at='2026-11-11T00:00:00Z')]:
            with self.subTest(changes=changes),self.assertRaises(DataError):self.result(reviews=[review(**changes)])
        with self.assertRaises(DataError):self.result(signals=[signal(data_kind='synthetic')])
        with self.assertRaises(DataError):self.result(signals=[signal(value_text='')])

    def test_scope_dispute_excess_and_conflicting_completion_are_unknown(self):
        self.assertEqual(self.label(signals=[signal(signal_type='quantity_change')])['label'],'unknown')
        self.assertEqual(self.label(reviews=[review(delivery_status='disputed')])['label'],'unknown')
        self.assertEqual(self.label(receipts=[receipt(quantity='12')])['label'],'unknown')
        self.assertEqual(self.label(reviews=[review(delivery_status='completed',complete_accepted_at='2026-11-05T00:00:00Z')])['label'],'unknown')
        self.assertEqual(self.label(receipts=[receipt(quantity='10')])['label'],'unknown')

    def test_conflicting_existing_label_is_not_overwritten(self):
        result=self.label(reviews=[review(label='on_time')])
        self.assertEqual(result['label'],'unknown')
        self.assertEqual(result['candidate_label'],'late')
        self.assertEqual(result['calculation_reason'],'confirmed_original_deadline_balance')

    def test_weekly_reviews_latest_wins_but_same_time_ambiguity_blocks(self):
        older=review('older',reviewed_at='2026-11-09T12:00:00Z',known_at='2026-11-09T12:00:00Z',
                     captured_at='2026-11-10T00:00:00Z',register_coverage_through='2026-11-09T00:00:00Z')
        self.assertEqual(self.label(reviews=[review(),older])['label'],'late')
        with self.assertRaisesRegex(DataError,'competing active reviews'):self.result(reviews=[review(),review('other')])

    def test_review_and_signal_corrections_reject_broken_competing_or_cyclic_links(self):
        for rows in [[review(supersedes_id='missing')],[review(),review('b',supersedes_id='review-1'),review('c',supersedes_id='review-1')],
                     [review(supersedes_id='b'),review('b',supersedes_id='review-1')]]:
            with self.subTest(count=len(rows)),self.assertRaises(DataError):self.result(reviews=rows)
        self.assertEqual(self.label(reviews=[review(),review('fixed',supersedes_id='review-1')])['label'],'late')
        with self.assertRaises(DataError):self.result(signals=[signal(supersedes_id='missing')])

    def test_timezone_deadline_is_exclusive_and_handles_dst(self):
        self.assertEqual(deadline(snapshot(original_promise_date='2026-11-10',decision_timezone='Asia/Kolkata')).isoformat(),'2026-11-10T18:30:00+00:00')
        self.assertEqual(deadline(snapshot(original_promise_date='2026-03-08',decision_timezone='America/New_York')).isoformat(),'2026-03-09T04:00:00+00:00')
        with self.assertRaises(DataError):deadline(snapshot(original_promise_date='2011-12-30',decision_timezone='Pacific/Apia'))
        boundary=receipt(quantity='10',event_at='2026-11-11T00:00:00Z',known_at='2026-11-11T01:00:00Z',captured_at='2026-11-11T02:00:00Z')
        self.assertEqual(self.label(receipts=[boundary],reviews=[review(delivery_status='completed',complete_accepted_at=boundary['event_at'])])['label'],'late')
        inside=dict(boundary,event_at='2026-11-10T23:59:59.999999Z')
        self.assertEqual(self.label(receipts=[inside],reviews=[review(delivery_status='completed',complete_accepted_at=inside['event_at'])])['label'],'on_time')
        india=dict(boundary,event_at='2026-11-10T19:00:00Z')
        result=label_delays([snapshot(original_promise_date='2026-11-10',decision_timezone='Asia/Kolkata')],
                            [india],[review(delivery_status='completed',complete_accepted_at=india['event_at'])],[],
                            dict(setup(),timezone='Asia/Kolkata'),policy(),NOW)
        self.assertEqual(result['lines'][0]['label'],'late')
        with self.assertRaisesRegex(DataError,'precedes order placement'):
            self.result(order=snapshot(original_promise_date='2026-11-01'))

    def test_inputs_and_csv_files_remain_unchanged_and_cli_is_json(self):
        rows=[receipt()];before=copy.deepcopy(rows)
        self.result(receipts=rows)
        self.assertEqual(rows,before)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);receipt_fixtures.BuyerReceiptTests().folder(folder,rows)
            for name,items in [('outcome_reviews',[review()]),('decision_signals',[])]:
                with (TEMPLATES/f'{name}.csv').open(encoding='utf-8-sig',newline='') as stream:headers=next(csv.reader(stream))
                with (folder/f'{name}.csv').open('w',encoding='utf-8',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=headers);writer.writeheader();writer.writerows(items)
            with (folder/'order_snapshots.csv').open(encoding='utf-8-sig',newline='') as stream:headers=next(csv.reader(stream))
            with (folder/'order_snapshots.csv').open('w',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=headers);writer.writeheader();writer.writerow(snapshot(original_promise_date='2026-11-10'))
            (folder/'label_policy.json').write_text(json.dumps(policy()),encoding='utf-8')
            original={p.name:p.read_bytes() for p in folder.iterdir()}
            self.assertEqual(label_folder(folder,NOW)['lines'][0]['label'],'late')
            output=io.StringIO()
            with patch('buyer_delay_labels.datetime') as clock,patch.object(sys,'argv',['buyer_delay_labels',str(folder)]),redirect_stdout(output):
                # Keep the actual datetime type for the calendar constructor.
                from datetime import datetime
                clock.now.return_value=NOW;clock.combine.side_effect=datetime.combine
                self.assertEqual(main(),0)
            self.assertEqual(json.loads(output.getvalue())['label_counts'],{'late':1})
            self.assertNotIn('test-only-coverage-source',output.getvalue())
            self.assertEqual(original,{p.name:p.read_bytes() for p in folder.iterdir()})
            (folder/'label_policy.json').write_text('{broken',encoding='utf-8')
            with self.assertRaisesRegex(DataError,'valid UTF-8 JSON'):label_folder(folder,NOW)
            failure=io.StringIO()
            with patch('buyer_delay_labels.datetime') as clock,patch.object(sys,'argv',['buyer_delay_labels',str(folder)]),redirect_stdout(failure):
                clock.now.return_value=NOW
                self.assertEqual(main(),2)
            self.assertEqual(json.loads(failure.getvalue())['status'],'blocked')


if __name__ == '__main__':
    unittest.main()
