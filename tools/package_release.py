#!/usr/bin/env python3
"""Compress a sanitized regular image into GitHub-sized release assets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('output', type=Path, help='New directory for release assets')
    p.add_argument('--part-mib', type=int, default=1900)
    a = p.parse_args()
    if not a.image.is_file() or a.image.is_symlink() or not shutil.which('zstd'):
        p.error('Need a regular image file and zstd')
    if not 1 <= a.part_mib < 2048 or a.output.exists():
        p.error('Need part size below2048MiB and a new output directory')
    manifest = a.image.with_suffix('.release.json')
    if not manifest.is_file():
        p.error('Missing capture_release manifest; arbitrary disk dumps must not be published')
    info = json.loads(manifest.read_text())
    if info.get('userdata') != 'fresh; source data never copied' or info.get('image_size') != a.image.stat().st_size:
        p.error('Manifest does not describe a sanitized capture of this image')
    a.output.mkdir(parents=True)
    process = subprocess.Popen(['zstd', '-T2', '-6', '--stdout', str(a.image)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    limit = a.part_mib * 1024**2
    assets = []
    current = None
    size = 0
    try:
        while data := process.stdout.read(1024**2):
            while data:
                if current is None:
                    path = a.output / (a.image.name + f'.zst.{len(assets) + 1:03d}')
                    current = path.open('xb')
                    digest = hashlib.sha256()
                    size = 0
                block, data = data[:limit - size], data[limit - size:]
                current.write(block)
                digest.update(block)
                size += len(block)
                if size == limit:
                    current.close()
                    assets.append({'name': path.name, 'bytes': size, 'sha256': digest.hexdigest()})
                    print('Compressed part complete:', path.name, flush=True)
                    current = None
        if current:
            current.close()
            current = None
            assets.append({'name': path.name, 'bytes': size, 'sha256': digest.hexdigest()})
        stderr = process.stderr.read().decode(errors='replace')
        if process.wait():
            raise RuntimeError('zstd failed: ' + stderr)
    finally:
        if current:
            current.close()
        if process.poll() is None:
            process.terminate()
            process.wait()
    if not assets:
        raise RuntimeError('No compressed data')
    if len(assets) == 1:
        old = a.output / assets[0]['name']
        new = a.output / (a.image.name + '.zst')
        old.rename(new)
        assets[0]['name'] = new.name
    shutil.copyfile(manifest, a.output / manifest.name)
    package = {'image': a.image.name, 'image_bytes': a.image.stat().st_size,
               'compression': 'zstd', 'parts': assets,
               'restore': 'Concatenate numbered parts in order, then decompress with zstd.'}
    (a.output / 'assets.json').write_text(json.dumps(package, indent=2) + '\n')
    (a.output / 'SHA256SUMS').write_text(''.join(f'{v["sha256"]}  {v["name"]}\n' for v in assets))
    print('Ready:', len(assets), 'image assets; each below GitHub 2GiB limit.', flush=True)


if __name__ == '__main__':
    main()
