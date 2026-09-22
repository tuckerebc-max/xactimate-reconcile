#!/usr/bin/env python3
"""Offline structural checks. Passing is not legal/claims approval or permission to send."""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ARG_FIELDS = ('issue_id proposition rule_or_policy_text_needed facts_needed evidence_needed '
              'calculation_dependency requested_change strongest_carrier_response supported_reply '
              'concession_or_failure_condition source_ids status').split()
SRC_FIELDS = ('source_id title url authority jurisdiction publication_or_effective_date '
              'accessed_date locator supported_claim limitation retrieval_status').split()
STATUSES = {'CONDITIONAL_NEEDS_CLAIM_EVIDENCE','POLICY_AND_LEGAL_REVIEW_REQUIRED',
            'SPECIALIST_INPUT_REQUIRED','LEGAL_REVIEW_AND_CURRENT_PROCESS_CHECK_REQUIRED',
            'ROLE_REVIEW_REQUIRED','DATE_AND_SCOPE_REVIEW_REQUIRED'}

def validate(root):
    errors=[]
    def check(condition,message):
        if not condition: errors.append(message)
    records={}
    for filename,fields,idfield,pattern in [
        ('B_ARGUMENTS.json',ARG_FIELDS,'issue_id',r'B-I\d{2}'),
        ('B_SOURCES.json',SRC_FIELDS,'source_id',r'B-S\d{2}')]:
        try: data=json.loads((root/filename).read_text(encoding='utf-8'))
        except (OSError,ValueError) as exc:
            errors.append(f'{filename}: {exc}');continue
        if not isinstance(data,list) or not data:
            errors.append(f'{filename}: nonempty top-level array required');continue
        seen=set()
        for index,row in enumerate(data):
            if not isinstance(row,dict):
                errors.append(f'{filename}[{index}]: object required');continue
            for field in fields:check(field in row and row[field] not in ('',[],None),f'{filename}[{index}]: missing/empty {field}')
            ident=row.get(idfield,'')
            check(isinstance(ident,str) and bool(re.fullmatch(pattern,ident)),f'{filename}[{index}]: invalid ID')
            check(ident not in seen,f'{filename}: duplicate ID {ident}');seen.add(ident)
        records[filename]=data
    source_map={s.get('source_id'):s for s in records.get('B_SOURCES.json',[]) if isinstance(s,dict)}
    issues=records.get('B_ARGUMENTS.json',[])
    for row in issues:
        if not isinstance(row,dict):continue
        ident=row.get('issue_id','?')
        check(row.get('status') in STATUSES,f'{ident}: claim must remain conditional/review-required')
        for field in ['facts_needed','evidence_needed','source_ids']:
            value=row.get(field)
            check(isinstance(value,list) and bool(value) and all(isinstance(x,str) and bool(x.strip()) for x in value),f'{ident}: invalid {field}')
        refs=row.get('source_ids',[])
        if isinstance(refs,list):
            for ref in refs:check(ref in source_map,f'{ident}: unresolved source {ref}')
            check(any(source_map.get(ref,{}).get('retrieval_status')=='opened_relevant_text' for ref in refs),f'{ident}: no opened substantive source')
    for name in ['B_RESEARCH.md','B_TEMPLATES.md','B_CLAIMS_REVIEW.md','B_LEGAL_REVIEW.md']:
        try:t=(root/name).read_text(encoding='utf-8')
        except OSError as exc:errors.append(f'{name}: {exc}');continue
        check(bool(t.strip()),f'{name}: empty')
        for ref in set(re.findall(r'B-S\d{2}',t)):check(ref in source_map,f'{name}: unresolved source {ref}')
    for name in ['B_CLAIMS_REVIEW.md','B_LEGAL_REVIEW.md']:
        if (root/name).exists():check('NON-INDEPENDENT' in (root/name).read_text(),f'{name}: review independence not disclosed')
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir()) if p.is_file() and p.name not in {'B_VALIDATION.json'}}
    return {'checked_at':datetime.now(timezone.utc).isoformat(),'structural_validation':'PASS' if not errors else 'FAIL',
            'issues':len(issues),'sources':len(source_map),'errors':errors,'file_sha256':files,
            'limitations':['Checks required fields, identifier integrity, opened-source presence and conditional statuses.',
                          'Does not verify legal truth, source interpretation, live prices, roof conditions or claim arithmetic.',
                          'Does not authorize external use, professional practice or release of a claim packet.']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',nargs='?',default=str(Path(__file__).resolve().parent))
    parser.add_argument('--output',help='Optional path for the JSON validation report')
    args=parser.parse_args();result=validate(Path(args.directory))
    payload=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if args.output:Path(args.output).write_text(payload,encoding='utf-8')
    print(payload,end='');sys.exit(0 if result['structural_validation']=='PASS' else 1)
