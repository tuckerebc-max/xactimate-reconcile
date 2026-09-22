"""Local command-line workflow for Codex, Claude, and a human operator."""
from __future__ import annotations
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import shutil
import sys
import tempfile
import uuid
from . import __version__
from .store import read_json, write_json, atomic_text, sha_file, now, within, init_case, invalidate, input_digest, canonical_hash
from .intake import capabilities, add_document, extract_document
from .engine import reconcile
from .extensions import validate_pack, select_packs

ASSETS = Path(__file__).resolve().parents[2] / 'assets'


def emit(value):
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))


def load_context(root, case):
    packs, warnings = [], []
    paths = list((ASSETS/'extensions').glob('*.json')) + list((Path(root)/'extensions').rglob('pack.json'))
    for path in sorted(paths):
        try:
            pack = read_json(path)
            errors = validate_pack(pack, path.parent)
            if errors:
                warnings.extend(f'{path.name}: {error}' for error in errors)
            else:
                packs.append(pack)
        except (OSError, ValueError, TypeError) as e:
            warnings.append(f'{path.name}: {e}')
    result = select_packs(packs, case)
    result.setdefault('warnings', []).extend(warnings)
    return result


def execution_digest(root):
    runtime = {p.name:sha_file(p) for p in Path(__file__).resolve().parent.glob('*.py')}
    packs = {p.name:sha_file(p) for p in (ASSETS/'extensions').glob('*.json')}
    return canonical_hash({'case':input_digest(root),'runtime':runtime,'bundled_context':packs})


def current_status(root):
    root = Path(root)
    pointer = root/'runs/CURRENT.json'
    if not pointer.exists():
        return {'status':'not_run','reason':'Run the comparison after populating the case ledger.'}
    state = read_json(pointer)
    try:
        if state.get('input_digest') != execution_digest(root):
            state.update(status='stale',reason='Inputs, review records, runtime, or context changed after this run.')
        run = within(root,state['path'])
        manifest = read_json(run/'run_manifest.json')
        for rel, digest in manifest.get('outputs',{}).items():
            path = within(run,rel)
            if not path.exists() or sha_file(path) != digest:
                state.update(status='stale',reason='A generated output changed or is missing. Regenerate the package.')
                break
    except (OSError, ValueError, KeyError) as e:
        state.update(status='stale',reason=str(e))
    return state


def check_intake_integrity(root, case):
    """Link active ledger documents to registered intake originals, including derivatives."""
    manifest = read_json(Path(root)/'manifest.json')
    registered = {d['id']:d for d in manifest.get('documents',[])}
    problems = []
    for d in case.get('documents',[]):
        original = registered.get(d.get('id'))
        if not original or any(original.get(k) != d.get(k) for k in ('path','sha256','role','page_count','received_pages','version','estimate_complete','pages')):
            problems.append({'code':'E_INTAKE_LINK','ref':d.get('id','document'),'message':'Active document does not match its intake record. Import or select the correct source.','severity':'error'})
            continue
        for page in d.get('pages',[]):
            if page.get('image_path'):
                try:
                    if sha_file(within(root,page['image_path'])) != page.get('image_sha256'):
                        raise ValueError('hash mismatch')
                except (OSError,ValueError):
                    problems.append({'code':'E_DERIVATIVE_HASH','ref':d['id'],'message':'A rendered source page changed or is missing. Re-extract and review dependent values.','severity':'error'})
    return problems


def calculate(root):
    root = Path(root)
    case = read_json(root/'case.json')
    reviews = read_json(root/'reviews/records.json')
    report = reconcile(case,root,reviews)
    if isinstance(case,dict) and isinstance(case.get('documents'),list) and all(isinstance(d,dict) for d in case['documents']):
        errors = check_intake_integrity(root,case)
        if errors:
            report['issues'].extend(errors)
            report['status']='blocked'
            report['totals']=None
            report['groups']=[]
    return case,report


def run_case(root, formats=('md',)):
    from .render import render_all
    root=Path(root).resolve()
    invalidate(root,'A new run is in progress.')
    run_id=now().replace(':','').replace('.','')+'-'+uuid.uuid4().hex[:6]
    runs=root/'runs'
    runs.mkdir(exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.building-',dir=runs))
    try:
        fingerprint=execution_digest(root)
        case,report=calculate(root)
        context=load_context(root,case)
        write_json(stage/'report.json',report)
        write_json(stage/'case_snapshot.json',case)
        write_json(stage/'context.json',context)
        rendered=render_all(case,report,root,stage,formats,context,ASSETS)
        if execution_digest(root)!=fingerprint:
            raise ValueError('Inputs changed during rendering; rerun after completing edits.')
        outputs={p.relative_to(stage).as_posix():sha_file(p) for p in stage.rglob('*') if p.is_file()}
        manifest={'schema_version':'xr-run/1.0','run_id':run_id,'version':__version__,'at':now(),
                  'input_digest':fingerprint,'status':report['status'],'outputs':outputs,
                  'formats_requested':list(formats),'render_warnings':rendered['warnings'],
                  'automatic_sending':False,'human_identity_authenticated':False}
        write_json(stage/'run_manifest.json',manifest)
        target=runs/run_id
        stage.rename(target)
        write_json(runs/'CURRENT.json',{'run_id':run_id,'path':target.relative_to(root).as_posix(),
                                      'status':report['status'],'input_digest':fingerprint,'at':now()})
        return {'run':str(target),'status':report['status'],'totals':report.get('totals'),
                'review':report.get('review_summary'),'warnings':rendered['warnings']}
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        invalidate(root,'The last run failed. Previous outputs are historical and must not be used as current.')
        raise


def add_extension(root,path):
    root,path=Path(root),Path(path).resolve()
    if not (root/'case.json').is_file():
        raise ValueError('Initialize the case before adding an extension.')
    (root/'extensions').mkdir(exist_ok=True)
    pack=read_json(path)
    errors=validate_pack(pack,path.parent)
    if errors:
        raise ValueError('; '.join(errors))
    import re
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,64}',pack['version']):
        raise ValueError('Pack version must be a safe filename component.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}',pack['id']):
        raise ValueError('Pack ID must be a portable filename component.')
    dest=root/'extensions'/pack['id']/pack['version']
    if dest.exists():
        raise ValueError('That pack version is already present; create a new version rather than overwriting it.')
    temp=Path(tempfile.mkdtemp(prefix='.pack-',dir=root/'extensions'))
    try:
        write_json(temp/'pack.json',pack)
        for entry in pack['entries']:
            if entry.get('artifact_path'):
                source=within(path.parent,entry['artifact_path'])
                target=within(temp,entry['artifact_path'])
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
        dest.parent.mkdir(parents=True,exist_ok=True)
        temp.rename(dest)
    finally:
        if temp.exists():shutil.rmtree(temp)
    invalidate(root,'An evidence/context extension was added.')
    return {'id':pack['id'],'version':pack['version'],'path':str(dest),'rates_automatically_applied':False}


def operator_check(root, export, direct_total, reviewer, notes):
    root=Path(root)
    state=current_status(root)
    if state['status'] not in ('draft','partial'):
        raise ValueError('A current draft run is required.')
    report=read_json(within(root,state['path'])/'report.json')
    if not report.get('totals'):
        raise ValueError('Resolve incomplete comparison totals before checking a revised estimate.')
    value=Decimal(direct_total)
    if not value.is_finite() or value<0 or value!=value.quantize(Decimal('.01')):
        raise ValueError('Supply a finite nonnegative cent-precise direct subtotal.')
    if not reviewer.strip():raise ValueError('Actual operator name required.')
    export=Path(export)
    if export.suffix.lower() not in ('.pdf','.esx') or not export.is_file() or export.stat().st_size>100*1024*1024:
        raise ValueError('Provide the actual readable PDF or native ESX export, up to 100 MiB.')
    digest=sha_file(export)
    dest=root/'reviews/operator_exports'/(digest+export.suffix.lower())
    dest.parent.mkdir(exist_ok=True)
    if not dest.exists():shutil.copy2(export,dest)
    receipt={'run_id':state['run_id'],'input_digest':state['input_digest'],'reviewer':reviewer,'at':now(),
             'export_sha256':digest,'export_path':dest.relative_to(root).as_posix(),'declared_direct_total':str(value),
             'expected_direct_total':report['totals']['proposed_direct'],
             'matches':value==Decimal(report['totals']['proposed_direct']),'notes':notes,
             'method':'Operator-supplied subtotal and exported bytes; not automatic ESX parsing.',
             'identity_authenticated':False}
    write_json(root/'reviews'/('operator-'+state['run_id']+'.json'),receipt)
    return receipt


def package_review(root,reviewer,kind,decision,notes):
    root=Path(root)
    state=current_status(root)
    if state['status'] not in ('draft','partial'):
        raise ValueError('A current generated draft is required.')
    if not reviewer.strip():raise ValueError('Actual reviewer name required.')
    run=within(root,state['path'])
    manifest=read_json(run/'run_manifest.json')
    case=read_json(run/'case_snapshot.json')
    report=read_json(run/'report.json')
    if decision=='approve':
        if kind!='sender':raise ValueError('Only the sender review can record approval; specialist passes record reviewed or changes_required.')
        if case['synthetic']:raise ValueError('Synthetic examples cannot be approved as a live claim packet.')
        if not report.get('totals'):raise ValueError('Complete the comparison before recording sender approval.')
        review=report.get('review_summary',{})
        if review.get('pending_subjects') or review.get('stale_subjects') or set(review.get('human_confirmed',[]))!=set(review.get('required',[])) or not review.get('required'):
            raise ValueError('All required numeric source readings need current human confirmation.')
        sender=case.get('sender',{})
        evidence_ids={e['id'] for e in case.get('evidence',[])}
        if sender.get('authority_status')!='documented' or not sender.get('authority_evidence_ids') or not set(sender['authority_evidence_ids'])<=evidence_ids:
            raise ValueError('Sender authority remains undocumented.')
        op_path=root/'reviews'/('operator-'+state['run_id']+'.json')
        op=read_json(op_path) if op_path.exists() else {}
        if not op.get('matches') or op.get('input_digest')!=state['input_digest']:
            raise ValueError('A matching current operator export check is required.')
        if sha_file(within(root,op['export_path']))!=op.get('export_sha256'):
            raise ValueError('Operator export changed after its check; repeat the operator check.')
        for specialist in ('claims','legal'):
            prior=root/'reviews'/(specialist+'-'+state['run_id']+'.json')
            if prior.exists() and read_json(prior).get('decision')=='changes_required':
                raise ValueError('An unresolved '+specialist+' review requires changes before sender approval.')
    receipt={'run_id':state['run_id'],'kind':kind,'decision':decision,'reviewer':reviewer,'at':now(),
             'notes':notes,'input_digest':state['input_digest'],'output_hashes':manifest['outputs'],
             'identity_authenticated':False,'automatic_sending_authorized':False}
    write_json(root/'reviews'/(kind+'-'+state['run_id']+'.json'),receipt)
    return receipt


def parser():
    p=argparse.ArgumentParser(description='Reconcile roof estimates and prepare traceable review drafts. No claim submission.')
    p.add_argument('--version',action='version',version=__version__)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='Show available local capabilities.')
    i=sub.add_parser('init',help='Create a private case outside the public repository.')
    i.add_argument('--case-dir',required=True);i.add_argument('--case-id',required=True)
    i.add_argument('--roof-type',choices=['shingle','tile','low_slope'],required=True);i.add_argument('--synthetic',action='store_true')
    i=sub.add_parser('demo',help='Copy a synthetic worked case to a writable private directory.')
    i.add_argument('--roof',choices=['shingle','tile','low_slope'],required=True);i.add_argument('--case-dir',required=True)
    i=sub.add_parser('intake');i.add_argument('--case-dir',required=True);i.add_argument('--file',required=True)
    i.add_argument('--role',choices=['baseline','proposed','evidence','policy','operator'],required=True)
    i.add_argument('--document-version',default='v1');i.add_argument('--expected-pages',type=int)
    i=sub.add_parser('extract');i.add_argument('--case-dir',required=True);i.add_argument('--document-id',required=True);i.add_argument('--ocr',choices=['auto','off','always'],default='auto')
    i=sub.add_parser('select-estimate');i.add_argument('--case-dir',required=True);i.add_argument('--document-id',required=True)
    for name in ['validate','status','review-sheet','context']:
        i=sub.add_parser(name);i.add_argument('--case-dir',required=True)
    i=sub.add_parser('run');i.add_argument('--case-dir',required=True);i.add_argument('--formats',default='md',help='Comma-separated md,docx,pdf')
    i=sub.add_parser('review-import');i.add_argument('--case-dir',required=True);i.add_argument('--file',required=True);i.add_argument('--by',required=True);i.add_argument('--kind',choices=['human','ai','synthetic'],required=True)
    i=sub.add_parser('extension-validate');i.add_argument('--file',required=True)
    i=sub.add_parser('extension-add');i.add_argument('--case-dir',required=True);i.add_argument('--file',required=True)
    i=sub.add_parser('operator-check');i.add_argument('--case-dir',required=True);i.add_argument('--export',required=True);i.add_argument('--direct-total',required=True);i.add_argument('--by',required=True);i.add_argument('--notes',default='')
    i=sub.add_parser('package-review');i.add_argument('--case-dir',required=True);i.add_argument('--by',required=True);i.add_argument('--kind',choices=['claims','legal','sender'],required=True);i.add_argument('--decision',choices=['reviewed','changes_required','approve'],required=True);i.add_argument('--notes',required=True)
    return p


def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=='doctor':emit(capabilities())
        elif args.command=='init':emit(init_case(args.case_dir,args.case_id,args.roof_type,args.synthetic))
        elif args.command=='demo':
            dest=Path(args.case_dir)
            if dest.exists() and any(dest.iterdir()):raise ValueError('Demo destination must be empty.')
            shutil.copytree(ASSETS/'examples'/args.roof,dest,dirs_exist_ok=True)
            for folder in ('runs','extensions','reviews','derived','originals'):
                (dest/folder).mkdir(exist_ok=True)
            emit({'case_dir':str(dest.resolve()),'synthetic':True,'next':'run --case-dir <that directory> --formats md,docx,pdf'})
        elif args.command=='intake':emit(add_document(args.case_dir,args.file,args.role,args.document_version,args.expected_pages))
        elif args.command=='extract':emit(extract_document(args.case_dir,args.document_id,args.ocr))
        elif args.command=='select-estimate':
            root=Path(args.case_dir);manifest=read_json(root/'manifest.json');case=read_json(root/'case.json')
            selected=next((d for d in manifest['documents'] if d['id']==args.document_id),None)
            if not selected or selected['role'] not in ('baseline','proposed'):raise ValueError('Select a registered baseline or proposed estimate.')
            case['documents']=[d for d in case['documents'] if d['role']!=selected['role']]+[selected]
            write_json(root/'case.json',case);invalidate(root,'Active estimate changed; remap and review all affected lines.')
            emit({'selected':selected['id'],'next':'Remap the affected lines and totals; stale references will be refused.'})
        elif args.command=='validate':
            _,report=calculate(args.case_dir);emit(report);return 2 if report['status']=='blocked' else 0
        elif args.command=='run':
            formats=tuple(args.formats.split(','))
            if not set(formats)<= {'md','docx','pdf'}:raise ValueError('Formats are md, docx, pdf.')
            result=run_case(args.case_dir,formats);emit(result);return 2 if result['status']=='blocked' else 0
        elif args.command=='status':emit(current_status(args.case_dir))
        elif args.command=='review-sheet':
            from .review import prepare_review
            emit(prepare_review(args.case_dir))
        elif args.command=='review-import':
            from .review import import_decisions
            emit(import_decisions(args.case_dir,args.file,args.by,args.kind))
        elif args.command=='context':emit(load_context(args.case_dir,read_json(Path(args.case_dir)/'case.json')))
        elif args.command=='extension-validate':
            path=Path(args.file);errors=validate_pack(read_json(path),path.parent);emit({'valid':not errors,'errors':errors});return 2 if errors else 0
        elif args.command=='extension-add':emit(add_extension(args.case_dir,args.file))
        elif args.command=='operator-check':emit(operator_check(args.case_dir,args.export,args.direct_total,args.by,args.notes))
        elif args.command=='package-review':emit(package_review(args.case_dir,args.by,args.kind,args.decision,args.notes))
        return 0
    except (OSError,ValueError,KeyError,TypeError,InvalidOperation) as e:
        if getattr(args,'case_dir',None) and args.command=='run':
            invalidate(args.case_dir,'Run failed: '+str(e))
        print(json.dumps({'status':'error','message':str(e)},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
