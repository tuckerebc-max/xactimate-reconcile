"""Deterministic Markdown demonstration outputs. No sending or release operation."""
import argparse
import json
from pathlib import Path
from .reconcile import load_case, reconcile

def clean(value):
    return str(value).replace('|', '\\|').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')

def render(case, report):
    banner='SYNTHETIC DEMONSTRATION — HELD DRAFT — DO NOT SEND\n\n'
    if report['status']!='draft':
        errors='\n'.join(f"- {clean(e['code'])}: {clean(e['ref'])}: {clean(e['message'])}" for e in report['issues'])
        return {name:banner+'WITHHELD: resolve input and evidence defects before drafting a request.\n\n'+errors+'\n' for name in ['reconciliation_memo.md','operator_checklist.md','cover_letter.md','evidence_appendix.md']}
    t=report['totals']; groups=report['groups']
    memo=banner+f"# Reconciliation memo: {clean(case['case_id'])}\n\nAuthor role: {clean(case.get('author_role','Unspecified'))}.\n\nRequest: review the supplied scope and arithmetic supporting a {t['delta_direct']} USD direct-cost change, subject to source, price and policy review.\n\nBaseline direct costs: {t['baseline_direct']} USD. Proposed direct costs: {t['proposed_direct']} USD. Increases: {t['upward_changes']} USD. Reductions: {t['downward_changes']} USD.\n\n| Claim | Baseline | Proposed | Delta | Disposition | Evidence |\n|---|---:|---:|---:|---|---|\n"
    for g in groups:
        memo+=f"| {g['claim_id']} | {g['baseline_direct']} | {g['proposed_direct']} | {g['delta']} | {clean(g['disposition'])} | {', '.join(g['source_ids'])} |\n"
    for g in groups:
        memo+=f"\n## {g['claim_id']}: {g['roof_location']}\n\n{clean(g['mapping_rationale'])}\n\nCalculation: {g['proposed_direct']} − {g['baseline_direct']} = {g['delta']} USD. Components: "+'; '.join(f'{k} {v}' for k,v in g['components'].items())+f".\n\nCounterargument: {clean(g['counterargument'])}\n\nScope: synthetic support only. Coverage: unknown. Status: held for review.\n"
    memo+='\n## Financial bridge and outstanding decisions\n\nOnly direct pre-tax cost is calculated. Tax, general overhead and profit, RCV, depreciation, recoverability, ACV, deductible, limits, prior payments and net payment remain unknown. No price-list month or licensed Xactimate result is supplied.\n'
    letter=banner+f"Re: {clean(case['case_id'])} — request to review roof scope and estimate arithmetic\n\nDear reviewer,\n\nPlease review the attached itemized comparison and exhibits. The proposed direct-cost subtotal is {t['proposed_direct']} USD against {t['baseline_direct']} USD, a net change of {t['delta_direct']} USD. This comparison includes {t['upward_changes']} USD in increases and {t['downward_changes']} USD in reductions.\n\n{' '.join(g['claim_id'] + ': ' + clean(g['mapping_rationale']).rstrip('.;') + '.' for g in groups)} Please respond by claim ID with any different measurement, scope or pricing basis so the comparison can be corrected.\n\nThe memo records the counterarguments and outstanding evidence. Coverage and the payment calculation remain unresolved; the figures above describe direct costs.\n\nSincerely,\nSynthetic roofing-contractor example\n"
    checklist=banner+'# Xactimate operator action checklist\n\n'
    checklist+='- [ ] Verify active estimate versions, price-list location/month, line descriptions, units and source images.\n- [ ] Confirm every quantity and monetary field against its original page/crop; obtain an accountable human review.\n'
    for g in groups:
        checklist+=f"- [ ] {g['claim_id']}: {g['action']}; map {', '.join(g['baseline']) or 'verified absence'} to {', '.join(g['proposed']) or 'verified absence'} at {g['roof_location']}; direct-cost delta {g['delta']} USD. Verify actual catalog item and inclusions in licensed software.\n"
    checklist+='- [ ] Review scope support separately from the policy and endorsements.\n- [ ] Enter only reviewed changes in a separately saved licensed Xactimate estimate.\n- [ ] Re-export and independently check quantities, direct costs, taxes, general O&P, RCV, depreciation, ACV, deductible, limits and prior payments.\n- [ ] Reconcile every difference to the memo; obtain the authorized sender’s approval.\n\nNo action in this file authorizes sending or uploading a claim.\n'
    appendix=banner+'# Indexed evidence appendix\n\n| Exhibit | Document | Page | Description | sha256 | Claims |\n|---|---|---:|---|---|---|\n'
    docs={d['id']:d for d in case['documents']}
    for e in case['evidence']:
        d=docs[e['doc_id']]; claims=', '.join(g['claim_id'] for g in groups if e['id'] in g['source_ids'])
        appendix+=f"| {e['id']} | {d['id']} | {e['page']} | {clean(e['description'])} | {d['sha256']} | {claims} |\n"
    appendix+='\n## Field-level source index\n\n| Line.field | Value | Raw text | Document/page | Pixel crop | Verification |\n|---|---|---|---|---|---|\n'
    for line in case['lines']:
        for name in ['quantity','unit_price','reported_total']:
            f=line[name];s=f['source']
            appendix+=f"| {line['id']}.{name} | {clean(f['value'])} | {clean(f['raw_text'])} | {s['doc_id']} / {s['page']} | {s['bbox']} | {f['verification']} |\n"
    appendix+='\nOriginals are supplied in fixtures/originals. Crop coordinates refer to each synthetic SVG’s 1500 × 800 canvas. Review notes are a page-one text exhibit. No real client evidence is present.\n'
    return {'reconciliation_memo.md':memo,'operator_checklist.md':checklist,'cover_letter.md':letter,'evidence_appendix.md':appendix}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case');p.add_argument('--source-root',required=True);p.add_argument('--out-dir',required=True);a=p.parse_args()
    out=Path(a.out_dir)
    if out.resolve().is_relative_to(Path(a.source_root).resolve()):
        p.error('Output directory must be outside the source root.')
    if any((out/name).resolve()==Path(a.case).resolve() for name in ['report.json','reconciliation_memo.md','operator_checklist.md','cover_letter.md','evidence_appendix.md']):
        p.error('Output would overwrite the case input.')
    try:
        case=load_case(a.case);report=reconcile(case,a.source_root)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        case={};report={'status':'blocked','release_allowed':False,'totals':None,'issues':[{'code':'E_INPUT','ref':'case','message':str(exc)}]}
    out.mkdir(parents=True,exist_ok=True)
    for name,content in render(case,report).items():(out/name).write_text(content,encoding='utf-8')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='draft' else 2

if __name__=='__main__':raise SystemExit(main())
