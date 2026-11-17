"""Artificial readiness fixtures; no buyer records or genuine approvals."""
import csv
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from buyer_readiness import readiness, render_html, main
from buyer_snapshot_check import TEMPLATES
from real_procurement import DataError
import test_buyer_receipts as receipts
import test_buyer_delay_labels as labels
from test_buyer_snapshot_check import NOW, snapshot


class ReadinessTests(unittest.TestCase):
    def test_successful_cli_html_and_json_remain_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            self.folder(folder)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            for fmt in ('html', 'json'):
                output = io.StringIO()
                with self.subTest(format=fmt), patch('buyer_readiness.datetime') as clock, \
                     patch.object(sys, 'argv', ['buyer_readiness', temp, '--format', fmt]), redirect_stdout(output):
                    clock.now.return_value = NOW
                    self.assertEqual(main(), 0)
                if fmt == 'json':
                    report = json.loads(output.getvalue())
                    self.assertEqual(report['status'], 'checks_complete')
                    self.assertFalse(report['model_ready'])
                    self.assertFalse(report['purchase_authorized'])
                else:
                    self.assertIn('Checks passed', output.getvalue())
                self.assertNotIn('test-line', output.getvalue())
                self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def folder(self, folder):
        receipts.BuyerReceiptTests().folder(folder, [receipts.receipt()])
        for name, rows in [('order_snapshots', [snapshot(original_promise_date='2026-11-10')]),
                           ('outcome_reviews', [labels.review()]), ('decision_signals', [])]:
            with (TEMPLATES / f'{name}.csv').open(encoding='utf-8-sig', newline='') as stream:
                fields = next(csv.reader(stream))
            with (folder / f'{name}.csv').open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
        (folder / 'label_policy.json').write_text(json.dumps(labels.policy()), encoding='utf-8')

    def test_complete_pipeline_preserves_inputs_and_only_returns_aggregates(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); self.folder(folder)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            report = readiness(folder, NOW)
            self.assertEqual([s['status'] for s in report['stages']], ['passed'] * 3)
            self.assertEqual(report['stages'][2]['summary']['label_counts'], {'late': 1})
            self.assertFalse(report['model_ready']); self.assertFalse(report['purchase_authorized'])
            self.assertTrue(report['human_review_required'])
            for private in ('test-line', 'test-only-coverage-source', str(folder)):
                self.assertNotIn(private, json.dumps(report))
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_blocked_stage_skips_later_checks(self):
        with patch('buyer_readiness.check_folder', side_effect=DataError('blocked input')), \
             patch('buyer_readiness.reconcile_folder') as receipt_check, patch('buyer_readiness.label_folder') as label_check:
            report = readiness('unused', NOW)
            self.assertEqual([s['status'] for s in report['stages']], ['blocked', 'skipped', 'skipped'])
            receipt_check.assert_not_called(); label_check.assert_not_called()

    def test_missing_receipts_and_pending_policy_block_at_correct_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); self.folder(folder)
            receipt_bytes = (folder / 'receipt_events.csv').read_bytes()
            (folder / 'receipt_events.csv').unlink()
            self.assertEqual([s['status'] for s in readiness(folder, NOW)['stages']], ['passed', 'blocked', 'skipped'])
            (folder / 'receipt_events.csv').write_bytes(receipt_bytes)
            rules = labels.policy(); rules['approval_confirmed'] = False
            (folder / 'label_policy.json').write_text(json.dumps(rules))
            self.assertEqual([s['status'] for s in readiness(folder, NOW)['stages']], ['passed', 'passed', 'blocked'])

    def test_unknown_labels_are_not_training_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); self.folder(folder)
            with (folder / 'outcome_reviews.csv').open(encoding='utf-8') as stream:
                header = stream.readline()
            (folder / 'outcome_reviews.csv').write_text(header)
            report = readiness(folder, NOW)
            self.assertEqual(report['stages'][2]['summary']['label_counts'], {'unknown': 1})
            self.assertFalse(report['model_ready'])
            self.assertIn('human review required', render_html(report))
            self.assertIn('Unknown: 1', render_html(report))
            self.assertNotIn('{&quot;unknown&quot;', render_html(report))

    def test_html_escapes_error_content_and_disables_external_assets(self):
        with patch('buyer_readiness.check_folder', side_effect=DataError('<script>alert("buyer")</script>')):
            html = render_html(readiness('unused', NOW))
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn("default-src 'none'", html)
        self.assertIn('SKIPPED', html)

    def test_cli_reports_blocked_html_and_json_without_traceback(self):
        script = Path(__file__).resolve().parents[1] / 'ml/buyer_readiness.py'
        with tempfile.TemporaryDirectory() as temp:
            for fmt in ('html', 'json'):
                result = subprocess.run([sys.executable, str(script), temp, '--format', fmt], capture_output=True, encoding='utf-8')
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, '')
                if fmt == 'json': self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
                else: self.assertIn('Input checks blocked', result.stdout)


if __name__ == '__main__':
    unittest.main()
