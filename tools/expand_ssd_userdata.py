#!/usr/bin/env python3
"""Offline Hynix SSD userdata expansion, preserving starts and other partitions."""
from ssd_identity import expected_ssd_serial
import json, subprocess, pathlib, os, datetime

def run(*args, **kw):
    return subprocess.run(args, text=True, capture_output=True, check=True, **kw).stdout

def table():
    return json.loads(run('sfdisk', '--json', '/dev/sda'))['partitiontable']

assert os.geteuid() == 0
info = json.loads(run('lsblk', '-J', '-o', 'NAME,SERIAL,TRAN,MOUNTPOINTS', '/dev/sda'))['blockdevices'][0]
assert info['serial'] == expected_ssd_serial() and info['tran'] == 'usb'
def unused(n):
    return not any(n.get('mountpoints') or []) and all(unused(c) for c in n.get('children', []))
assert unused(info)
assert '/dev/sda' not in pathlib.Path('/proc/swaps').read_text()
t = table()
assert t['label'] == 'dos' and t['sectorsize'] == 512
parts = t['partitions']
p = next(x for x in parts if x['node'] == '/dev/sda3')
assert p['start'] == 17874944 and p['size'] == 12125056 and p['type'] == '83'
assert all(x['start'] + x['size'] <= p['start'] for x in parts if x is not p)
assert 'LABEL="userdata"' in run('blkid', '/dev/sda3')
sectors = int(run('blockdev', '--getsz', '/dev/sda'))
assert 110000000 < sectors < 125000000
backup = pathlib.Path(__file__).resolve().parents[1] / 'work' / ('ssd-expand-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
(backup/'table.json').write_text(json.dumps(t, indent=2))
(backup/'table.sfdisk').write_text(run('sfdisk', '--dump', '/dev/sda'))
with open('/dev/sda', 'rb') as f:
    (backup/'mbr.bin').write_bytes(f.read(512))
r = subprocess.run(['e2fsck', '-p', '/dev/sda3'], capture_output=True, text=True)
(backup/'fsck-before.log').write_text(r.stdout+r.stderr)
assert r.returncode in (0,1), r.stdout+r.stderr
newsize = sectors - p['start']
print('Backup:', backup, 'new userdata bytes:', newsize*512, flush=True)
(backup/'resize-table.log').write_text(run('sfdisk', '--no-reread', '-N', '3', '/dev/sda', input=f"{p['start']}, {newsize}, 83\n"))
new = table()
expected = json.loads(json.dumps(t))
next(x for x in expected['partitions'] if x['node']=='/dev/sda3')['size'] = newsize
assert new == expected, 'Partition readback differs; STOP before filesystem resize'
run('blockdev', '--rereadpt', '/dev/sda')
assert int(run('blockdev', '--getsize64', '/dev/sda3')) == newsize*512
(backup/'resizefs.log').write_text(run('resize2fs', '/dev/sda3'))
(backup/'fsck-after.log').write_text(run('e2fsck', '-fn', '/dev/sda3'))
run('sync')
run('blockdev', '--flushbufs', '/dev/sda')
print('PASS: userdata expanded, other partitions unchanged. Backup:', backup)
