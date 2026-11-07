#!/usr/bin/env python3
"""Offline growth of final primary userdata partition3 on the Pi USB layout.

Preview by default. --write requires a new backup directory and an exact serial.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

from flash_release import inspect, run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('disk', type=Path)
    p.add_argument('--serial', required=True)
    p.add_argument('--write', action='store_true')
    p.add_argument('--backup', type=Path)
    a = p.parse_args()
    if os.geteuid() != 0:
        p.error('Run as root: even preview needs read access to the partition table')
    disk = a.disk.resolve()
    info = inspect(disk, a.serial)
    table = json.loads(run('sfdisk', '--json', disk))['partitiontable']
    if table['label'] != 'dos' or table['sectorsize'] != 512:
        p.error('Only the tested MBR/512 layout is supported')
    prefix = str(disk) + ('p' if disk.name[-1].isdigit() else '')
    parts = table['partitions']
    targets = [v for v in parts if v['node'] == prefix + '3']
    if len(targets) != 1 or targets[0]['type'] != '83':
        p.error('Expected primary ext4 partition3')
    target = targets[0]
    if any(v['start'] + v['size'] > target['start'] for v in parts if v is not target):
        p.error('Userdata is not physically last')
    sectors = info['size'] // 512
    if sectors >= 2**32:
        p.error('Disk exceeds this MBR tool capacity')
    newsize = (sectors - target['start']) // 8 * 8
    label = run('blkid', '-s', 'LABEL', '-o', 'value', target['node']).strip()
    if label != 'userdata' or newsize < target['size']:
        p.error('Unexpected label or shrink requested')
    print(f'userdata: {target["size"] * 512} -> {newsize * 512} bytes; start unchanged')
    if not a.write or newsize == target['size']:
        print('Preview only.' if not a.write else 'Already uses available space.')
        return
    if os.geteuid() != 0 or not a.backup or a.backup.exists():
        p.error('--write needs root and a new --backup directory')
    inspect(disk, a.serial)
    a.backup.mkdir(parents=True, mode=0o700)
    (a.backup / 'table.sfdisk').write_text(run('sfdisk', '--dump', disk))
    (a.backup / 'table.json').write_text(json.dumps(table, indent=2))
    with disk.open('rb') as f:
        (a.backup / 'mbr.bin').write_bytes(f.read(512))
    status = subprocess.run(['e2fsck', '-p', target['node']], capture_output=True, text=True)
    (a.backup / 'fsck-before.log').write_text(status.stdout + status.stderr)
    if status.returncode not in [0, 1]:
        raise RuntimeError('Source filesystem needs manual repair; partition table unchanged')
    subprocess.run(['sfdisk', '--no-reread', '-N', '3', str(disk)],
                   input=f'{target["start"]}, {newsize}, 83\n', text=True, check=True)
    actual = json.loads(run('sfdisk', '--json', disk))['partitiontable']
    target['size'] = newsize
    if actual != table:
        raise RuntimeError('Partition readback differs; stop before filesystem growth')
    run('blockdev', '--rereadpt', disk)
    run('resize2fs', prefix + '3')
    (a.backup / 'fsck-after.log').write_text(run('e2fsck', '-fn', prefix + '3'))
    run('sync')
    run('blockdev', '--flushbufs', disk)
    print('Data filesystem expanded; other partitions unchanged. Backup:', a.backup)


if __name__ == '__main__':
    main()
