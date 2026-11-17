"""Artificial order history only; no buyer records or genuine acceptance."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from buyer_order_timeline import timeline, render_timeline
from buyer_delay_labels import load_pilot_evidence
from real_procurement import DataError
from test_buyer_snapshot_check import NOW, setup, snapshot
from test_buyer_receipts import receipt, later
from test_buyer_delay_labels import policy, review, signal
import test_buyer_readiness as readiness_fixtures


class OrderTimelineTests(unittest.TestCase):
    def result(self, snapshots=None, receipts=None, reviews=None, signals=None, key='test-line'):
        return timeline(snapshots or [snapshot(original_promise_date='2026-11-10')],
                        [receipt()] if receipts is None else receipts,
                        [review()] if reviews is None else reviews, signals or [], setup(), policy(), NOW, key)

    def test_partial_rejection_reversal_and_history_are_preserved_without_mutation(self):
        receipts = [receipt(), later('undo', event_type='reversal', quantity='2', reverses_event_id='receipt-1'),
                    receipt('reject', event_type='rejected', quantity='1')]
        original = snapshot(original_promise_date='2026-11-10', quantity='bad-original')
        fixed = snapshot('fixed', original_promise_date='2026-11-10', supersedes_id='snapshot-1',
                         captured_at='2026-11-04T09:00:00Z')
        snapshots = [fixed, original]
        before = copy.deepcopy((snapshots, receipts))
        report = self.result(snapshots, receipts)
        self.assertEqual((snapshots, receipts), before)
        events = {e['record_id']: e for e in report['events']}
        self.assertEqual(events['receipt-1']['kind'], 'receipt:accepted')
        self.assertEqual(events['reject']['kind'], 'receipt:rejected')
        self.assertEqual(events['undo']['reverses_event_id'], 'receipt-1')
        self.assertEqual(events['snapshot-1']['details']['quantity'], 'bad-original')
        self.assertTrue(events['snapshot-1']['superseded'])
        self.assertFalse(events['fixed']['superseded'])
        self.assertEqual(events['fixed']['supersedes_id'], 'snapshot-1')
        self.assertFalse(report['model_ready']); self.assertFalse(report['purchase_authorized'])
        self.assertEqual(report, self.result(list(reversed(snapshots)), list(reversed(receipts))))

    def test_review_and_signal_corrections_keep_both_versions_and_clocks(self):
        old = review()
        new = review('review-2', supersedes_id='review-1', reviewed_at='2026-11-13T01:00:00Z',
                     known_at='2026-11-13T02:00:00Z', captured_at='2026-11-13T03:00:00Z')
        first = signal(signal_type='disruption')
        correction = signal('signal-2', signal_type='disruption', supersedes_id='cancel-1',
                            known_at='2026-11-09T01:00:00Z', captured_at='2026-11-09T02:00:00Z')
        events = {e['record_id']: e for e in self.result(reviews=[new, old], signals=[correction, first])['events']}
        self.assertTrue(events['review-1']['superseded']); self.assertTrue(events['cancel-1']['superseded'])
        self.assertEqual(events['review-2']['event_at'], new['reviewed_at'])
        self.assertEqual(events['signal-2']['known_at'], correction['known_at'])
        self.assertEqual(events['signal-2']['captured_at'], correction['captured_at'])

    def test_invalid_lineage_units_future_events_and_unknown_line_block(self):
        for rows in ([receipt(unit='wrong')], [later('undo', event_type='reversal', reverses_event_id='missing')],
                     [receipt(known_at='2027-01-01T00:00:00Z')]):
            with self.subTest(rows=rows), self.assertRaises(DataError): self.result(receipts=rows)
        with self.assertRaises(DataError):
            self.result(snapshots=[snapshot(supersedes_id='missing')])
        with self.assertRaisesRegex(DataError, 'no validated matching line'):
            self.result(key='unknown-private-line')

    def test_html_escapes_source_content_and_contains_no_external_assets(self):
        report = self.result(snapshots=[snapshot(original_promise_date='2026-11-10'),
                                       snapshot('second', order_line_id='other-private-line', source_ref='other-private-source')],
                             receipts=[receipt(source_ref='<script>private</script>')])
        html = render_timeline(report)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;private&lt;/script&gt;', html)
        self.assertIn("default-src 'none'", html)
        self.assertIn('Promise-event changes are not supported', html)
        self.assertNotIn('other-private', json.dumps(report) + html)

    def test_external_folder_is_unchanged_and_cli_blocks_without_echoing_selected_key(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); readiness_fixtures.ReadinessTests().folder(folder)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            report = timeline(*load_pilot_evidence(folder, NOW), NOW, 'test-line')
            self.assertEqual(report['status'], 'timeline_available')
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})
            (folder / 'receipt_events.csv').unlink()
            script = Path(__file__).resolve().parents[1] / 'ml/buyer_order_timeline.py'
            for fmt in ('json', 'html'):
                result = subprocess.run([sys.executable, str(script), temp, 'unknown-private-line', '--format', fmt],
                                        capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, '')
                self.assertNotIn('unknown-private-line', result.stdout)
                if fmt == 'json': self.assertEqual(json.loads(result.stdout)['events'], [])
                else: self.assertIn('Blocked:', result.stdout)


if __name__ == '__main__': unittest.main()
