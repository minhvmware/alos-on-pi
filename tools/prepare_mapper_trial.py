#!/usr/bin/env python3
"""Patch a copy of the M1 ext4 system image for the Pi allocator trial."""
import argparse
import hashlib
from pathlib import Path
import subprocess


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True)


def quote(path):
    value = str(path)
    if any(c in value for c in '\n\r"\\'):
        raise ValueError('Unsupported character in debugfs path')
    return f'"{value}"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    project = Path(__file__).resolve().parents[1]
    if output.exists():
        parser.error('Output already exists')
    if source.stat().st_size != 8 * 1024**3:
        parser.error('Expected an 8 GiB ext4 system image')
    staging = output.with_suffix('.patch-files')
    staging.mkdir()
    cil = staging / 'plat_sepolicy.cil'
    mapping = staging / 'mapping.cil'
    for image_path, local in [('/system/etc/selinux/plat_sepolicy.cil', cil),
                              ('/system/etc/selinux/mapping/202604.cil', mapping)]:
        run('debugfs', '-R', f'dump {quote(image_path)} {quote(local)}', str(source))
        if not local.is_file() or not local.stat().st_size:
            raise RuntimeError(f'Could not extract {image_path}')
    extra = (project / 'patches/sepolicy/gpuservice-allocator-client.cil').read_bytes()
    if b'Equivalent to hal_client_domain(gpuservice' in cil.read_bytes():
        raise RuntimeError('Source already patched')
    cil.write_bytes(cil.read_bytes() + b'\n' + extra)
    digest = staging / 'plat_sepolicy_and_mapping.sha256'
    digest.write_text(hashlib.sha256(cil.read_bytes() + mapping.read_bytes()).hexdigest() + '\n')
    replacements = {
        '/system/etc/selinux/plat_sepolicy.cil': cil,
        '/system/etc/selinux/plat_sepolicy_and_mapping.sha256': digest,
        '/system/etc/init/zzz-logcap.rc': project / 'device/brcm/rpi5/portdiag.rc',
        '/system/etc/portdiag.sh': project / 'device/brcm/rpi5/portdiag.sh',
    }
    run('cp', '--reflink=auto', '--sparse=always', str(source), str(output))
    # No mounted image: all mutations happen through debugfs, then are checked.
    for target, local in replacements.items():
        run('debugfs', '-w', '-R', f'rm {quote(target)}', str(output))
        run('debugfs', '-w', '-R', f'write {quote(local)} {quote(target)}', str(output))
        for field, value in [('mode', '0100644'), ('uid', '0'), ('gid', '0')]:
            run('debugfs', '-w', '-R', f'sif {quote(target)} {field} {value}', str(output))
        expected_label = ('u:object_r:sepolicy_file:s0' if target.endswith('/plat_sepolicy.cil')
                          else 'u:object_r:system_file:s0')
        run('debugfs', '-w', '-R',
            f'ea_set {quote(target)} security.selinux {quote(expected_label)}', str(output))
        readback = staging / (local.name + '.readback')
        run('debugfs', '-R', f'dump {quote(target)} {quote(readback)}', str(output))
        if readback.read_bytes() != local.read_bytes():
            raise RuntimeError(f'Content mismatch: {target}')
        stat = run('debugfs', '-R', f'stat {quote(target)}', str(output)).stdout
        label = run('debugfs', '-R', f'ea_list {quote(target)}', str(output)).stdout
        if 'Mode:  0644' not in stat or 'User:     0   Group:     0' not in stat:
            raise RuntimeError(f'Incorrect metadata: {target}\n{stat}')
        if expected_label not in label:
            raise RuntimeError(f'Incorrect label: {target}')
    result = run('e2fsck', '-fn', str(output))
    (staging / 'fsck.txt').write_text(result.stdout + result.stderr)
    print(f'Prepared and verified: {output}')
    print('SELinux enforcing retained. No automatic shutdown. Boot test required.')


if __name__ == '__main__':
    main()
