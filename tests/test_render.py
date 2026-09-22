from pathlib import Path
import tempfile
import unittest
import bootstrap
from xactimate_reconcile.render import build_documents,render_all

class RenderTests(unittest.TestCase):
    def fixture(self):
        case={'case_id':'EXAMPLE','synthetic':True,'as_of':'2026-09-21','documents':[], 'evidence':[], 'lines':[],
              'groups':[{'claim_id':'I-1','title':'Measured roof area','observation':'Two measured faces total 25 SQ.',
                         'necessity':'The installation quantity must cover those measured faces.',
                         'reply':'The supplied surface measurement includes pitch once.',
                         'requested_action':'Correct the affected area to 25 SQ.'}], 'sender':{'name':'Synthetic estimator'}}
        report={'status':'draft','issues':[],'financial_bridge':{},'groups':[{'claim_id':'I-1','baseline_direct':'8000.00','proposed_direct':'11250.00','delta':'3250.00',
                 'components':{'quantity':'2000.00','price':'1250.00','rounding':'0.00'},'source_ids':['E-1'],'counterargument':'Confirm surface versus plan area.',
                 'mapping_rationale':'Same installation scope.','coverage_status':'unknown','scope_status':'supported','baseline':['B1'],'proposed':['P1']}],
                'totals':{'baseline_direct':'8000.00','proposed_direct':'11250.00','delta_direct':'3250.00','downward_changes':'0.00'}}
        return case,report

    def test_all_documents_share_the_same_amount_and_source(self):
        case,report=self.fixture();docs=build_documents(case,report)
        self.assertEqual({'reconciliation_memo','cover_letter','operator_checklist','evidence_appendix'},set(docs))
        for key in ['reconciliation_memo','cover_letter','operator_checklist']:
            self.assertIn('3,250.00',str(docs[key]))
        self.assertIn('E-1',str(docs['reconciliation_memo']))
        self.assertIn('SYNTHETIC',str(docs['cover_letter']))

    def test_partial_comparison_cannot_state_complete_request_amount(self):
        case,report=self.fixture();report['totals']=None;report['status']='partial'
        letter=str(build_documents(case,report)['cover_letter'])
        self.assertIn('incomplete',letter)
        self.assertNotIn('net change of',letter)

    def test_markdown_and_requested_formats_produce_files(self):
        case,report=self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            result=render_all(case,report,tmp,tmp,formats=('md','docx','pdf'))
            self.assertTrue((Path(tmp)/'cover_letter.md').is_file())
            for ext in ('docx','pdf'):
                if not any(ext in w for w in result['warnings']):self.assertTrue((Path(tmp)/('cover_letter.'+ext)).is_file())

if __name__=='__main__':unittest.main()
