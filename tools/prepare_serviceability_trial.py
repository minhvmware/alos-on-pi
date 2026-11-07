#!/usr/bin/env python3
"""Prepare an offline p5 trial with an isolated Java statistics-provider domain.

The signed provider APK must already be installed for desktop user 10. This
tool never modifies a block device and does not touch user data or hardware HALs.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def quote(path):
    s = str(path)
    if any(c in s for c in '\n\r"\\'):
        raise ValueError('Unsupported debugfs path')
    return '"' + s + '"'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if not source.is_file() or source.stat().st_size != 8 * 1024**3:
        p.error('Source must be a regular 8 GiB ext4 image')
    if output.exists():
        p.error('Output exists')
    project = Path(__file__).resolve().parents[1]
    stage = output.with_suffix('.patch-files')
    stage.mkdir(exist_ok=False)

    def dump(target, name):
        dest = stage / name
        run('debugfs', '-R', f'dump {quote(target)} {quote(dest)}', str(source))
        if not dest.is_file() or not dest.stat().st_size:
            raise RuntimeError('Could not extract ' + target)
        return dest

    paths = [
        '/system/etc/selinux/plat_sepolicy.cil',
        '/system/etc/selinux/mapping/202604.cil',
        '/system_ext/etc/selinux/system_ext_sepolicy.cil',
        '/system_ext/etc/selinux/mapping/202604.cil',
        '/product/etc/selinux/product_sepolicy.cil',
        '/product/etc/selinux/mapping/202604.cil',
    ]
    inputs = [dump(v, f'policy-{i}.cil') for i, v in enumerate(paths)]
    cil = stage / 'plat_sepolicy.cil'
    old = inputs[0].read_bytes()
    if b'(type rpi_serviceability)' in old:
        raise RuntimeError('Image already contains the trial')
    cil.write_bytes(old + b'\n' + (project / 'patches/sepolicy/rpi-serviceability.cil').read_bytes())
    inputs[0] = cil
    vendor = project / 'work/mapper-review/vendor/etc/selinux'
    inputs += [vendor / 'plat_pub_versioned.cil', vendor / 'vendor_sepolicy.cil']
    # This mixed user/system + userdebug/vendor baseline already needs -N at
    # boot. A successful compile is not a claim that neverallow validation passes.
    result = run(str(project / 'work/mapper-review/secilc'), '-m', '-M', 'true',
                 '-G', '-N', '-c', '30', '-o', str(stage / 'serviceability.policy'),
                 '-f', '/dev/null', *map(str, inputs))
    (stage / 'compile.log').write_text(result.stdout + result.stderr)

    target = '/system_ext/etc/selinux/system_ext_seapp_contexts'
    before = dump(target, 'system_ext_seapp_contexts.before')
    entry = ('user=system seinfo=platform name=vendor.google.desktop.serviceability '
             'domain=rpi_serviceability type=system_app_data_file')
    if 'name=vendor.google.desktop.serviceability' in before.read_text():
        raise RuntimeError('Package already has a context entry; inspect it first')
    seapp = stage / 'system_ext_seapp_contexts'
    seapp.write_text(before.read_text().rstrip() + '\n' + entry + '\n')
    # Validate both policy types and the combined platform/vendor neverallow
    # selectors, not only the added package line.
    checker = project / 'work/taskmanager-review/checkseapp'
    if not checker.is_file():
        raise RuntimeError('Build work/taskmanager-review/checkseapp as documented first')
    all_seapp = [dump('/system/etc/selinux/plat_seapp_contexts', 'plat_seapp_contexts'),
                 seapp, dump('/product/etc/selinux/product_seapp_contexts', 'product_seapp_contexts'),
                 vendor / 'vendor_seapp_contexts']
    combined = stage / 'combined-seapp'
    combined.write_text('\n'.join(f.read_text() for f in all_seapp))
    result = run(str(checker), '-p', str(stage / 'serviceability.policy'),
                 '-o', str(stage / 'combined-seapp.checked'), str(combined))
    if 'Not checking types' in result.stdout + result.stderr:
        raise RuntimeError('checkseapp must be built with LINK_SEPOL_STATIC')
    (stage / 'checkseapp.log').write_text(result.stdout + result.stderr)
    digest = stage / 'plat_sepolicy_and_mapping.sha256'
    # Required Android policy cache metadata, not disk/image SHA verification.
    digest.write_text(hashlib.sha256(cil.read_bytes() + inputs[1].read_bytes()).hexdigest() + '\n')
    replacements = {
        '/system/etc/selinux/plat_sepolicy.cil': (cil, 'sepolicy_file'),
        '/system/etc/selinux/plat_sepolicy_and_mapping.sha256': (digest, 'system_file'),
        target: (seapp, 'seapp_contexts_file'),
    }
    run('cp', '--reflink=auto', '--sparse=always', str(source), str(output))
    for dest, (local, label) in replacements.items():
        run('debugfs', '-w', '-R', f'rm {quote(dest)}', str(output))
        run('debugfs', '-w', '-R', f'write {quote(local)} {quote(dest)}', str(output))
        for field, value in [('mode', '0100644'), ('uid', '0'), ('gid', '0')]:
            run('debugfs', '-w', '-R', f'sif {quote(dest)} {field} {value}', str(output))
        context = f'u:object_r:{label}:s0'
        run('debugfs', '-w', '-R', f'ea_set {quote(dest)} security.selinux {context}', str(output))
        readback = stage / (local.name + '.readback')
        run('debugfs', '-R', f'dump {quote(dest)} {quote(readback)}', str(output))
        if local.read_bytes() != readback.read_bytes():
            raise RuntimeError('Content mismatch: ' + dest)
        stat = run('debugfs', '-R', f'stat {quote(dest)}', str(output)).stdout
        if 'Mode:  0644' not in stat or 'User:     0   Group:     0' not in stat:
            raise RuntimeError('Metadata mismatch: ' + dest)
        actual = run('debugfs', '-R', f'ea_get {quote(dest)} security.selinux', str(output)).stdout
        if context not in actual:
            raise RuntimeError('Context mismatch: ' + dest)
    result = run('e2fsck', '-fn', str(output))
    (stage / 'fsck.txt').write_text(result.stdout + result.stderr)
    print('Prepared:', output)
    print('Compiled with runtime-compatible -N; metadata and fsck passed.')
    print('Physical boot validation still required; no permissive domain added.')


if __name__ == '__main__':
    main()
