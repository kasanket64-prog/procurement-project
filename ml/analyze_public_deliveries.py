"""Describe historical SCMS delivery dates; never produce supplier risk scores."""
import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SOURCE_URL = ('https://github.com/jrcinco/supply-chain-shipment-price-data/blob/'
              '3d12aa307c4fcfa19df7dfbfa2f277db9132c557/SCMS_Delivery_History_Dataset.csv')
SOURCE_SHA256 = '918b992dd3e8d4b64d2a727b2c4ea607603d0c58f19484e73f7b78528c6a8673'
FIELDS = ('ID', 'ASN/DN #', 'Country', 'Scheduled Delivery Date',
          'Delivered to Client Date', 'Delivery Recorded Date')


def date(value):
    try:
        return datetime.strptime(value.strip(), '%d-%b-%y').date()
    except (ValueError, AttributeError):
        return None


def metrics(pairs):
    late = sum(actual > scheduled for scheduled, actual in pairs)
    return {'eligible_count': len(pairs), 'late_count': late,
            'on_or_before_schedule_count': len(pairs) - late,
            'late_rate': late / len(pairs) if pairs else None}


def analyze(rows):
    ids = [r['ID'] for r in rows]
    if not all(ids) or len(set(ids)) != len(ids):
        raise ValueError('Line-item IDs must be populated and unique')
    pairs, shipments, actuals = [], defaultdict(list), []
    missing_dates = missing_shipment_ids = recording_before_delivery = 0
    for r in rows:
        scheduled, actual = date(r['Scheduled Delivery Date']), date(r['Delivered to Client Date'])
        recorded = date(r['Delivery Recorded Date'])
        if actual:
            actuals.append(actual)
        if recorded and actual and recorded < actual:
            recording_before_delivery += 1
        pair = (scheduled, actual) if scheduled and actual else None
        if pair:
            pairs.append(pair)
        else:
            missing_dates += 1
        key = r['ASN/DN #'].strip()
        if key:
            shipments[key].append(pair)
        else:
            missing_shipment_ids += 1
    consistent, conflicts, incomplete = [], 0, 0
    for values in shipments.values():
        if None in values:
            incomplete += 1
        elif len(set(values)) != 1:
            conflicts += 1
        else:
            consistent.append(values[0])
    return {
        'status': 'HISTORICAL_MIRROR_RESEARCH_ONLY_NOT_SUPPLIER_VALIDATION',
        'line_item_count': len(rows), 'country_count': len({r['Country'] for r in rows if r['Country']}),
        'recorded_delivery_range': [min(actuals).isoformat(), max(actuals).isoformat()] if actuals else None,
        'line_item_metrics': metrics(pairs),
        'missing_or_unparseable_delivery_date_rows': missing_dates,
        'recording_before_delivery_rows': recording_before_delivery,
        'distinct_asn_dn_identifiers': len(shipments),
        'rows_without_asn_dn': missing_shipment_ids,
        'consistent_asn_dn_metrics': metrics(consistent),
        'conflicting_asn_dn_date_groups': conflicts,
        'incomplete_asn_dn_date_groups': incomplete,
        'definition': 'Late means Delivered to Client Date is after Scheduled Delivery Date; no grace period.',
        'limitations': [
            'Downloaded from a public mirror attributed to USAID SCMS; original portal unavailable; authenticity not certified.',
            'Reuse metadata conflict (CC BY versus CC BY-ND); raw data and row-level derivatives are not redistributed in this repository.',
            'Historical health-commodity records do not validate current suppliers or other procurement sectors.',
            'The scheduled dates may have been revised; original commitment and revision timestamps are unavailable.',
            'ASN/DN identifiers are grouping keys, not proof of independent complete physical shipments; conflicting or incomplete groups are excluded from group metrics.',
            'Late arrival does not establish supplier fault; route, buyer, customs and schedule revisions can affect outcomes.',
            'No predictive model trained, no supplier names ranked, and no link to purchasing or customer demo scores.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(args.csv_path.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError('Input does not match the reviewed SCMS mirror snapshot')
    with args.csv_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('Missing required SCMS delivery columns')
        report = analyze(list(reader))
    report['source_url'] = SOURCE_URL
    report['input_sha256'] = digest
    report['analyzer_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
