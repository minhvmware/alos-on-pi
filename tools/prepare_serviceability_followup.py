#!/usr/bin/env python3
"""Prepare the M8 follow-up for the existing framework memory-stat service."""
import argparse
import hashlib
import json
from pathlib import Path

from prepare_serviceability_trial import quote, run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    source, output = a.source.resolve(), a.output.resolve()
    if not source.is_file() or source.stat().st_size != 8589934592 or output.exists():
        p.error('Need a regular 8 GiB source and a new output path')
    project = Path(__file__).resolve().parents[1]
    stage = output.with_suffix('.patch-files')
    stage.mkdir(exist_ok=False)

    def dump(target, name):
        f = stage / name
        run('debugfs', '-R', f'dump {quote(target)} {quote(f)}', str(source))
        if not f.is_file() or not f.stat().st_size:
            raise RuntimeError('Missing source ' + target)
        return f

    plat_path = '/system/etc/selinux/plat_sepolicy.cil'
    contexts_path = '/system/etc/selinux/plat_service_contexts'
    plat = dump(plat_path, 'plat.before')
    contexts = dump(contexts_path, 'service-contexts.before')
    if b'(type rpi_serviceability)' not in plat.read_bytes():
        raise RuntimeError('M8 provider domain is missing')
    if b'(type rpi_desktop_serviceability_service)' in plat.read_bytes():
        raise RuntimeError('Already patched')
    patched = stage / 'plat_sepolicy.cil'
    patched.write_bytes(plat.read_bytes() + b'\n' +
                        (project / 'patches/sepolicy/rpi-serviceability-memory.cil').read_bytes())
    name = 'com.android.server.desktop.serviceability.IDesktopServiceabilityService/default'
    if name in contexts.read_text():
        raise RuntimeError('Endpoint already mapped; inspect')
    mapped = stage / 'plat_service_contexts'
    mapped.write_text(contexts.read_text().rstrip() + '\n' + name +
                      ' u:object_r:rpi_desktop_serviceability_service:s0\n')
    policy_paths = ['/system/etc/selinux/mapping/202604.cil',
                    '/system_ext/etc/selinux/system_ext_sepolicy.cil',
                    '/system_ext/etc/selinux/mapping/202604.cil',
                    '/product/etc/selinux/product_sepolicy.cil',
                    '/product/etc/selinux/mapping/202604.cil']
    inputs = [patched] + [dump(v, f'policy-{i}.cil') for i, v in enumerate(policy_paths)]
    vendor = project / 'work/mapper-review/vendor/etc/selinux'
    inputs += [vendor / 'plat_pub_versioned.cil', vendor / 'vendor_sepolicy.cil']
    result = run(str(project / 'work/mapper-review/secilc'), '-m', '-M', 'true',
                 '-G', '-N', '-c', '30', '-o', str(stage / 'serviceability.policy'),
                 '-f', '/dev/null', *map(str, inputs))
    (stage / 'compile.log').write_text(result.stdout + result.stderr)
    digest = stage / 'plat_sepolicy_and_mapping.sha256'
    digest.write_text(hashlib.sha256(patched.read_bytes() + inputs[1].read_bytes()).hexdigest() + '\n')
    changes = [(plat_path, patched, 'sepolicy_file'),
               (contexts_path, mapped, 'service_contexts_file'),
               ('/system/etc/selinux/plat_sepolicy_and_mapping.sha256', digest, 'system_file')]
    manifest = {
        'guards': [[plat_path, plat.name], [contexts_path, contexts.name],
                   [policy_paths[0], inputs[1].name]],
        'changes': [[target, f.name, label] for target, f, label in changes],
    }
    (stage / 'apply-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    run('cp', '--reflink=auto', '--sparse=always', str(source), str(output))
    for target, f, label in changes:
        run('debugfs', '-w', '-R', f'rm {quote(target)}', str(output))
        run('debugfs', '-w', '-R', f'write {quote(f)} {quote(target)}', str(output))
        for field, value in [('mode', '0100644'), ('uid', '0'), ('gid', '0')]:
            run('debugfs', '-w', '-R', f'sif {quote(target)} {field} {value}', str(output))
        context = 'u:object_r:' + label + ':s0'
        run('debugfs', '-w', '-R', f'ea_set {quote(target)} security.selinux {context}', str(output))
        back = stage / (f.name + '.readback')
        run('debugfs', '-R', f'dump {quote(target)} {quote(back)}', str(output))
        if f.read_bytes() != back.read_bytes():
            raise RuntimeError('Readback failed: ' + target)
        meta = run('debugfs', '-R', f'stat {quote(target)}', str(output)).stdout
        if 'Mode:  0644' not in meta or 'User:     0   Group:     0' not in meta:
            raise RuntimeError('Metadata failed: ' + target)
        if context not in run('debugfs', '-R', f'ea_get {quote(target)} security.selinux', str(output)).stdout:
            raise RuntimeError('Label failed: ' + target)
    result = run('e2fsck', '-fn', str(output))
    (stage / 'fsck.txt').write_text(result.stdout + result.stderr)
    print('Prepared follow-up; compiled with runtime-compatible -N, readback and fsck passed.')


if __name__ == '__main__':
    main()
