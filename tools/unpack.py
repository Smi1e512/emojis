#!/usr/bin/env python3
"""Unpack all bundled images and verify every image SHA-256 (standard library only)."""
import hashlib, json, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def unpack():
    manifest = json.loads((ROOT/'manifest.json').read_text())
    expected = {entry['path']:entry['sha256'] for entry in manifest}
    found = set()
    for bundle in sorted((ROOT/'packs').glob('*/*.zip')):
        with zipfile.ZipFile(bundle) as archive:
            for member in archive.infolist():
                if member.filename not in expected or member.filename in found:
                    raise ValueError(f'Unexpected or duplicate archive member: {member.filename}')
                target = (ROOT/member.filename).resolve()
                if not target.is_relative_to(ROOT): raise ValueError('Unsafe archive path')
                data = archive.read(member)
                if hashlib.sha256(data).hexdigest() != expected[member.filename]:
                    raise ValueError(f'Checksum mismatch: {member.filename}')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                found.add(member.filename)
    if found != set(expected): raise ValueError(f'{len(set(expected)-found)} images are missing')
    print(f'Unpacked and verified {len(found)} images.')

if __name__ == '__main__': unpack()
