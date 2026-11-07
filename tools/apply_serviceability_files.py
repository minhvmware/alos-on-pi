#!/usr/bin/env python3
"""Apply the reviewed M8 three-file patch to an unmounted Hynix USB SSD.

Run as root after the Pi is powered off and its SSD is connected to the host.
The source files must match the reviewed M7 base byte for byte. No image or
userdata rewrite is performed. Backups and verification are mandatory.
"""
from ssd_identity import expected_ssd_serial
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess


def run(*args, allowed=(0,)):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode not in allowed:
        raise RuntimeError(f'{args[0]} failed ({r.returncode}): {r.stdout}\n{r.stderr}')
    return r


def quote(value):
    s = str(value)
    if any(c in s for c in '\n\r"\\'):
        raise ValueError('Unsupported path')
    return '"' + s + '"'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('partition', type=Path)
    p.add_argument('backup', type=Path)
    p.add_argument('--stage', type=Path, help='Reviewed follow-up directory with apply-manifest.json')
    a = p.parse_args()
    device = a.partition.resolve()
    if os.geteuid() != 0 or not stat.S_ISBLK(device.stat().st_mode):
        p.error('Root and an actual block partition are required')
    parent_name = run('lsblk', '-ndo', 'PKNAME', str(device)).stdout.strip()
    if not parent_name or '/' in parent_name:
        p.error('Could not determine parent disk')
    parent = Path('/dev') / parent_name
    info = json.loads(run('lsblk', '--tree', '-J', '-b', '-o',
                         'PATH,TYPE,SERIAL,TRAN,SIZE,MOUNTPOINTS', str(parent)).stdout)['blockdevices'][0]
    if info['serial'] != expected_ssd_serial() or info['tran'] != 'usb':
        p.error('This is not the expected Hynix USB SSD')
    expected = str(parent) + ('p5' if parent.name[-1].isdigit() else '5')
    if str(device) != expected or int(run('blockdev', '--getsize64', str(device)).stdout) != 8589934592:
        p.error('Expected the 8 GiB system partition 5')

    def mounted(node):
        return any(node.get('mountpoints') or []) or any(mounted(c) for c in node.get('children', []))

    if str(parent) in Path('/proc/swaps').read_text():
        p.error('A partition on this SSD is active swap')
    if mounted(info):
        p.error('A partition on this SSD is mounted')
    backup = a.backup.resolve()
    backup.mkdir(exist_ok=False)
    project = Path(__file__).resolve().parents[1]
    stage = a.stage.resolve() if a.stage else project / 'work/m8-p5-serviceability-trial.patch-files'
    manifest = json.loads((stage / 'apply-manifest.json').read_text()) if a.stage else None
    # Recover the journal before reading old files or changing metadata.
    r = run('e2fsck', '-p', str(device), allowed=(0, 1))
    (backup / 'journal-check.log').write_text(r.stdout + r.stderr)

    def dbg(command, write=False):
        r = run('debugfs', *(['-w'] if write else []), '-R', command, str(device))
        return r.stdout

    guards = [('/system/etc/selinux/plat_sepolicy.cil', 'policy-0.cil'),
              ('/system/etc/selinux/mapping/202604.cil', 'policy-1.cil'),
              ('/system_ext/etc/selinux/system_ext_seapp_contexts', 'system_ext_seapp_contexts.before')]
    if manifest:
        guards = manifest['guards']
    for i, (target, expected_file) in enumerate(guards):
        actual = backup / f'guard-{i}'
        dbg(f'dump {quote(target)} {quote(actual)}')
        if actual.read_bytes() != (stage / expected_file).read_bytes():
            raise RuntimeError('Disk differs from reviewed source base: ' + target)
    changes = [('/system/etc/selinux/plat_sepolicy.cil', 'plat_sepolicy.cil', 'sepolicy_file'),
               ('/system/etc/selinux/plat_sepolicy_and_mapping.sha256', 'plat_sepolicy_and_mapping.sha256', 'system_file'),
               ('/system_ext/etc/selinux/system_ext_seapp_contexts', 'system_ext_seapp_contexts', 'seapp_contexts_file')]
    if manifest:
        changes = manifest['changes']
    # Back up all targets before the first mutation.
    for target, name, _ in changes:
        dbg(f'dump {quote(target)} {quote(backup / (name + ".before"))}')
        if not (backup / (name + '.before')).is_file():
            raise RuntimeError('Missing backup: ' + target)
    for target, name, label in changes:
        local = stage / name
        dbg(f'rm {quote(target)}', True)
        dbg(f'write {quote(local)} {quote(target)}', True)
        for field, value in [('mode', '0100644'), ('uid', '0'), ('gid', '0')]:
            dbg(f'sif {quote(target)} {field} {value}', True)
        ctx = 'u:object_r:' + label + ':s0'
        dbg(f'ea_set {quote(target)} security.selinux {ctx}', True)
        readback = backup / (name + '.readback')
        dbg(f'dump {quote(target)} {quote(readback)}')
        if readback.read_bytes() != local.read_bytes():
            raise RuntimeError('Content mismatch: ' + target)
        meta = dbg(f'stat {quote(target)}')
        if 'Mode:  0644' not in meta or 'User:     0   Group:     0' not in meta:
            raise RuntimeError('Metadata mismatch: ' + target)
        if ctx not in dbg(f'ea_get {quote(target)} security.selinux'):
            raise RuntimeError('SELinux label mismatch: ' + target)
    r = run('e2fsck', '-fn', str(device))
    (backup / 'final-fsck.log').write_text(r.stdout + r.stderr)
    run('sync')
    run('blockdev', '--flushbufs', str(device))
    print(f'{len(changes)} policy/config files applied; content, metadata and fsck passed.')
    print('Userdata preserved. Physical boot/subsystem validation remains required.')


if __name__ == '__main__':
    main()
