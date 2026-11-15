import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from analyze_public_deliveries import analyze


def row(identifier, shipment, scheduled, actual, recorded='5-Jan-15'):
    return {'ID': identifier, 'ASN/DN #': shipment, 'Country': 'Fixture country',
            'Scheduled Delivery Date': scheduled, 'Delivered to Client Date': actual,
            'Delivery Recorded Date': recorded}


class PublicDeliveryTests(unittest.TestCase):
    def test_unreviewed_file_cannot_claim_the_pinned_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'other.csv'
            path.write_text('different data', encoding='utf-8')
            output = Path(folder) / 'report.json'
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'ml/analyze_public_deliveries.py'),
                       str(path), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('does not match the reviewed SCMS mirror snapshot', result.stderr)
            self.assertFalse(output.exists())

    def test_line_items_are_not_independent_shipments(self):
        result = analyze([row('1', 'A', '1-Jan-15', '2-Jan-15'),
                          row('2', 'A', '1-Jan-15', '2-Jan-15'),
                          row('3', 'B', '2-Jan-15', '2-Jan-15')])
        self.assertEqual(result['line_item_metrics']['late_count'], 2)
        self.assertEqual(result['consistent_asn_dn_metrics']['eligible_count'], 2)
        self.assertEqual(result['consistent_asn_dn_metrics']['late_count'], 1)

    def test_conflicts_and_missing_dates_stay_visible(self):
        result = analyze([row('1', 'A', '1-Jan-15', '2-Jan-15'),
                          row('2', 'A', '1-Jan-15', '3-Jan-15'),
                          row('3', 'B', 'Date Not Captured', '3-Jan-15'),
                          row('4', '', '1-Jan-15', '2-Jan-15', '1-Jan-15')])
        self.assertEqual(result['conflicting_asn_dn_date_groups'], 1)
        self.assertEqual(result['incomplete_asn_dn_date_groups'], 1)
        self.assertEqual(result['missing_or_unparseable_delivery_date_rows'], 1)
        self.assertEqual(result['recording_before_delivery_rows'], 1)
        self.assertIsNone(result['consistent_asn_dn_metrics']['late_rate'])
        self.assertEqual(result['rows_without_asn_dn'], 1)

    def test_duplicate_line_ids_fail(self):
        with self.assertRaises(ValueError):
            analyze([row('1', 'A', '1-Jan-15', '2-Jan-15')] * 2)


if __name__ == '__main__':
    unittest.main()
