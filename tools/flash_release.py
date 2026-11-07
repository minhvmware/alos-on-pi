#!/usr/bin/env python3
"""Flash a release image to an explicitly selected, unmounted USB disk.

Default is read-only preview. --write erases the selected disk's contents.
No boot configuration changes or full-disk checksum pass are performed.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess


def run(*args):
    return subprocess.check_output([str(v) for v in args], text=True)


def inspect(disk, serial):
    if not serial.strip() or serial == 'YOUR_SSD_SERIAL':
        raise RuntimeError('Supply the exact verified USB serial')
    if not stat.S_ISBLK(disk.stat().st_mode):
        raise RuntimeError('Target is not a block device')
    info = json.loads(run('lsblk', '--tree', '-J', '-b', '-o',
                          'NAME,TYPE,SIZE,SERIAL,TRAN,RO,MOUNTPOINTS', disk))['blockdevices'][0]
    if info['type'] != 'disk' or info['tran'] != 'usb' or info['serial'] != serial or info['ro']:
        raise RuntimeError('Expected writable USB disk with the supplied serial')
    def unused(node):
        return not any(node.get('mountpoints') or []) and all(unused(c) for c in node.get('children', []))
    if not unused(info) or str(disk) in Path('/proc/swaps').read_text():
        raise RuntimeError('Target is mounted or in use as swap')
    return info


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path)
    p.add_argument('disk', type=Path)
    p.add_argument('--serial', required=True)
    p.add_argument('--write', action='store_true')
    a = p.parse_args()
    image, disk = a.image.resolve(), a.disk.resolve()
    if not image.is_file() or image.is_symlink():
        p.error('Use an extracted regular .img file')
    info = inspect(disk, a.serial)
    size = image.stat().st_size
    if size > info['size'] or size < 1024**3:
        p.error('Image is too large for target or unexpectedly small')
    table = json.loads(run('sfdisk', '--json', image))['partitiontable']
    if table['label'] != 'dos' or len(table['partitions']) != 6:
        p.error('Expected the documented Pi5 MBR image')
    for part in table['partitions']:
        if (part['start'] + part['size']) * 512 > size:
            p.error('Image is truncated')
    print(f'Image: {image.name}, {size} bytes\nTarget: {disk}, USB serial {a.serial}')
    if not a.write:
        print('Preview only. Add --write to erase this target and flash.')
        return
    if os.geteuid() != 0:
        p.error('Run this command as root for --write')
    inspect(disk, a.serial)
    subprocess.run(['dd', 'if=' + str(image), 'of=' + str(disk), 'bs=4M',
                    'status=progress', 'conv=fsync'], check=True)
    run('blockdev', '--flushbufs', disk)
    with image.open('rb') as source, disk.open('rb', buffering=0) as target:
        for offset in [0, size - 1024**2]:
            source.seek(offset)
            target.seek(offset)
            if source.read(1024**2) != target.read(1024**2):
                raise RuntimeError('Start/end readback mismatch')
    run('blockdev', '--rereadpt', disk)
    print('Flash/flush and start/end readback passed. Safely eject, then boot Pi5.')


if __name__ == '__main__':
    main()
