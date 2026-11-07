#!/usr/bin/env python3
"""Extract Pi vendor policy from a regular ext4 image for the trial builders."""
import argparse
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('vendor_image', type=Path)
    a = p.parse_args()
    if not a.vendor_image.is_file() or a.vendor_image.is_symlink():
        p.error('A regular Pi vendor ext4 image is required; block devices are refused')
    project = Path(__file__).resolve().parents[1]
    parent = project / 'work/mapper-review/vendor/etc'
    if (parent / 'selinux').exists():
        p.error('Policy workspace already exists; use a fresh checkout/work directory')
    parent.mkdir(parents=True, exist_ok=True)
    for path in [a.vendor_image.resolve(), parent.resolve()]:
        if any(c in str(path) for c in '\n\r"\\'):
            p.error('Unsupported debugfs path')
    r = subprocess.run(['debugfs', '-R', f'rdump /etc/selinux "{parent.resolve()}"',
                        str(a.vendor_image.resolve())], text=True, capture_output=True)
    for name in ['plat_pub_versioned.cil', 'vendor_sepolicy.cil', 'vendor_seapp_contexts']:
        if r.returncode or not (parent / 'selinux' / name).is_file():
            raise RuntimeError('Vendor policy extraction incomplete: ' + r.stderr)
    print('Vendor policy ready:', parent / 'selinux')
    print('Build the validators with tools/build_policy_tools.sh AOSP_WORKSPACE.')


if __name__ == '__main__':
    main()
