"""Synthetic replacement proposals and a deliberately limited price-only ablation."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ml'))
from procurement_recovery import recover, render_html
from quotation_demo import build_demo
from real_procurement import DataError, evaluate
from test_buyer_snapshot_check import NOW


def fixture(now=NOW):
    bundle = build_demo(now)
    for quote in bundle['quotes']:
        quote.update(valid_until=(now+timedelta(days=3)).isoformat(), all_costs_included=True)
    bundle['recovery_event'] = dict(type='supplier_unavailable', confirmed=True, supplier_id='demo-1',
                                   source_id='demo', source_record_id='disruption',
                                   event_at=(now-timedelta(hours=2)).isoformat(), known_at=(now-timedelta(hours=1)).isoformat())
    bundle['capacity_evidence'] = [dict(quote_id=q['id'], source_id='demo', source_record_id='capacity-'+q['id'],
                                       confirmed=True, quantity='10', unit='each', known_at=now.isoformat(),
                                       valid_until=(now+timedelta(days=1)).isoformat()) for q in bundle['quotes']]
    return bundle


def price_only(bundle):
    rows = [r for r in evaluate(bundle, NOW, demo=True)['quotes'] if r['eligible'] and
            r['supplier_id'] != bundle['recovery_event']['supplier_id']]
    return min(rows, key=lambda r:(Decimal(r['quoted_total']),r['quote_id']))['quote_id'] if rows else None


class RecoveryTests(unittest.TestCase):
    def test_valid_alternative_uses_exact_quote_and_does_not_mutate_inputs(self):
        bundle=fixture(); before=deepcopy(bundle)
        report=recover(bundle,NOW,demo=True)
        self.assertEqual(report['proposed_quote_ids'],['quote-2'])
        self.assertEqual(report['request'],bundle['request'])
        self.assertEqual(bundle,before)
        self.assertEqual(report['options'][0]['status'],'excluded')
        self.assertFalse(report['purchase_authorized']);self.assertFalse(report['model_ready'])
        self.assertTrue(report['human_review_required'])
        self.assertTrue(all(r['risk_estimate'] is None for r in report['options']))
        self.assertEqual(report['options'][1]['capacity_evidence']['quantity'],'10')
        self.assertIn('Original request and disruption evidence',render_html(report))

    def test_six_case_price_only_ablation(self):
        cases=[]
        good=fixture();cases.append(('complete',good,'quote-2','quote-2','options_available'))
        missing=fixture();missing['capacity_evidence'].pop(1);cases.append(('missing',missing,'quote-2','quote-3','options_available'))
        short=fixture();short['capacity_evidence'][1]['quantity']='4';cases.append(('short',short,'quote-2','quote-3','options_available'))
        stale=fixture();stale['capacity_evidence'][1].update(known_at=(NOW-timedelta(days=2)).isoformat(),valid_until=NOW.isoformat());cases.append(('stale',stale,'quote-2','quote-3','options_available'))
        unknown=fixture();unknown['capacity_evidence']=[];cases.append(('all missing',unknown,'quote-2',None,'needs_review'))
        budget=fixture();budget['request']['total_budget']='8000';cases.append(('budget',budget,None,None,'infeasible'))
        unsupported=0
        for name,bundle,baseline,proposal,status in cases:
            with self.subTest(name=name):
                report=recover(bundle,NOW,demo=True)
                self.assertEqual(price_only(bundle),baseline)
                self.assertEqual(report['proposed_quote_ids'],[proposal] if proposal else [])
                self.assertEqual(report['status'],status)
                if baseline and next(r for r in report['options'] if r['quote_id']==baseline)['status']!='feasible':unsupported+=1
        self.assertEqual(unsupported,4)  # Constructed stress cases, not population performance.

    def test_quote_constraints_still_gate_recovery_and_decimal_ties_remain_tied(self):
        bundle=fixture();bundle['quotes'][1]['quantity']='9'
        self.assertEqual(recover(bundle,NOW,demo=True)['proposed_quote_ids'],['quote-3'])
        bundle=fixture();bundle['quotes'][2]['total_amount']='9000.000000'
        self.assertEqual(recover(bundle,NOW,demo=True)['proposed_quote_ids'],['quote-2','quote-3'])
        bundle=fixture();bundle['request']['required_brand']='Required'
        report=recover(bundle,NOW,demo=True)
        self.assertEqual(report['status'],'needs_review');self.assertEqual(report['proposed_quote_ids'],[])

    def test_future_unconfirmed_and_unit_mismatched_capacity_is_unavailable(self):
        for change in [dict(confirmed=False),dict(known_at=(NOW+timedelta(hours=1)).isoformat()),dict(unit='kg')]:
            bundle=fixture();bundle['capacity_evidence'][1].update(change)
            report=recover(bundle,NOW,demo=True)
            self.assertEqual(report['options'][1]['status'],'unavailable')
            self.assertEqual(report['proposed_quote_ids'],['quote-3'])

    def test_invalid_event_source_duplicate_capacity_and_wrong_mode_block(self):
        for change in [dict(source_id=[]),dict(source_id='missing'),dict(confirmed=False),dict(known_at=(NOW+timedelta(days=1)).isoformat())]:
            bundle=fixture();bundle['recovery_event'].update(change)
            with self.subTest(change=change),self.assertRaises(DataError):recover(bundle,NOW,demo=True)
        bundle=fixture();bundle['capacity_evidence'].append(deepcopy(bundle['capacity_evidence'][1]))
        with self.assertRaises(DataError):recover(bundle,NOW,demo=True)
        with self.assertRaises(DataError):recover(fixture(),NOW)

    def test_html_escapes_identifiers_and_cli_is_read_only(self):
        report=recover(fixture(),NOW,demo=True);report['options'][1]['supplier_id']='<script>test</script>'
        html=render_html(report)
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
        self.assertIn("default-src 'none'",html)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fixture.json';path.write_text(json.dumps(fixture()),encoding='utf-8');before=path.read_bytes()
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'ml/procurement_recovery.py'),str(path)],capture_output=True,encoding='utf-8',timeout=30)
            self.assertEqual(result.returncode,2);self.assertEqual(result.stderr,'')
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(list(Path(temp).iterdir()),[path])


if __name__=='__main__':unittest.main()
