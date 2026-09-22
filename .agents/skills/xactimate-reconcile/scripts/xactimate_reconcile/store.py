"""Private local case storage. Original bytes are never rewritten by this package."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}$")


def now():
    return datetime.now(timezone.utc).isoformat()


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def read_json(path):
    p = Path(path)
    if p.stat().st_size > 20 * 1024 * 1024:
        raise ValueError('JSON exceeds the 20 MiB limit.')
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError(f'Duplicate JSON key: {k}')
            out[k] = v
        return out
    def constant(value):
        raise ValueError(f'Non-finite JSON constant: {value}')
    return json.loads(p.read_text(encoding='utf-8'), object_pairs_hook=unique, parse_constant=constant)


def write_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def atomic_text(path, text):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + p.name + '-', dir=p.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, p)
    finally:
        if Path(name).exists():
            Path(name).unlink()


def within(root, relative):
    root = Path(root).resolve()
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Path must remain inside the case directory.')
    resolved = (root / p).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('Path escapes the case directory.')
    return resolved


def init_case(root, case_id, roof_type, synthetic=False):
    if not ID.fullmatch(case_id):
        raise ValueError('Use a short opaque case ID containing letters, digits, dots, colons, underscores or hyphens.')
    if roof_type not in ('shingle', 'tile', 'low_slope'):
        raise ValueError('Unknown roof type.')
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (root / 'case.json').exists() or (root / 'manifest.json').exists():
        raise ValueError('Case already exists; refusing to overwrite it.')
    for name in ('originals', 'derived', 'reviews', 'runs', 'extensions'):
        (root / name).mkdir(exist_ok=True, mode=0o700)
    case = {
        'schema_version': 'xr-case/1.0', 'synthetic': synthetic, 'case_id': case_id,
        'title': 'Roof estimate reconciliation', 'roof_type': roof_type,
        'as_of': now()[:10], 'currency': 'USD', 'rounding': 'ROUND_HALF_UP',
        'financial_basis': 'direct_pre_tax', 'baseline_label': 'Carrier estimate',
        'proposed_label': 'Contractor estimate', 'author_role': 'Technical estimate preparation',
        'price_context': {'list': None, 'month': None, 'location': 'Unconfirmed'},
        'jurisdiction': {'country': 'US', 'state': 'AZ', 'municipality': None, 'verified': False},
        'sender': {'name': '', 'role': 'contractor', 'authority_status': 'unverified', 'authority_evidence_ids': []},
        'documents': [], 'evidence': [], 'lines': [], 'groups': [],
        'financial_adjustments': {'baseline': [], 'proposed': []}, 'payment_scenario': None,
        'notes': 'Technical draft. Confirm active estimate versions, completeness and actual jurisdiction.'
    }
    write_json(root / 'case.json', case)
    write_json(root / 'manifest.json', {'schema_version': 'xr-manifest/1.0', 'case_id': case_id, 'documents': [], 'events': []})
    write_json(root / 'reviews/records.json', [])
    return case


def invalidate(root, reason):
    p = Path(root) / 'runs/CURRENT.json'
    if p.exists():
        state = read_json(p)
        state.update(status='stale', reason=reason, invalidated_at=now())
        write_json(p, state)


def input_digest(root):
    root = Path(root)
    files = [root / 'case.json', root / 'manifest.json', root / 'reviews/records.json']
    files += sorted((root / 'extensions').rglob('*'))
    manifest = read_json(root / 'manifest.json')
    for d in manifest.get('documents', []):
        files.append(within(root, d['path']))
        for page in d.get('pages', []):
            if page.get('image_path'):
                files.append(within(root, page['image_path']))
    pairs = []
    for p in sorted(set(files)):
        if p.is_file():
            if not p.resolve().is_relative_to(root.resolve()):
                raise ValueError('Case dependency escapes its directory.')
            pairs.append((str(p.relative_to(root)).replace('\\', '/'), sha_file(p)))
    return canonical_hash(pairs)
