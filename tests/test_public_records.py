"""Integrity checks for the bounded public-source snapshot, without network access."""
import hashlib
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).resolve().parents[1] / 'dataset/public_procurement/multisource_2025_sample'


def read(name):
    return json.loads((DATA / name).read_text(encoding='utf-8-sig'))


class PublicRecordTests(unittest.TestCase):
    def test_original_responses_match_recorded_digests(self):
        manifest = read('manifest.json')
        self.assertEqual(len(manifest), 3)
        for source in manifest:
            with self.subTest(source=source['source']):
                self.assertEqual(source['status'], 'downloaded')
                self.assertTrue(source['retrieved_at_utc'].endswith('Z'))
                digest = hashlib.sha256((DATA / source['file']).read_bytes()).hexdigest()
                self.assertEqual(digest.upper(), source['sha256'])

    def test_display_records_are_distinct_and_link_to_their_source(self):
        records = read('records.json')
        self.assertEqual(len(records), 296)
        self.assertEqual(len({(r['source'], r['record_id']) for r in records}), len(records))
        hosts = {'UK Contracts Finder': 'www.contractsfinder.service.gov.uk',
                 'USAspending': 'www.usaspending.gov', 'EU TED': 'ted.europa.eu'}
        for record in records:
            with self.subTest(record=record['record_id']):
                self.assertTrue(record['title'])
                self.assertTrue(record['record_kind'])
                self.assertTrue(record['source_urls'])
                for value in record['source_urls']:
                    url = urlparse(value)
                    self.assertEqual(url.scheme, 'https')
                    self.assertEqual(url.hostname, hosts[record['source']])

    def test_display_ids_exist_in_downloaded_responses(self):
        ids = {
            'UK Contracts Finder': {a['id'] for r in read('uk-contracts-finder.json')['releases']
                                   for a in r.get('awards', [])},
            'USAspending': {r['generated_internal_id'] for r in read('usaspending.json')['results']},
            'EU TED': {r['publication-number'] for r in read('eu-ted.json')['notices']},
        }
        for record in read('records.json'):
            self.assertIn(record['record_id'], ids[record['source']])


if __name__ == '__main__':
    unittest.main()
