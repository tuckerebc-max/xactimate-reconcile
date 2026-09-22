"""Value-bound review receipts. These record local attestations, not authenticated identity."""
import csv
import html
from pathlib import Path
from .store import read_json, write_json, atomic_text, within, now, invalidate
from .engine import review_subjects


def prepare_review(root):
    root = Path(root)
    case = read_json(root / 'case.json')
    subjects = review_subjects(case)
    docs = {d['id']: d for d in case['documents']}
    review_dir = root / 'reviews'
    review_dir.mkdir(exist_ok=True)
    csv_path = review_dir / 'decisions.csv'
    # Never overwrite decisions the person has already entered.
    if csv_path.exists():
        csv_path = review_dir / ('decisions-' + now().replace(':','').replace('.','') + '.csv')
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['subject', 'value', 'unit', 'fingerprint', 'decision'])
        writer.writeheader()
        for sid, field in subjects.items():
            writer.writerow({'subject': sid, 'value': field.get('value'), 'unit': field.get('unit'),
                             'fingerprint': field['fingerprint'], 'decision': ''})
    blocks = ['<!doctype html><html lang="en"><meta charset="utf-8"><title>Source review</title>',
              '<style>body{font:16px system-ui;max-width:1000px;margin:40px auto;padding:0 20px;color:#172331}section{border-top:1px solid #ccd4db;padding:20px 0}img{max-width:100%;border:1px solid #ccd4db}code{overflow-wrap:anywhere}p{line-height:1.5}</style>',
              '<h1>Source review</h1><p>Check each value, unit and source location. Enter confirm or reject in the decision column of the accompanying CSV. A high OCR score is not a review. Import only decisions you actually made. This records an attestation; it does not authenticate identity.</p>']
    crops = review_dir / 'crops'
    crops.mkdir(exist_ok=True)
    for index, (sid, field) in enumerate(subjects.items()):
        source = field.get('source') or {}
        doc = docs.get(source.get('doc_id'), {})
        blocks.append('<section><h2>' + html.escape(sid) + '</h2><p>Value: <strong>' + html.escape(str(field.get('value'))) + '</strong> ' + html.escape(str(field.get('unit') or '')) + '</p>')
        blocks.append('<p>Raw text: ' + html.escape(str(field.get('raw_text', ''))) + '<br>Document: ' + html.escape(str(source.get('doc_id'))) + ' / page ' + html.escape(str(source.get('page'))) + '</p>')
        try:
            page = next(p for p in doc.get('pages', []) if p['page'] == source['page'])
            path = within(root, page['image_path'])
            from PIL import Image
            with Image.open(path) as img:
                box = source['bbox']
                if not (len(box) == 4 and 0 <= box[0] < box[2] <= img.width and 0 <= box[1] < box[3] <= img.height):
                    raise ValueError('Invalid crop')
                crop = crops / f'{index+1:04}.png'
                img.crop(tuple(box)).save(crop)
            blocks.append(f'<img alt="Source crop for {html.escape(sid)}" src="crops/{crop.name}">')
        except (ImportError, KeyError, TypeError, ValueError, OSError, StopIteration):
            blocks.append('<p><strong>Crop unavailable. Open the original and correct the page locator before confirming.</strong></p>')
        blocks.append('<p>Fingerprint: <code>' + html.escape(field['fingerprint']) + '</code></p></section>')
    blocks.append('</html>')
    atomic_text(review_dir / 'source-review.html', '\n'.join(blocks))
    return {'html': str(review_dir / 'source-review.html'), 'decisions': str(csv_path), 'subjects': len(subjects)}


def import_decisions(root, file, reviewer, kind='human'):
    root = Path(root)
    if not reviewer.strip() or kind not in ('human', 'ai', 'synthetic'):
        raise ValueError('A reviewer name and human, ai, or synthetic kind are required.')
    case = read_json(root / 'case.json')
    if kind == 'synthetic' and not case['synthetic']:
        raise ValueError('Synthetic review is confined to synthetic examples.')
    subjects = review_subjects(case)
    pending = []
    with Path(file).open(newline='', encoding='utf-8-sig') as stream:
        for row in csv.DictReader(stream):
            decision = (row.get('decision') or '').strip()
            if not decision:
                continue
            sid = row.get('subject')
            if sid not in subjects or decision not in ('confirm', 'reject'):
                raise ValueError('Unknown subject or invalid decision.')
            if row.get('fingerprint') != subjects[sid]['fingerprint']:
                raise ValueError(f'Stale review for {sid}; regenerate the source review.')
            expected_value = subjects[sid].get('value')
            if row.get('value','') != ('' if expected_value is None else str(expected_value)) or row.get('unit','') != str(subjects[sid].get('unit') or ''):
                raise ValueError(f'The displayed value or unit changed for {sid}; edit the source ledger and regenerate the review sheet instead.')
            pending.append({'subject': sid, 'fingerprint': row['fingerprint'], 'decision': decision,
                            'kind': kind, 'reviewer': reviewer.strip(), 'reviewed_at': now()})
    records = read_json(root / 'reviews/records.json')
    records.extend(pending)
    write_json(root / 'reviews/records.json', records)
    invalidate(root, 'Source review records changed.')
    return {'imported': len(pending), 'kind': kind, 'identity_authenticated': False}
