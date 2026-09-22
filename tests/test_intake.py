import json
from pathlib import Path
import tempfile
import unittest
import bootstrap
from xactimate_reconcile.store import init_case,read_json,write_json,within,sha_file
from xactimate_reconcile.intake import add_document,extract_document

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'case'
        init_case(self.root,'TEST-1','shingle',True)

    def test_original_is_retained_and_duplicate_import_is_idempotent(self):
        src=Path(self.temp.name)/'notes.txt';src.write_text('Roof A observed on inspection.\n')
        before=src.read_bytes()
        doc=add_document(self.root,src,'evidence')
        self.assertEqual(before,within(self.root,doc['path']).read_bytes())
        self.assertEqual(doc['id'],add_document(self.root,src,'evidence')['id'])
        self.assertEqual(1,len(read_json(self.root/'manifest.json')['documents']))

    def test_missing_pdf_pages_do_not_become_complete(self):
        try:import fitz
        except ImportError:self.skipTest('PyMuPDF optional dependency absent')
        src=Path(self.temp.name)/'one.pdf'
        d=fitz.open();d.new_page().insert_text((72,72),'Quantity 25 SQ at 450.00');d.save(src);d.close()
        doc=add_document(self.root,src,'baseline',expected_pages=2)
        self.assertFalse(doc['estimate_complete'])
        pages=extract_document(self.root,doc['id'],ocr='off')
        self.assertEqual(1,len(pages))
        text=within(self.root,pages[0]['text_path']).read_text()
        self.assertIn('25 SQ',text)
        self.assertEqual(sha_file(within(self.root,pages[0]['image_path'])),pages[0]['image_sha256'])

    def test_second_estimate_requires_explicit_selection(self):
        for index in range(2):
            src=Path(self.temp.name)/f'source{index}.txt';src.write_text(str(index))
            add_document(self.root,src,'baseline',version=f'v{index+1}')
        self.assertEqual(2,len(read_json(self.root/'manifest.json')['documents']))
        self.assertEqual(1,len(read_json(self.root/'case.json')['documents']))

    def test_hash_change_refuses_extraction(self):
        src=Path(self.temp.name)/'notes.txt';src.write_text('Original evidence')
        doc=add_document(self.root,src,'evidence')
        within(self.root,doc['path']).write_text('Changed evidence')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):extract_document(self.root,doc['id'])

    def test_paths_and_duplicate_json_keys_refused(self):
        with self.assertRaises(ValueError):within(self.root,'../outside')
        target=self.root/'bad.json';target.write_text('{"value":1,"value":2}')
        with self.assertRaisesRegex(ValueError,'Duplicate'):read_json(target)

    def test_init_does_not_overwrite_existing_case(self):
        with self.assertRaisesRegex(ValueError,'already exists'):init_case(self.root,'TEST-1','tile')

    def test_image_ocr_can_fall_back_to_manual_review(self):
        try:from PIL import Image
        except ImportError:self.skipTest('Pillow optional dependency absent')
        src=Path(self.temp.name)/'photo.png';Image.new('RGB',(400,200),'white').save(src)
        doc=add_document(self.root,src,'baseline')
        pages=extract_document(self.root,doc['id'],ocr='off')
        self.assertEqual('vision',pages[0]['method'])
        self.assertEqual((400,200),(pages[0]['width'],pages[0]['height']))

if __name__=='__main__':unittest.main()
