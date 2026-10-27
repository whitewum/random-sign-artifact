"""Verify release integrity and English-only text without external dependencies."""
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'audit/SHA256SUMS.json'
IGNORE={'.git','.venv','.cache','__pycache__','bin','outputs'}
def files():
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if not p.is_file() or any(s in IGNORE for s in rel.parts): continue
        if p==MANIFEST or p.suffix in ('.pyc','.pdf','.png') or p.name in ('.DS_Store','fig-scale.csv'): continue
        yield p

def main():
    errors=[]; hashes={}
    for p in files():
        rel=str(p.relative_to(ROOT));raw=p.read_bytes()
        hashes[rel]=hashlib.sha256(raw).hexdigest()
        try: text=raw.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'Unexpected non-text release file: {rel}');continue
        if re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\U00020000-\U000323af]',text):
            errors.append(f'CJK text: {rel}')
        if re.search(r'/(?:Users|home|public/home)/[A-Za-z0-9_]',text):
            errors.append(f'Machine-specific home path: {rel}')
    if errors: raise SystemExit('\n'.join(errors))
    if sys.argv[1:]==['--write']:
        MANIFEST.write_text(json.dumps(hashes,indent=2)+'\n')
        print(f'Wrote hashes for {len(hashes)} files.');return
    expected=json.loads(MANIFEST.read_text())
    for p in sorted(set(expected)|set(hashes)):
        if expected.get(p)!=hashes.get(p): errors.append(f'Integrity mismatch: {p}')
    if errors: raise SystemExit('\n'.join(errors))
    print(f'PASS: {len(hashes)} file hashes, English-only text, and portable home paths.')
if __name__=='__main__': main()
