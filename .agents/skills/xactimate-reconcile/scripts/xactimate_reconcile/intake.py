"""PDF/image/text intake and local extraction; no automatic table-to-fact promotion."""
from __future__ import annotations
import csv
import importlib.util
import io
from pathlib import Path
import shutil
import subprocess
import sys
from .store import read_json, write_json, sha_file, now, within, invalidate

MAX_BYTES = 100 * 1024 * 1024
MAX_PAGES = 300
IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp'}


def capabilities():
    return {'python': sys.version.split()[0], 'libraries': {k: importlib.util.find_spec(k) is not None for k in ('fitz', 'PIL', 'docx', 'reportlab')},
            'executables': {k: shutil.which(k) for k in ('tesseract', 'pdftotext', 'soffice')},
            'network_required': False, 'note': 'Availability is not an OCR accuracy or Xactimate compatibility test.'}


def _inventory(path):
    suffix = Path(path).suffix.lower()
    if suffix == '.pdf':
        try:
            import fitz
        except ImportError as e:
            raise ValueError('PDF intake needs PyMuPDF; install requirements-optional.txt or provide page images.') from e
        with fitz.open(path) as doc:
            if doc.needs_pass:
                raise ValueError('Encrypted PDF: provide an authorized unlocked copy.')
            n = len(doc)
        return n, 'application/pdf'
    if suffix in IMAGE_EXT:
        try:
            from PIL import Image
        except ImportError as e:
            raise ValueError('Image intake needs Pillow.') from e
        with Image.open(path) as img:
            n = getattr(img, 'n_frames', 1)
        return n, 'image/' + ('jpeg' if suffix in ('.jpg', '.jpeg') else suffix[1:])
    if suffix in ('.txt', '.csv'):
        Path(path).read_text(encoding='utf-8')
        return 1, 'text/plain'
    if suffix == '.esx':
        return 1, 'application/octet-stream'
    raise ValueError('Supported intake: PDF, PNG/JPEG/TIFF/WebP, UTF-8 TXT/CSV, or ESX preserved for the operator.')


def add_document(root, source, role, version='v1', expected_pages=None):
    root, source = Path(root).resolve(), Path(source).resolve()
    if role not in ('baseline', 'proposed', 'evidence', 'policy', 'operator'):
        raise ValueError('Unknown document role.')
    if not source.is_file() or not 0 < source.stat().st_size <= MAX_BYTES:
        raise ValueError('Source must be a nonempty file of at most 100 MiB.')
    if expected_pages is not None and not 1 <= expected_pages <= MAX_PAGES:
        raise ValueError('Expected pages must be between 1 and 300.')
    n, mime = _inventory(source)
    if not 0 < n <= MAX_PAGES:
        raise ValueError('Document must contain 1 to 300 pages.')
    manifest = read_json(root / 'manifest.json')
    digest = sha_file(source)
    did = 'D-' + digest[:16] + '-' + role
    existing = next((d for d in manifest['documents'] if d['id'] == did), None)
    if existing:
        if sha_file(within(root, existing['path'])) != digest:
            raise ValueError('Stored original changed; restore the original before continuing.')
        return existing
    rel = 'originals/' + did + source.suffix.lower()
    target = within(root, rel)
    if target.exists():
        raise ValueError('Original destination already exists.')
    with source.open('rb') as src, target.open('xb') as dst:
        shutil.copyfileobj(src, dst)
    if sha_file(target) != digest:
        raise ValueError('Source changed during import; imported document is not accepted.')
    case = read_json(root / 'case.json')
    doc = {'id': did, 'role': role, 'path': rel, 'sha256': digest, 'page_count': n,
           'received_pages': list(range(1, n + 1)), 'version': version, 'date': now()[:10],
           'kind': 'estimate' if role in ('baseline', 'proposed') else role,
           'estimate_complete': expected_pages is None or expected_pages == n,
           'synthetic': case['synthetic'], 'reported_direct_total': None, 'pages': [],
           'original_name': source.name, 'mime_type': mime, 'receipt_time': now(),
           'inspection_limits': 'File page count verified; a person must confirm the full intended document was supplied.'}
    if expected_pages is not None and expected_pages != n:
        doc['inspection_limits'] += f' Expected {expected_pages} pages; received {n}.'
    manifest['documents'].append(doc)
    manifest['events'].append({'at': now(), 'action': 'intake', 'document_id': did})
    # Preserve superseded originals in manifest; do not silently select a second estimate.
    if role not in ('baseline', 'proposed') or not any(d['role'] == role for d in case['documents']):
        case['documents'].append(doc)
    write_json(root / 'manifest.json', manifest)
    write_json(root / 'case.json', case)
    invalidate(root, 'A source document was added.')
    return doc


def _ocr(image_path, enabled):
    if not enabled:
        return '', [], 'not_requested'
    exe = shutil.which('tesseract')
    if not exe:
        return '', [], 'TOOL_UNAVAILABLE: tesseract; use vision/manual reading and source review.'
    result = subprocess.run([exe, str(image_path), 'stdout', '-l', 'eng', '--psm', '6', 'tsv'],
                            capture_output=True, text=True, timeout=90, check=False)
    if result.returncode:
        return '', [], 'OCR_ERROR: ' + result.stderr[-500:]
    words = []
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter='\t'):
        if not row.get('text', '').strip():
            continue
        x, y, w, h = (int(row[k]) for k in ('left', 'top', 'width', 'height'))
        words.append({'text': row['text'], 'bbox': [x, y, x+w, y+h], 'confidence': row.get('conf'),
                      'line': [row.get(k) for k in ('block_num', 'par_num', 'line_num')]})
    lines = {}
    for word in words:
        lines.setdefault(tuple(word['line']), []).append(word['text'])
    return '\n'.join(' '.join(v) for v in lines.values()), words, 'local_ocr'


def extract_document(root, document_id, ocr='auto'):
    root = Path(root).resolve()
    if ocr not in ('auto', 'off', 'always'):
        raise ValueError('OCR must be auto, off, or always.')
    manifest = read_json(root / 'manifest.json')
    doc = next((d for d in manifest['documents'] if d['id'] == document_id), None)
    if doc is None:
        raise ValueError('Unknown document ID.')
    source = within(root, doc['path'])
    if sha_file(source) != doc['sha256']:
        raise ValueError('Original hash mismatch. Extraction stopped.')
    out = root / 'derived' / document_id
    out.mkdir(parents=True, exist_ok=True)
    pages = []
    suffix = source.suffix.lower()
    if suffix == '.esx':
        raise ValueError('ESX is preserved for a licensed operator; obtain a readable PDF export for extraction.')
    if suffix in ('.txt', '.csv'):
        text = source.read_text(encoding='utf-8')
        (out / 'page-001.txt').write_text(text, encoding='utf-8')
        pages = [{'page': 1, 'width': 1, 'height': 1, 'text_path': str((out/'page-001.txt').relative_to(root)).replace('\\','/'),
                  'image_path': None, 'method': 'native_text', 'coordinate_space': 'pixels',
                  'note': 'Text exhibit; not a source image for monetary verification.'}]
    else:
        try:
            from PIL import Image, ImageOps
        except ImportError as e:
            raise ValueError('Extraction needs Pillow.') from e
        pdf = None
        img = None
        try:
            if suffix == '.pdf':
                import fitz
                pdf = fitz.open(source)
                count = len(pdf)
            else:
                img = Image.open(source)
                count = getattr(img, 'n_frames', 1)
            for index in range(count):
                image_path = out / f'page-{index+1:03}.png'
                text, words, method = '', [], 'vision'
                transform = {'kind': 'identity', 'scale': 1}
                if pdf is not None:
                    page = pdf[index]
                    scale = 2.0
                    if page.rect.width*page.rect.height*scale*scale > 40_000_000:
                        raise ValueError('Page exceeds the rendering pixel limit.')
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    pix.save(image_path)
                    text = page.get_text('text', sort=True)
                    words = [{'bbox': [v*scale for v in w[:4]], 'text': w[4], 'confidence': None} for w in page.get_text('words', sort=True)]
                    method = 'native_text'
                    transform = {'kind': 'pdf_render', 'scale': scale, 'original_space': 'PDF points', 'rotation': page.rotation}
                else:
                    img.seek(index)
                    if img.width*img.height > 40_000_000:
                        raise ValueError('Image exceeds the 40 megapixel limit.')
                    original_orientation = img.getexif().get(274, 1)
                    normalized = ImageOps.exif_transpose(img).convert('RGB')
                    normalized.save(image_path)
                    transform = {'kind': 'exif_orientation', 'original_orientation': original_orientation,
                                 'original_size': list(img.size), 'derived_size': list(normalized.size)}
                if ocr == 'always' or (ocr == 'auto' and len(text.strip()) < 30):
                    candidate, tokens, outcome = _ocr(image_path, True)
                    if outcome == 'local_ocr':
                        text, words, method = candidate, tokens, outcome
                    else:
                        method = 'vision'
                        transform['ocr_note'] = outcome
                with Image.open(image_path) as rendered:
                    width, height = rendered.size
                text_path = out / f'page-{index+1:03}.txt'
                words_path = out / f'page-{index+1:03}.words.json'
                text_path.write_text(text, encoding='utf-8')
                write_json(words_path, words)
                pages.append({'page': index+1, 'width': width, 'height': height,
                              'image_path': str(image_path.relative_to(root)).replace('\\','/'),
                              'image_sha256': sha_file(image_path), 'text_path': str(text_path.relative_to(root)).replace('\\','/'),
                              'words_path': str(words_path.relative_to(root)).replace('\\','/'),
                              'method': method, 'coordinate_space': 'pixels', 'transform': transform})
        finally:
            if pdf is not None:
                pdf.close()
            if img is not None:
                img.close()
    doc['pages'] = pages
    manifest['events'].append({'at': now(), 'action': 'extract', 'document_id': document_id, 'ocr': ocr})
    case = read_json(root / 'case.json')
    for active in case['documents']:
        if active['id'] == document_id:
            # Keep the analyst's reviewed subtotal field; refresh only extracted page metadata.
            active['pages'] = pages
    write_json(root / 'manifest.json', manifest)
    write_json(root / 'case.json', case)
    invalidate(root, 'Extraction changed; review source locators and prior confirmations.')
    return pages
