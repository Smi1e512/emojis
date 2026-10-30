#!/usr/bin/env python3
"""Batch resize source-manifest images to 128x128 PNG/GIF without cropping.

python tools/normalize.py sources.json --cache ../raw --output .
Requires Pillow >= 10. Source files are cached by SHA256 of their URL.
"""
import argparse
import concurrent.futures as cf
import hashlib
import io
import json
import struct
import subprocess
import urllib.request
from pathlib import Path
from PIL import Image, ImageOps

SIZE = (128, 128)

def fit(frame):
    image = ImageOps.exif_transpose(frame).convert('RGBA')
    image = ImageOps.contain(image, SIZE, Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', SIZE)
    canvas.paste(image, ((128-image.width)//2, (128-image.height)//2))
    return canvas

def gif_frame(frame):
    # Reserve index 255 for transparency. Matte partial-alpha edge pixels on
    # white because GIF cannot represent partial transparency; PNG keeps alpha.
    matte = Image.new('RGB', SIZE, 'white')
    matte.paste(frame, mask=frame.getchannel('A'))
    paletted = matte.quantize(colors=255, method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.FLOYDSTEINBERG)
    palette = paletted.getpalette()
    palette += [0] * (768-len(palette))
    palette[765:768] = [255,255,255]
    paletted.putpalette(palette)
    paletted.paste(255, mask=frame.getchannel('A').point(lambda a: 255 if a == 0 else 0))
    paletted.info['transparency'] = 255
    return paletted

def convert(data):
    with Image.open(io.BytesIO(data)) as src:
        original_size = list(src.size)
        n = getattr(src, 'n_frames', 1)
        loop = src.info.get('loop')
        # An APNG default image is a poster, not part of its animation.
        start = int(bool(src.info.get('default_image')))
        frames, durations = [], []
        digest = hashlib.sha256()
        for i in range(start, n):
            src.seek(i)
            frame = fit(src.copy())
            duration = float(src.info.get('duration', 100))
            frames.append(frame)
            durations.append(max(10, round(duration/10)*10))
            digest.update(frame.tobytes())
            digest.update(struct.pack('!d', durations[-1] if n-start > 1 else 0))
        digest.update(str(loop if n-start > 1 else None).encode())
        animated = len(frames) > 1
        output = io.BytesIO()
        if animated:
            quantized = [gif_frame(f) for f in frames]
            options = dict(save_all=True, append_images=quantized[1:],
                           duration=durations, disposal=2, transparency=255,
                           background=255, optimize=True)
            if loop is not None:
                options['loop'] = loop
            quantized[0].save(output, format='GIF', **options)
        else:
            frames[0].save(output, format='PNG', optimize=True, compress_level=9)
        result = output.getvalue()
        with Image.open(io.BytesIO(result)) as check:
            count = getattr(check, 'n_frames', 1)
            total = 0
            for i in range(count):
                check.seek(i)
                if check.size != SIZE: raise ValueError('Incorrect output dimensions')
                check.load()
                total += check.info.get('duration', 0)
            if animated and (count < 2 or total != sum(durations)):
                raise ValueError('Animation duration or frames lost')
            if animated and check.info.get('loop') != loop:
                raise ValueError('Animation loop changed')
        return result, dict(pixel_hash=digest.hexdigest(), original_size=original_size,
            source_frames=n-start, output_frames=count,
            duration_ms=total, animated=animated, loop=loop,
            source_sha256=hashlib.sha256(data).hexdigest(),
            sha256=hashlib.sha256(result).hexdigest())

def process(item, cache):
    try:
        path = cache / hashlib.sha256(item['url'].encode()).hexdigest()
        if not path.exists():
            # Bound total transfer time, including slow trickle responses.
            response = subprocess.run(['curl','--fail','--location','--silent',
                '--show-error','--max-time','20','--max-filesize','31457280',
                '--user-agent','Mozilla/5.0','--referer',item['page'],item['url']],
                capture_output=True, timeout=25)
            if response.returncode:
                raise ValueError(response.stderr.decode(errors='replace').strip())
            data = response.stdout
            if len(data) >= 30*1024*1024: raise ValueError('Source exceeds 30 MiB')
            path.write_bytes(data)
        result, metadata = convert(path.read_bytes())
        return item, result, metadata
    except Exception as error:
        return item, None, {'error':str(error)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--cache', type=Path, default=Path('.cache/originals'))
    parser.add_argument('--output', type=Path, default=Path('.'))
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    sources = json.loads(args.manifest.read_text())
    manifest, failures, seen = [], [], {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as executor:
        jobs = executor.map(lambda item: process(item, args.cache), sources)
        for index, (item, data, meta) in enumerate(jobs, 1):
            if data is None:
                failures.append({**item, **meta})
            else:
                key = (item['role'], meta['pixel_hash'])
                if key in seen:
                    seen[key]['sources'].append(item)
                else:
                    kind = '动图' if meta['animated'] else '静态图'
                    extension = '.gif' if meta['animated'] else '.png'
                    relative = Path(item['role']) / kind / (meta['pixel_hash'][:16]+extension)
                    target = args.output / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    entry = dict(path=relative.as_posix(), role=item['role'],
                        title=item['title'], size=[128,128], bytes=len(data),
                        sources=[item], **meta)
                    seen[key] = entry
                    manifest.append(entry)
            if index % 50 == 0:
                print(f'{index}/{len(sources)} checked; {len(manifest)} unique; {len(failures)} failed', flush=True)
    (args.output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    (args.output/'failures.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2)+'\n')
    print(f'Complete: {len(manifest)} unique, {len(failures)} failed', flush=True)

if __name__ == '__main__': main()
