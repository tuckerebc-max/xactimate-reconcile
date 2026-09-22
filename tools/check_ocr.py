"""Bounded synthetic OCR smoke check; not a benchmark of real-document accuracy."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SKILL=Path(os.environ.get('XR_DEV_SKILL',ROOT/'.agents/skills/xactimate-reconcile'))
sys.path.insert(0,str(SKILL/'scripts'))
from xactimate_reconcile.intake import add_document,extract_document,capabilities
from xactimate_reconcile.store import init_case,read_json


def main():
    report={'test_type':'synthetic OCR smoke check','real_document_validation':False,'capabilities':capabilities(),'samples':[]}
    source_root=SKILL/'assets/examples/shingle'
    case=read_json(source_root/'case.json')
    doc=next(d for d in case['documents'] if d['role']=='proposed')
    image=source_root/doc['pages'][0]['image_path']
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp)
        from PIL import Image,ImageFilter
        im=Image.open(image).convert('RGB')
        paths={'clean_image':base/'clean.png','scan_pdf':base/'scan.pdf','degraded_image':base/'degraded.jpg'}
        im.save(paths['clean_image']);im.save(paths['scan_pdf'],'PDF',resolution=144)
        im.resize((612,792)).filter(ImageFilter.GaussianBlur(.8)).rotate(3,expand=True,fillcolor='white').save(paths['degraded_image'],quality=60)
        expected=['25','450','11250.00','80','800.00','350.00','12400.00']
        for label,path in paths.items():
            root=base/label;init_case(root,'OCR-'+label.replace('_','-'),'shingle',True)
            d=add_document(root,path,'proposed');extract_document(root,d['id'],'always')
            pages=read_json(root/'case.json')['documents'][0]['pages']
            text='\n'.join((root/p['text_path']).read_text() for p in pages)
            compact=text.replace(',','')
            observed={value:value in compact for value in expected}
            report['samples'].append({'sample':label,'methods':[p['method'] for p in pages],
                'expected_numeric_strings':expected,'found_by_literal_smoke_check':observed,
                'found_count':sum(observed.values()),'denominator':len(expected),
                'verified_line_mapping':False,'transcription':text})
    report['limitations']=['Literal presence can match an unrelated occurrence; these are smoke checks, not digit-level precision/recall.',
        'No automatic semantic table extraction or human verification is claimed.',
        'All samples derive from one generated estimate; no real scanner, phone capture or client document was evaluated.']
    output=ROOT/'validation/ocr-smoke.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'report':str(output),'samples':[{k:v for k,v in x.items() if k!='transcription'} for x in report['samples']]},indent=2))

if __name__=='__main__':main()
