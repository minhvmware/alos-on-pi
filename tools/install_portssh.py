#!/usr/bin/env python3
"""Install the prepared key-only SSH trial into an unmounted ext4 image.

Disk identity/mount/journal checks must be done by the caller for block devices.
Private keys and binaries are local under work/ssh-trial (gitignored).
"""
import argparse
import re
from pathlib import Path
import subprocess

from capture_release import check_ext4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    image = str(args.image.resolve())
    # Never apply offline changes on top of a pending journal replay.
    check_ext4(Path(image))
    project = Path(__file__).resolve().parents[1]
    payload = project / 'work/ssh-trial/payload'

    def dbg(command, write=False):
        return subprocess.run(['debugfs', *(['-w'] if write else []), '-R', command, image],
                              check=True, capture_output=True, text=True).stdout

    def quote(path):
        value = str(path)
        if any(c in value for c in '\n\r"\\'):
            raise ValueError('Unsupported debugfs path')
        return '"' + value + '"'

    entries = [
        (payload / 'port-sshd', '/system/bin/port-sshd', 0o755, 0, 2000, 'system_file'),
        (project / 'device/brcm/rpi5/portssh.rc', '/system/etc/init/portssh.rc', 0o644, 0, 0, 'system_file'),
        (project / 'device/brcm/rpi5/portssh-start.sh', '/system/etc/portssh/start.sh', 0o644, 0, 0, 'system_file'),
        (project / 'device/brcm/rpi5/portssh-session.sh', '/system/etc/portssh/session.sh', 0o644, 0, 0, 'system_file'),
        (project / 'device/brcm/rpi5/portssh_config', '/system/etc/portssh/sshd_config', 0o644, 0, 0, 'system_file'),
        (payload / 'config/authorized_keys', '/system/etc/portssh/authorized_keys', 0o644, 0, 0, 'system_file'),
        (payload / 'config/ssh_host_ed25519_key', '/system/etc/portssh/ssh_host_ed25519_key', 0o600, 2000, 2000, 'system_file'),
    ]
    entries.extend((file, '/system/lib64/portssh/' + file.name, 0o644, 0, 0, 'system_lib_file')
                   for file in sorted((payload / 'lib64').glob('*.so')))
    for source, *_ in entries:
        if not source.is_file() or not source.stat().st_size:
            raise RuntimeError(f'Missing payload: {source}')
    for path, label in [('/system/etc/portssh', 'system_file'),
                        ('/system/lib64/portssh', 'system_lib_file')]:
        dbg(f'mkdir {path}', True)
        dbg(f'sif {path} mode 040755', True)
        dbg(f'sif {path} uid 0', True)
        dbg(f'sif {path} gid 0', True)
        dbg(f'ea_set {path} security.selinux u:object_r:{label}:s0', True)
    for source, target, mode, uid, gid, label in entries:
        dbg(f'rm {target}', True)
        dbg(f'write {quote(source)} {target}', True)
        for field, value in [('mode', oct(0o100000 | mode)[2:]), ('uid', uid), ('gid', gid)]:
            # debugfs parses mode in octal only with a leading zero.
            if field == 'mode':
                value = '0' + value
            dbg(f'sif {target} {field} {value}', True)
        dbg(f'ea_set {target} security.selinux u:object_r:{label}:s0', True)
        metadata = dbg(f'stat {target}')
        owners = re.search(r'User:\s+(\d+)\s+Group:\s+(\d+)', metadata)
        if not owners or (int(owners.group(1)), int(owners.group(2))) != (uid, gid):
            raise RuntimeError(f'Bad owner: {target}')
        if f'Mode:  {mode:04o}' not in metadata:
            raise RuntimeError(f'Bad mode: {target}')
        if f'u:object_r:{label}:s0' not in dbg(f'ea_get {target} security.selinux'):
            raise RuntimeError(f'Bad label: {target}')
        # Verify bytes without dumping key material into logs.
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            readback = Path(temp) / 'file'
            dbg(f'dump {target} {quote(readback)}')
            if readback.read_bytes() != source.read_bytes():
                raise RuntimeError(f'Bad content: {target}')
        print(f'Installed {target} ({mode:04o}, {uid}:{gid}, {label})')
    subprocess.run(['e2fsck', '-fn', image], check=True)
    print('SSH payload installed. Actual Pi startup/login still needs testing.')


if __name__ == '__main__':
    main()
