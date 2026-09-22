"""Portable release structure/cross-reference checks; not a claim or legal validator."""
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
SKILL=Path(os.environ.get('XR_DEV_SKILL',ROOT/'.agents/skills/xactimate-reconcile'))
sys.path.insert(0,str(SKILL/'scripts'))
from xactimate_reconcile.extensions import validate_pack

def main():
    errors=[]
    def read(path):return json.loads(path.read_text(encoding='utf-8'))
    for path in ['README.md','AGENTS.md','CLAUDE.md','docs/OPERATING_GUIDE.md','docs/EXTENDING.md','docs/READINESS.md']:
        if not (ROOT/path).is_file():errors.append('Missing '+path)
    for path in ['SKILL.md','agents/openai.yaml','scripts/xr.py','assets/schemas/case.schema.json','assets/schemas/extension.schema.json']:
        if not (SKILL/path).is_file():errors.append('Missing skill file '+path)
    knowledge=SKILL/'assets/knowledge'
    a=read(knowledge/'A/A_OPPORTUNITIES.json');b=read(knowledge/'B/B_ARGUMENTS.json')
    if len(a)!=20:errors.append('Expected 20 A review categories')
    if len(b)!=24:errors.append('Expected 24 conditional B arguments')
    for path in list((ROOT/'extension_examples').glob('*.json'))+list((SKILL/'assets/extensions').glob('*.json')):
        errors.extend(path.name+': '+e for e in validate_pack(read(path),path.parent))
    for roof in ['shingle','tile','low_slope']:
        root=SKILL/'assets/examples'/roof
        for path in ['case.json','manifest.json','reviews/records.json']:
            if not (root/path).is_file():errors.append('Missing '+str(root/path))
    result={'structural_validation':'PASS' if not errors else 'FAIL','a_categories':len(a),'b_arguments':len(b),'errors':errors,
            'scope':'File presence, pack validation and inventory counts; not substantive evidence verification.'}
    print(json.dumps(result,indent=2))
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
