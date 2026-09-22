import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class OutputTests(unittest.TestCase):
    def test_cli_and_all_three_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, '-m', 'prototype.render', str(ROOT/'fixtures/synthetic_case.json'), '--source-root', str(ROOT/'fixtures'), '--out-dir', tmp], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            for name in ['reconciliation_memo.md', 'operator_checklist.md', 'cover_letter.md', 'evidence_appendix.md', 'report.json']:
                self.assertTrue((Path(tmp)/name).is_file(), name)
            memo = (Path(tmp)/'reconciliation_memo.md').read_text()
            letter = (Path(tmp)/'cover_letter.md').read_text()
            appendix = (Path(tmp)/'evidence_appendix.md').read_text()
            self.assertIn('640.00', memo)
            self.assertIn('-200.00', memo)
            self.assertIn('SYNTHETIC', letter)
            self.assertIn('C-003', letter)
            self.assertIn('EX-003', appendix)
            self.assertIn('sha256', appendix)

    def test_blocked_input_cannot_make_a_request_letter(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=json.loads((ROOT/'fixtures/synthetic_case.json').read_text())
            data['lines'][1]['quantity']['value']=None
            p=Path(tmp)/'bad.json';p.write_text(json.dumps(data))
            result=subprocess.run([sys.executable,'-m','prototype.render',str(p),'--source-root',str(ROOT/'fixtures'),'--out-dir',str(Path(tmp)/'out')],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(2,result.returncode)
            letter=(Path(tmp)/'out/cover_letter.md').read_text()
            self.assertIn('WITHHELD',letter)
            self.assertNotIn('Please review',letter)

    def test_duplicate_json_key_refused(self):
        from prototype.reconcile import load_case
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.json';p.write_text('{"synthetic":true,"synthetic":false}')
            with self.assertRaisesRegex(ValueError,'Duplicate JSON key'):load_case(p)

if __name__=='__main__': unittest.main()
