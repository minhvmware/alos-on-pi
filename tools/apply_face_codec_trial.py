#!/usr/bin/env python3
"""Correct Pi face feature/FFmpeg mapping in an unmounted ext4 image.

Caller must check disk identity/mounts and recover the journal for block devices.
"""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('backup', type=Path)
    args = parser.parse_args()
    image = str(args.image.resolve())
    backup = args.backup.resolve()
    backup.mkdir(exist_ok=False)
    project = Path(__file__).resolve().parents[1]

    def quote(path):
        value = str(path)
        if any(c in value for c in '\n\r"\\'):
            raise ValueError('Unsupported debugfs path')
        return '"' + value + '"'

    def dbg(command, write=False):
        return subprocess.run(['debugfs', *(['-w'] if write else []), '-R', command, image],
                              check=True, capture_output=True, text=True).stdout

    feature = '/product/etc/permissions/android.hardware.biometrics.face.xml'
    contexts = '/system/etc/selinux/plat_service_contexts'
    old_feature = backup / 'android.hardware.biometrics.face.xml'
    old_contexts = backup / 'plat_service_contexts.before'
    dbg(f'dump {feature} {quote(old_feature)}')
    dbg(f'dump {contexts} {quote(old_contexts)}')
    if 'android.hardware.biometrics.face' not in old_feature.read_text():
        raise RuntimeError('Unexpected face feature file')
    text = old_contexts.read_text()
    endpoint = 'android.hardware.media.c2.IComponentStore/ffmpeg'
    if endpoint in text:
        raise RuntimeError('FFmpeg already has a mapping; inspect instead of overwriting')
    fixed = backup / 'plat_service_contexts.after'
    fixed.write_text(text.rstrip() + '\n' + endpoint + ' u:object_r:hal_codec2_service:s0\n')
    dbg(f'rm {contexts}', True)
    dbg(f'write {quote(fixed)} {contexts}', True)
    for field, value in [('mode', '0100644'), ('uid', '0'), ('gid', '0')]:
        dbg(f'sif {contexts} {field} {value}', True)
    dbg(f'ea_set {contexts} security.selinux u:object_r:service_contexts_file:s0', True)
    readback = backup / 'plat_service_contexts.readback'
    dbg(f'dump {contexts} {quote(readback)}')
    if fixed.read_bytes() != readback.read_bytes():
        raise RuntimeError('Service contexts content mismatch')
    metadata = dbg(f'stat {contexts}')
    if 'Mode:  0644' not in metadata or 'User:     0   Group:     0' not in metadata:
        raise RuntimeError('Service contexts metadata mismatch')
    if 'u:object_r:service_contexts_file:s0' not in dbg(f'ea_get {contexts} security.selinux'):
        raise RuntimeError('Service contexts label mismatch')
    dbg(f'rm {feature}', True)
    if 'Inode:' in dbg(f'stat {feature}'):
        raise RuntimeError('Face feature file still exists')
    subprocess.run(['bash', str(project / 'tools/update_portdiag.sh'), image,
                    str(backup / 'portdiag')], check=True)
    print('Face feature removed; FFmpeg service mapped; diagnostics corrected.')
    print('No new allow rules or permissive domains. Boot test still required.')


if __name__ == '__main__':
    main()
