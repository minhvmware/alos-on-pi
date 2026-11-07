#!/usr/bin/env python3
"""Prepare optional SSH from a local Pi baseline and NEW per-installation keys.

Does not edit an OS image or disk. This development endpoint is opt-in.
"""
import argparse
from pathlib import Path
import shutil
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('baseline_system', type=Path, help='Pi baseline p5 ext4 image')
    a = p.parse_args()
    if not a.baseline_system.is_file() or a.baseline_system.is_symlink():
        p.error('Need a regular Pi baseline system image')
    for tool in ['debugfs', 'ssh-keygen']:
        if not shutil.which(tool):
            p.error('Missing ' + tool)
    state = Path(__file__).resolve().parents[1] / 'work/ssh-trial'
    state.mkdir(parents=True, mode=0o700, exist_ok=False)
    keys, payload = state / 'keys', state / 'payload'
    keys.mkdir(mode=0o700)
    (payload / 'config').mkdir(parents=True, mode=0o700)
    (payload / 'lib64').mkdir()
    for path in [state, a.baseline_system.resolve()]:
        if any(c in str(path) for c in '\n\r"\\'):
            p.error('Unsupported debugfs path')
    files = [('/system/bin/sshd', payload / 'port-sshd')]
    files += [('/system/lib64/' + name, payload / 'lib64' / name) for name in
              ['libbase.so', 'libc++.so', 'libcrypto.so', 'libcutils.so',
               'liblog.so', 'libssh.so', 'libssl.so', 'libz.so']]
    for source, dest in files:
        r = subprocess.run(['debugfs', '-R', f'dump {source} "{dest}"',
                            str(a.baseline_system.resolve())], capture_output=True, text=True)
        if r.returncode or not dest.is_file() or dest.stat().st_size == 0:
            raise RuntimeError('Baseline does not contain required SSH payload: ' + source)
    client = keys / 'client_ed25519'
    host = payload / 'config/ssh_host_ed25519_key'
    for key, comment in [(client, 'HoshinoOS debug client'), (host, 'HoshinoOS debug host')]:
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key),
                        '-C', comment], check=True)
        key.chmod(0o600)
    (payload / 'config/authorized_keys').write_bytes(client.with_suffix('.pub').read_bytes())
    public = host.with_suffix('.pub').read_text().split()
    (state / 'known_hosts').write_text('aluminium-pi5 ' + ' '.join(public[:2]) + '\n')
    print('Prepared SSH payload and fresh client/host keys in gitignored work/ssh-trial.')
    print('Install into a regular system image copy with tools/install_portssh.py.')


if __name__ == '__main__':
    main()
