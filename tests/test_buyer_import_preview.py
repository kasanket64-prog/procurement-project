"""Artificial fixed-schema preview checks; no buyer approvals or records."""
import csv
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from buyer_import_preview import preview, render_preview
from real_procurement import DataError
import test_buyer_readiness as readiness_tests
from test_buyer_snapshot_check import NOW


class ImportPreviewTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for the workspace preview contract check')
    def test_generated_source_previews_are_accepted_by_workspace(self):
        script = '''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8'),context=vm.createContext({});
vm.runInContext(source.slice(source.indexOf('function parseReadiness('),source.indexOf('function renderReadiness(')),context);
for(const report of JSON.parse(fs.readFileSync(0,'utf8')))
  assert.equal(JSON.stringify(context.parseReadiness(JSON.stringify(report))),JSON.stringify(report));
'''
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); readiness_tests.ReadinessTests().folder(folder)
            reports = [preview(folder, NOW)]
            path = folder / 'decision_signals.csv'
            path.write_text('invalid-header\n')
            reports.append(preview(folder, NOW))
            path.unlink()
            reports.append(preview(folder, NOW))
            (folder / 'pilot_setup.csv').unlink()
            reports.append(preview(folder, NOW))
            self.assertEqual(reports[-1]['source_preview'], [])
            template = Path(__file__).resolve().parents[1] / 'ml/procurement_platform_template.html'
            result = subprocess.run([shutil.which('node'), '-e', script, str(template)],
                                    input=json.dumps(reports), capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_valid_schema_and_pipeline_are_read_only_and_omit_private_values(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); readiness_tests.ReadinessTests().folder(folder)
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            report = preview(folder, NOW)
            self.assertEqual(report['status'], 'checks_complete')
            self.assertEqual(len(report['source_preview']), 4)
            self.assertTrue(all(s['status'] == 'passed' for s in report['source_preview']))
            self.assertFalse(report['model_ready']); self.assertFalse(report['purchase_authorized'])
            output = json.dumps(report) + render_preview(report)
            for private in ('test-line', str(folder), 'test-only-coverage-source'):
                self.assertNotIn(private, output)
            self.assertIn('no row-level quarantine', output)
            html = render_preview(report)
            self.assertLess(html.index('Not ready for training or purchasing.'), html.index('Fixed-schema source preview'))
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_missing_extra_duplicate_and_reordered_headers_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); readiness_tests.ReadinessTests().folder(folder)
            path = folder / 'decision_signals.csv'
            fields = next(csv.reader(path.read_text().splitlines()))
            for changed in (fields[1:], fields + ['<private-source>'], fields + [fields[0]], list(reversed(fields))):
                with self.subTest(columns=changed):
                    with path.open('w', encoding='utf-8-sig', newline='') as stream:
                        csv.writer(stream).writerow(changed)
                    before = path.read_bytes()
                    report = preview(folder, NOW)
                    item = report['source_preview'][-1]
                    self.assertEqual(report['status'], 'blocked')
                    self.assertEqual(item['status'], 'blocked')
                    self.assertFalse(item['exact_order'])
                    self.assertEqual(item['missing_columns'], [key for key in fields if key not in changed])
                    self.assertEqual(item['unexpected_column_count'], sum(key not in fields for key in changed))
                    self.assertEqual(item['duplicate_column_count'], len(changed) - len(set(changed)))
                    self.assertNotIn('private-source', json.dumps(report) + render_preview(report))
                    self.assertEqual(before, path.read_bytes())

    def test_permission_failure_skips_header_inspection(self):
        with patch('buyer_import_preview.readiness', return_value={'status': 'blocked'}), \
             patch('buyer_import_preview.load_pilot_setup', side_effect=DataError('blocked')), \
             patch('buyer_import_preview.Path.open') as opened:
            self.assertEqual(preview('unused', NOW)['source_preview'], [])
            opened.assert_not_called()

    def test_matching_headers_do_not_bypass_timestamp_or_unit_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); readiness_tests.ReadinessTests().folder(folder)
            path = folder / 'receipt_events.csv'
            original = path.read_text()
            for field, value in [('event_at', 'invalid'), ('unit', 'mismatched-unit')]:
                rows = list(csv.DictReader(original.splitlines()))
                rows[0][field] = value
                with path.open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                    writer.writeheader(); writer.writerows(rows)
                report = preview(folder, NOW)
                self.assertTrue(all(s['status'] == 'passed' for s in report['source_preview']))
                self.assertEqual([s['status'] for s in report['stages']], ['passed', 'blocked', 'skipped'])
                self.assertFalse(report['model_ready'])

    def test_missing_file_and_cli_block_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp); readiness_tests.ReadinessTests().folder(folder)
            (folder / 'receipt_events.csv').unlink()
            report = preview(folder, NOW)
            self.assertEqual(report['source_preview'][1]['reason'], 'Cannot read a UTF-8 CSV header.')
            script = Path(__file__).resolve().parents[1] / 'ml/buyer_import_preview.py'
            for fmt in ('json', 'html'):
                result = subprocess.run([sys.executable, str(script), temp, '--format', fmt],
                                        capture_output=True, encoding='utf-8', timeout=30)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stderr, '')
                if fmt == 'json': self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
                else: self.assertIn('Buyer import preview', result.stdout)


if __name__ == '__main__':
    unittest.main()
