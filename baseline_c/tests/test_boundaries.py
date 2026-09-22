import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from prototype.reconcile import reconcile

ROOT=Path(__file__).resolve().parents[1]
class BoundaryTests(unittest.TestCase):
    def setUp(self):self.case=json.loads((ROOT/'fixtures/synthetic_case.json').read_text())
    def test_malformed_geometry_is_refused_without_exception(self):
        self.case['lines'][0]['geometry']=None
        r=reconcile(self.case,ROOT/'fixtures')
        self.assertEqual('blocked',r['status']);self.assertIsNone(r['totals'])
    def test_unknown_property_is_refused(self):
        self.case['pretend_release_approved']=True
        self.assertEqual('blocked',reconcile(self.case,ROOT/'fixtures')['status'])
    def test_source_root_output_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=subprocess.run([sys.executable,'-m','prototype.reconcile',str(ROOT/'fixtures/synthetic_case.json'),'--source-root',str(ROOT/'fixtures'),'--out',str(ROOT/'fixtures/should-not-exist.json')],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(2,result.returncode)
            self.assertFalse((ROOT/'fixtures/should-not-exist.json').exists())
    def test_scope_removal_requires_verified_absence(self):
        self.case['groups'][0]['proposed']=[];self.case['groups'][0]['change_type']='scope'
        r=reconcile(self.case,ROOT/'fixtures')
        self.assertEqual('blocked',r['status'])
        self.assertIn('E_ABSENCE',{x['code'] for x in r['issues']})
    def test_empty_source_root_cannot_pass(self):
        r=reconcile(self.case)
        self.assertEqual('blocked',r['status'])
        self.assertIn('E_SOURCE_ROOT',{x['code'] for x in r['issues']})

if __name__=='__main__':unittest.main()
