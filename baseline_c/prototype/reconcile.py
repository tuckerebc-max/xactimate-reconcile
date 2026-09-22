"""Synthetic-only offline direct-cost reconciliation; Python standard library only."""
import argparse
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP, localcontext
import hashlib
import json
from pathlib import Path
import re
import sys

VERSION = 'c-prototype/0.1'
DECIMAL = re.compile(r'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,8})?$')
CENT = Decimal('0.01')
UNITS = {'SF': ('area', Decimal(1)), 'SQ': ('area', Decimal(100)), 'LF': ('length', Decimal(1)), 'EA': ('count', Decimal(1))}
UNKNOWN_FINANCE = ['taxes', 'general_overhead', 'general_profit', 'RCV', 'depreciation', 'recoverable_depreciation', 'ACV', 'deductible', 'limits', 'prior_payments', 'net_payable']


def money(value):
    return format(value.quantize(CENT, rounding=ROUND_HALF_UP), '.2f')


def reconcile(case, source_root=None):
    """Return a held draft or blocked report. Review metadata is an assertion, not visual verification."""
    issues = []
    result = {'schema_version': VERSION, 'status': 'blocked', 'release_allowed': False,
              'release_reason': 'Synthetic research prototype; human and licensed-software verification outstanding.',
              'issues': issues, 'groups': [], 'totals': None, 'unmapped_lines': [],
              'financial_bridge': dict.fromkeys(UNKNOWN_FINANCE), 'source_checks': [],
              'limitations': ['Direct pre-tax costs only.', 'Duplicates detected only through declared work components.',
                              'Source review metadata is not authenticated human approval.', 'No Xactimate estimate generated.']}
    from .contracts import validate_shape
    for error in validate_shape(case):
        issues.append({'code': 'E_SCHEMA', 'ref': 'case', 'message': error})
    if issues: return result
    def flag(code, ref, message):
        issues.append({'code': code, 'ref': ref, 'message': message})
    def required(obj, names, ref):
        if not isinstance(obj, dict):
            flag('E_SCHEMA', ref, 'Expected an object.'); return False
        missing = [n for n in names if n not in obj]
        if missing:
            flag('E_SCHEMA', ref, 'Missing fields: ' + ', '.join(missing)); return False
        return True
    if not required(case, ['schema_version', 'synthetic', 'case_id', 'currency', 'rounding', 'financial_basis', 'documents', 'evidence', 'lines', 'groups'], 'case'):
        return result
    if case['schema_version'] != VERSION: flag('E_SCHEMA', 'case', 'Unsupported schema version.')
    if case['synthetic'] is not True: flag('E_REAL_DATA', 'case', 'Only synthetic fixtures are accepted.')
    if case['currency'] != 'USD' or case['financial_basis'] != 'direct_pre_tax': flag('E_BASIS', 'case', 'Only USD direct pre-tax comparisons are supported.')
    if case['rounding'] != 'ROUND_HALF_UP': flag('E_ROUNDING', 'case', 'ROUND_HALF_UP must be explicit.')
    for name in ['documents', 'evidence', 'lines', 'groups']:
        if not isinstance(case[name], list) or not case[name]: flag('E_SCHEMA', name, 'A nonempty array is required.')
    if issues: return result
    def index(items, key, label):
        out = {}
        for i, item in enumerate(items):
            if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip():
                flag('E_SCHEMA', f'{label}[{i}]', f'Nonempty {key} required.'); continue
            if item[key] in out: flag('E_DUPLICATE_ID', item[key], 'Identifiers must be unique.')
            out[item[key]] = item
        return out
    docs = index(case['documents'], 'id', 'documents')
    lines = index(case['lines'], 'id', 'lines')
    exhibits = index(case['evidence'], 'id', 'evidence')
    groups = index(case['groups'], 'claim_id', 'groups')
    if issues: return result
    root = Path(source_root).resolve() if source_root is not None else None
    if root is None: flag('E_SOURCE_ROOT', 'case', 'Explicit source root required for hash verification.')
    for did, doc in docs.items():
        if not required(doc, ['role', 'path', 'sha256', 'page_count', 'received_pages', 'version', 'date', 'kind', 'estimate_complete', 'synthetic', 'reported_direct_total'], did): continue
        if doc['synthetic'] is not True: flag('E_REAL_DATA', did, 'Document must be explicitly synthetic.')
        if doc['role'] not in ['baseline', 'proposed', 'evidence']: flag('E_SCHEMA', did, 'Unknown document role.')
        n = doc['page_count']
        if type(n) is not int or not 1 <= n <= 10000:
            flag('E_SCHEMA', did, 'Invalid page count.'); continue
        if doc['received_pages'] != list(range(1, n+1)) or doc['estimate_complete'] is not True: flag('E_INCOMPLETE', did, 'Missing, reordered or incomplete source pages.')
        if not isinstance(doc['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', doc['sha256']):
            flag('E_SOURCE_HASH', did, 'Invalid SHA-256.'); continue
        if root is not None:
            try:
                if not isinstance(doc['path'], str): raise ValueError('Invalid path.')
                p = (root / doc['path']).resolve()
                if Path(doc['path']).is_absolute() or not p.is_relative_to(root):
                    flag('E_SOURCE_PATH', did, 'Source path escapes the supplied root.'); continue
                digest = hashlib.sha256(p.read_bytes()).hexdigest()
                if digest != doc['sha256']: flag('E_SOURCE_HASH', did, 'Original bytes differ from the recorded hash.')
                result['source_checks'].append({'doc_id': did, 'sha256': digest, 'match': digest == doc['sha256']})
            except (OSError, ValueError, TypeError): flag('E_SOURCE_PATH', did, 'Source is missing or unreadable.')
    if issues: return result
    def source(ref, where):
        if not required(ref, ['doc_id', 'page', 'bbox', 'coordinate_space', 'image_size', 'method'], where): return
        doc = docs.get(ref['doc_id'])
        if not doc or type(ref['page']) is not int or ref['page'] not in doc['received_pages']: flag('E_SOURCE_REF', where, 'Unknown document/page.')
        box, size = ref['bbox'], ref['image_size']
        numeric = lambda v: type(v) in [int, float] and abs(v) < 1e9
        if (ref['coordinate_space'] != 'pixels' or not isinstance(box, list) or len(box) != 4 or not isinstance(size, list) or len(size) != 2 or not all(numeric(v) for v in box+size) or not (0 <= box[0] < box[2] <= size[0] and 0 <= box[1] < box[3] <= size[1])):
            flag('E_COORDINATES', where, 'A bounded pixel crop and image dimensions are required.')
        if ref['method'] not in ['manual_synthetic', 'native_text', 'local_ocr', 'vision']: flag('E_SCHEMA', where, 'Unknown extraction method.')
    def number(field, where):
        if not required(field, ['value', 'raw_text', 'alternatives', 'resolution', 'verification', 'reviewer', 'reviewed_at', 'source'], where): return None
        source(field['source'], where)
        if field['verification'] != 'synthetic_checked' or not field['reviewer'] or not field['reviewed_at']: flag('E_REVIEW', where, 'Recorded synthetic source check required.')
        if not isinstance(field['alternatives'], list): flag('E_SCHEMA', where, 'Alternatives must be an array.')
        elif field['alternatives'] and not field['resolution']: flag('E_AMBIGUOUS', where, 'Retained alternatives need an explicit resolution.')
        value = field['value']
        if value is None:
            flag('E_UNKNOWN', where, 'Unknown number is not zero.'); return None
        if not isinstance(value, str) or not DECIMAL.fullmatch(value):
            flag('E_DECIMAL', where, 'Use a bounded nonnegative decimal string, without exponent or separators.'); return None
        return Decimal(value)
    for eid, ex in exhibits.items():
        if not required(ex, ['doc_id', 'page', 'description'], eid): continue
        doc = docs.get(ex['doc_id'])
        if not doc or type(ex['page']) is not int or ex['page'] not in doc['received_pages']: flag('E_SOURCE_REF', eid, 'Unknown exhibit document/page.')
    parsed, work_seen = {}, {}
    for lid, line in lines.items():
        if not required(line, ['side', 'description', 'specification', 'roof_location', 'quantity', 'unit', 'unit_price', 'reported_total', 'financial_basis', 'area_basis', 'geometry', 'work_components', 'quote_inclusions', 'source'], lid): continue
        if line['side'] not in ['baseline', 'proposed']: flag('E_SCHEMA', lid, 'Unknown comparison side.')
        source(line['source'], lid)
        if line['financial_basis'] != case['financial_basis']: flag('E_BASIS', lid, 'Financial bases differ.')
        unit = line['unit']
        if unit not in UNITS: flag('E_UNIT', lid, 'Unsupported unit.'); continue
        if (unit in ['SF', 'SQ'] and line['area_basis'] not in ['roof_surface', 'plan']) or (unit not in ['SF', 'SQ'] and line['area_basis'] != 'not_area'): flag('E_AREA_BASIS', lid, 'Unit and area basis are inconsistent.')
        geom = line['geometry']
        if required(geom, ['slope_included', 'waste_included', 'apply_slope', 'apply_waste'], lid):
            if any(type(geom[x]) is not bool for x in ['slope_included', 'waste_included', 'apply_slope', 'apply_waste']): flag('E_SCHEMA', lid, 'Geometry flags must be booleans.')
            for adjustment in ['slope', 'waste']:
                if geom['apply_'+adjustment]: flag('E_DOUBLE_'+adjustment.upper() if geom[adjustment+'_included'] else 'E_TRANSFORM_UNSUPPORTED', lid, 'Geometry transforms require a separately reviewed measurement step.')
        q = number(line['quantity'], lid+'.quantity'); p = number(line['unit_price'], lid+'.unit_price'); t = number(line['reported_total'], lid+'.reported_total')
        if all(x is not None for x in [q, p, t]):
            with localcontext() as ctx:
                ctx.prec = 60
                if Decimal(money(q*p)) != t: flag('E_LINE_TOTAL', lid, 'Quantity times unit price differs from the stated total after cent rounding.')
            if t != t.quantize(CENT): flag('E_LINE_TOTAL', lid, 'Reported line total must be cent precise.')
            factor = UNITS[unit][1]
            parsed[lid] = {'quantity': q*factor, 'unit_price': p/factor, 'total': t, 'dimension': UNITS[unit][0]}
        components, inclusions = line['work_components'], line['quote_inclusions']
        if not isinstance(components, list) or not components or not isinstance(inclusions, list) or not all(isinstance(x, str) and x for x in components+inclusions):
            flag('E_SCHEMA', lid, 'Declared work components and inclusion array required.'); continue
        for component in set(components+inclusions):
            key = (line['side'], line['roof_location'], component)
            if key in work_seen: flag('E_DUPLICATE_WORK', lid, 'Work also appears in '+work_seen[key]+': '+component)
            else: work_seen[key] = lid
    for side in ['baseline', 'proposed']:
        estimate_docs = [d for d in docs.values() if d['role'] == side]
        if len(estimate_docs) != 1:
            flag('E_ESTIMATE_VERSION', side, 'Select exactly one active estimate per side.'); continue
        d = estimate_docs[0]; footer = number(d['reported_direct_total'], d['id']+'.reported_direct_total')
        if footer is not None and all(lid in parsed for lid,l in lines.items() if l.get('side') == side):
            actual = sum((parsed[lid]['total'] for lid,l in lines.items() if l.get('side') == side), Decimal(0))
            if footer != actual: flag('E_ESTIMATE_TOTAL', d['id'], 'Declared direct subtotal differs from the sum of supplied lines.')
    used = Counter()
    for cid,g in groups.items():
        if not required(g, ['baseline', 'proposed', 'roof_location', 'change_type', 'mapping_rationale', 'source_ids', 'scope_support', 'coverage', 'counterargument', 'disposition', 'absence_verified'], cid): continue
        if not g['mapping_rationale']: flag('E_MAPPING', cid, 'Record the manual mapping rationale.')
        if not g['counterargument']: flag('E_ARGUMENT', cid, 'Record a material counterargument.')
        if not isinstance(g['baseline'], list) or not isinstance(g['proposed'], list):
            flag('E_SCHEMA', cid, 'Mapping sides must be arrays.'); continue
        if not g['baseline'] and not g['proposed']: flag('E_MAPPING', cid, 'An empty group has no scope.')
        if len(g['baseline']) > 1 and len(g['proposed']) > 1: flag('E_MAPPING_TOPOLOGY', cid, 'Split many-to-many into disjoint reviewed groups.')
        if not g['baseline'] or not g['proposed']:
            if g['change_type'] != 'scope' or g['absence_verified'] is not True: flag('E_ABSENCE', cid, 'Scope addition/removal requires verified absence on the complete opposite estimate.')
        members = []
        for side in ['baseline', 'proposed']:
            for lid in g[side]:
                if not isinstance(lid, str) or lid not in lines:
                    flag('E_MAPPING', cid, 'Mapping names an unknown line.'); continue
                used[lid] += 1
                if lines[lid].get('side') != side: flag('E_MAPPING', cid, 'Line belongs to the opposite side.')
                if lines[lid].get('roof_location') != g['roof_location']: flag('E_LOCATION', cid, 'Roof locations differ.')
                members.append(lines[lid])
        dims = {parsed[l['id']]['dimension'] for l in members if l['id'] in parsed}
        if len(dims)>1: flag('E_UNIT', cid, 'Mapped units have incompatible dimensions.')
        if len({l.get('area_basis') for l in members})>1: flag('E_AREA_BASIS', cid, 'Plan area and roof surface differ.')
        if len({(l.get('geometry',{}).get('slope_included'),l.get('geometry',{}).get('waste_included')) for l in members})>1: flag('E_AREA_BASIS', cid, 'Slope/waste inclusion states differ.')
        if not isinstance(g['source_ids'],list) or not g['source_ids']: flag('E_SOURCE_REF', cid, 'Evidence references required.')
        else:
            for eid in g['source_ids']:
                if eid not in exhibits: flag('E_SOURCE_REF', cid, 'Unknown evidence ID: '+str(eid))
        scope = g['scope_support']
        if not isinstance(scope,dict) or scope.get('status')!='supported' or not scope.get('source_ids'): flag('E_SCOPE', cid, 'Insufficient scope evidence: hold this issue.')
        elif any(eid not in exhibits for eid in scope['source_ids']): flag('E_SOURCE_REF', cid, 'Unknown scope evidence.')
        coverage = g['coverage']
        if not isinstance(coverage,dict) or coverage.get('status')!='unknown' or coverage.get('source_ids'): flag('E_COVERAGE', cid, 'Coverage determination is outside this prototype; retain unknown.')
        typ = g['change_type']
        if typ not in ['quantity_price','bundle','scope','specification_bundle']: flag('E_SCHEMA', cid, 'Unknown change type.')
        if typ=='quantity_price':
            if len(g['baseline'])!=1 or len(g['proposed'])!=1: flag('E_MAPPING', cid, 'Quantity/price decomposition requires one-to-one lines.')
            elif all(lid in lines for lid in g['baseline']+g['proposed']):
                b,p = lines[g['baseline'][0]],lines[g['proposed'][0]]
                if b.get('specification')!=p.get('specification') or set(b.get('work_components',[]))!=set(p.get('work_components',[])): flag('E_SPECIFICATION', cid, 'Separate scope/specification before quantity/price attribution.')
    for lid,count in used.items():
        if count>1: flag('E_LINE_REUSED', lid, 'A line can contribute to exactly one mapping.')
    result['unmapped_lines'] = sorted(set(lines)-set(used))
    if result['unmapped_lines']: flag('E_UNMAPPED', 'case', 'Unmapped lines preserved; complete net request blocked.')
    if issues: return result
    with localcontext() as ctx:
        ctx.prec = 60
        for cid,g in groups.items():
            bt=sum((parsed[lid]['total'] for lid in g['baseline']),Decimal(0));pt=sum((parsed[lid]['total'] for lid in g['proposed']),Decimal(0));delta=pt-bt
            components=dict.fromkeys(['quantity','price','scope','specification_bundle','bundle','rounding'],Decimal(0))
            if g['change_type']=='quantity_price':
                b,p=parsed[g['baseline'][0]],parsed[g['proposed'][0]]
                components['quantity']=Decimal(money((p['quantity']-b['quantity'])*b['unit_price']))
                components['price']=Decimal(money(p['quantity']*(p['unit_price']-b['unit_price'])))
                components['rounding']=delta-sum(components.values())
            else: components[g['change_type']]=delta
            result['groups'].append({'claim_id':cid,'baseline':list(g['baseline']),'proposed':list(g['proposed']),'roof_location':g['roof_location'],'baseline_direct':money(bt),'proposed_direct':money(pt),'delta':money(delta),'components':{k:money(v) for k,v in components.items()},'action':'increase' if delta>0 else 'reduce' if delta<0 else 'retain_baseline','disposition':g['disposition'],'source_ids':list(g['source_ids']),'coverage_status':'unknown','counterargument':g['counterargument'],'mapping_rationale':g['mapping_rationale']})
        bt=sum((p['total'] for lid,p in parsed.items() if lines[lid]['side']=='baseline'),Decimal(0));pt=sum((p['total'] for lid,p in parsed.items() if lines[lid]['side']=='proposed'),Decimal(0))
        deltas=[Decimal(g['delta']) for g in result['groups']]
        result['totals']={'baseline_direct':money(bt),'proposed_direct':money(pt),'delta_direct':money(pt-bt),'upward_changes':money(sum((d for d in deltas if d>0),Decimal(0))),'downward_changes':money(sum((d for d in deltas if d<0),Decimal(0))),'unchanged_groups':sum(d==0 for d in deltas)}
    result['status']='draft';result['financial_bridge']['direct_costs']=result['totals']['proposed_direct']
    return result


def _no_duplicate_keys(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ValueError('Duplicate JSON key: '+key)
        out[key]=value
    return out


def load_case(path):
    def bad_constant(value): raise ValueError('Nonfinite JSON constant: '+value)
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_no_duplicate_keys,parse_constant=bad_constant)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case');parser.add_argument('--source-root',required=True);parser.add_argument('--out',required=True)
    args=parser.parse_args(argv)
    try: report=reconcile(load_case(args.case),args.source_root)
    except (ValueError,TypeError,KeyError,OSError) as exc:
        report={'schema_version':VERSION,'status':'blocked','release_allowed':False,'totals':None,'groups':[],'issues':[{'code':'E_INPUT','ref':'case','message':str(exc)}]}
    out=Path(args.out)
    if out.resolve()==Path(args.case).resolve() or out.resolve().is_relative_to(Path(args.source_root).resolve()):
        print('Refusing to overwrite input.',file=sys.stderr);return 2
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0 if report['status']=='draft' else 2


if __name__=='__main__': raise SystemExit(main())
