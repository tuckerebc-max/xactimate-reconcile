from pathlib import Path
import copy
import csv
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch
import bootstrap
from xactimate_reconcile.cli import ASSETS, run_case, current_status, calculate, add_extension, operator_check, package_review
from xactimate_reconcile.review import prepare_review, import_decisions
from xactimate_reconcile.store import read_json, write_json
from xactimate_reconcile.render import build_documents


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'case with spaces'
        shutil.copytree(ASSETS/'examples/shingle',self.root)

    def tearDown(self):self.temp.cleanup()

    def test_three_examples_have_independently_specified_outcomes(self):
        for name,delta,status in [('shingle','3050.00','draft'),('tile','450.00','draft'),('low_slope',None,'partial')]:
            with self.subTest(name=name):
                case,report=calculate(ASSETS/'examples'/name)
                self.assertEqual(report['status'],status)
                if delta is None:
                    self.assertIsNone(report['totals'])
                    self.assertEqual(report['partial_totals']['supported_delta'],'500.00')
                else:self.assertEqual(report['totals']['delta_direct'],delta)

    def test_editing_an_output_makes_run_stale(self):
        result=run_case(self.root)
        self.assertEqual(current_status(self.root)['status'],'draft')
        (Path(result['run'])/'cover_letter.md').write_text('Changed amount')
        self.assertEqual(current_status(self.root)['status'],'stale')

    def test_editing_case_makes_run_stale(self):
        run_case(self.root)
        case=read_json(self.root/'case.json');case['notes']+=' New fact.'
        write_json(self.root/'case.json',case)
        self.assertEqual(current_status(self.root)['status'],'stale')

    def test_failed_rerun_cannot_leave_current_approval_target(self):
        run_case(self.root)
        with patch('xactimate_reconcile.render.render_all',side_effect=RuntimeError('render failed')):
            with self.assertRaises(RuntimeError):run_case(self.root)
        self.assertEqual(current_status(self.root)['status'],'stale')
        self.assertFalse(list((self.root/'runs').glob('.building-*')))

    def test_changed_original_blocks_the_comparison(self):
        case=read_json(self.root/'case.json')
        (self.root/case['documents'][0]['path']).write_bytes(b'changed')
        _,report=calculate(self.root)
        self.assertEqual(report['status'],'blocked');self.assertIsNone(report['totals'])

    def test_changed_source_page_blocks_the_comparison(self):
        case=read_json(self.root/'case.json')
        (self.root/case['documents'][0]['pages'][0]['image_path']).write_bytes(b'changed')
        _,report=calculate(self.root)
        self.assertEqual(report['status'],'blocked')
        self.assertIn('E_DERIVATIVE_HASH',{i['code'] for i in report['issues']})

    def test_malformed_nested_document_returns_a_blocked_report(self):
        case=read_json(self.root/'case.json');case['documents']=[None]
        write_json(self.root/'case.json',case)
        _,report=calculate(self.root)
        self.assertEqual(report['status'],'blocked')
        docs=build_documents(case,report)
        self.assertIn('DO NOT SUBMIT',str(docs))

    def decisions(self,kind='ai',alter=False):
        data=prepare_review(self.root)
        p=Path(data['decisions'])
        with p.open(newline='') as f:
            reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
        for row in rows:row['decision']='confirm'
        if alter:rows[0]['value']='999999'
        with p.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
        return p

    def test_ai_review_never_becomes_human_review(self):
        p=self.decisions();import_decisions(self.root,p,'AI test agent','ai')
        _,report=calculate(self.root)
        self.assertTrue(report['review_summary']['ai_confirmed'])
        self.assertFalse(report['review_summary']['human_confirmed'])
        self.assertNotEqual(report['review_summary']['required'],report['review_summary']['human_confirmed'])

    def test_changed_display_number_cannot_be_confirmed(self):
        p=self.decisions(alter=True)
        with self.assertRaisesRegex(ValueError,'displayed'):import_decisions(self.root,p,'Test reviewer','ai')

    def test_changed_source_context_rejects_old_review(self):
        p=self.decisions()
        case=read_json(self.root/'case.json');case['lines'][0]['unit']='SF'
        write_json(self.root/'case.json',case)
        with self.assertRaisesRegex(ValueError,'Stale'):import_decisions(self.root,p,'Test reviewer','ai')

    def test_synthetic_package_cannot_receive_live_sender_approval(self):
        run_case(self.root)
        with self.assertRaisesRegex(ValueError,'Synthetic'):package_review(self.root,'Synthetic person','sender','approve','test')

    def test_operator_mismatch_is_retained_without_claiming_match(self):
        result=run_case(self.root)
        case=read_json(self.root/'case.json')
        source=self.root/next(d['path'] for d in case['documents'] if d['role']=='proposed')
        receipt=operator_check(self.root,source,'12401.00','Synthetic operator','test only')
        self.assertFalse(receipt['matches'])
        self.assertEqual(receipt['expected_direct_total'],'12400.00')

    def test_pack_installation_is_versioned_and_does_not_change_amounts(self):
        source=ASSETS/'extensions/arizona-research.json'
        before=calculate(self.root)[1]['totals']
        added=add_extension(self.root,source)
        self.assertTrue((Path(added['path'])/'pack.json').is_file())
        with self.assertRaisesRegex(ValueError,'already present'):add_extension(self.root,source)
        self.assertEqual(before,calculate(self.root)[1]['totals'])

if __name__=='__main__':unittest.main()
