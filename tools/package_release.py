"""Build a portable repository ZIP with a SHA-256 file manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','__pycache__','.venv','.pytest_cache','cases','private','outputs','build','dist'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args();target=Path(args.output).resolve()
    files=[]
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if set(rel.parts)&EXCLUDED or p.name.startswith('.env') or p.suffix in ('.pyc','.pyo','.zip') or p.name=='RELEASE_MANIFEST.json':continue
        if p.is_symlink():raise ValueError('Do not package a symlink: '+str(rel))
        if p.is_file():files.append(p)
    manifest={'release':'0.1.0','artifact':'supervised draft repository','files':{
        p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
    m=ROOT/'RELEASE_MANIFEST.json';m.write_text(json.dumps(manifest,indent=2)+'\n');files.append(m)
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:z.write(p,'xactimate-reconcile/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as z:
        bad=z.testzip()
        if bad:raise ValueError('Archive CRC failure: '+bad)
    print(json.dumps({'path':str(target),'files':len(files),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':main()
