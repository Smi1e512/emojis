#!/usr/bin/env python3
"""Verify all output dimensions, checksums, animation frames and durations."""
import hashlib,json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'manifest.json').read_text())
for row in manifest:
    path=ROOT/row['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'], str(path)
    with Image.open(path) as image:
        count=getattr(image,'n_frames',1)
        assert count==row['output_frames'], str(path)
        total=0
        for i in range(count):
            image.seek(i);image.load()
            assert image.size==(128,128), str(path)
            total+=image.info.get('duration',0)
        if row['animated']:
            assert count>1 and total==row['duration_ms'], str(path)
            assert image.info.get('loop')==row['loop'], str(path)
print(f'Verified {len(manifest)} images, all frames are 128x128.')
