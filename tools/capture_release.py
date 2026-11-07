#!/usr/bin/env python3
"""Read an unmounted Pi USB disk into a compact, sanitized release image.

The SOURCE DISK IS NEVER WRITTEN. Data/metadata are created afresh; a configured
SSH endpoint is removed from the image copy. Linux host tools are required.
"""
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import uuid


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run(*args):
    r = subprocess.run([str(x) for x in args], capture_output=True, text=True)
    require(r.returncode == 0, f'{args[0]} failed: {r.stdout}\n{r.stderr}')
    return r.stdout


def quote(value):
    value = str(value)
    require(not any(c in value for c in '\n\r"\\'), 'Unsupported debugfs path')
    return '"' + value + '"'


def dbg(image, command, write=False):
    r = subprocess.run(['debugfs', *(['-w'] if write else []), '-R', command, str(image)],
                       capture_output=True, text=True)
    require(r.returncode == 0, 'debugfs failed')
    bad = ['File not found', 'No space left', 'Filesystem is read-only',
           'Ext2 inode is not a directory', 'Command not found', 'Usage:']
    require(not any(s in r.stderr for s in bad), f'debugfs: {command}: {r.stderr}')
    return r.stdout


def exists(image, path):
    r = subprocess.run(['debugfs', '-R', 'stat ' + quote(path), str(image)],
                       capture_output=True, text=True)
    return 'Inode:' in r.stdout


def remove_tree(image, path):
    if not exists(image, path):
        return
    info = dbg(image, 'stat ' + quote(path))
    if 'Type: directory' not in info:
        dbg(image, 'rm ' + quote(path), True)
        return
    listing = dbg(image, 'ls -p ' + quote(path))
    for line in listing.splitlines():
        if not line.startswith('/'):
            continue
        fields = line.split('/')
        name = fields[5]
        if name in ('.', '..', ''):
            continue
        require('/' not in name and '\n' not in name, 'Unsupported image filename')
        remove_tree(image, path + '/' + name)
    dbg(image, 'rmdir ' + quote(path), True)


def sparse_copy(source, destination, offset):
    """Copy data extents into an already-created regular image, preserving holes."""
    size = source.stat().st_size
    with source.open('rb') as src, destination.open('r+b') as dst:
        pos = 0
        while pos < size:
            try:
                begin = os.lseek(src.fileno(), pos, os.SEEK_DATA)
                end = min(os.lseek(src.fileno(), begin, os.SEEK_HOLE), size)
            except OSError as e:
                if e.errno == errno.ENXIO:
                    break
                raise
            src.seek(begin)
            dst.seek(offset + begin)
            remain = end - begin
            while remain:
                data = src.read(min(4 * 1024**2, remain))
                require(bool(data), 'Unexpected end of partition image')
                dst.write(data)
                remain -= len(data)
            pos = end


def header(device):
    return dict((a.strip(), b.strip()) for line in run('dumpe2fs', '-h', device).splitlines()
                if ':' in line for a, b in [line.split(':', 1)])


def check_ext4(image):
    h = header(image)
    features = set(h['Filesystem features'].split())
    require(not features.intersection({'needs_recovery', 'orphan_present'}),
            'Filesystem still needs recovery/orphan processing')
    r = subprocess.run(['e2fsck', '-fn', str(image)], capture_output=True, text=True)
    result = r.stdout + r.stderr
    require(r.returncode == 0 and 'Warning:' not in result and 'Clear? no' not in result,
            'Unresolved filesystem warning: ' + result)


def normalize_ext4_copy(image):
    """Recover ONLY an image copy, then replace its journal with an empty one."""
    r = subprocess.run(['e2fsck', '-fp', str(image)], capture_output=True, text=True)
    require(r.returncode in (0, 1), 'Image-copy recovery needs manual review: ' + r.stdout + r.stderr)
    h = header(image)
    if 'has_journal' in h['Filesystem features'].split():
        journal = int(h['Total journal blocks']) * int(h['Block size']) // 1024**2
        run('tune2fs', '-O', '^has_journal', image)
        run('tune2fs', '-j', '-J', 'size=' + str(journal), image)
    r = subprocess.run(['e2fsck', '-fp', str(image)], capture_output=True, text=True)
    require(r.returncode in (0, 1), 'Image-copy check failed: ' + r.stdout + r.stderr)
    check_ext4(image)


def fresh_ext4(device, output, size, label):
    h = header(device)
    features = h['Filesystem features'].split()
    require('needs_recovery' not in features, 'Source needs journal recovery; stop')
    require(int(h['Block size']) == 4096 and size % 4096 == 0, 'Unsupported block size')
    with output.open('xb') as f:
        f.truncate(size)
    options = ['nodiscard', 'lazy_itable_init=0', 'lazy_journal_init=0']
    if 'casefold' in features:
        options.append('encoding=' + h['Character encoding'])
    args = ['mke2fs', '-F', '-t', 'ext4', '-b', '4096', '-I', h['Inode size'],
            '-i', '16384', '-m', '5', '-L', label, '-U', str(uuid.uuid4()),
            '-O', 'none,' + ','.join(features), '-E', ','.join(options)]
    if 'has_journal' in features:
        journal = int(h['Total journal blocks']) * 4096 // 1024**2
        args += ['-J', 'size=' + str(journal)]
    run(*args, output, str(size // 4096))
    check_ext4(output)
    actual = header(output)
    require(set(actual['Filesystem features'].split()) == set(features), 'Feature mismatch')
    entries = [line.split('/')[5] for line in dbg(output, 'ls -p /').splitlines()
               if line.startswith('/')]
    require(set(entries) == {'.', '..', 'lost+found'}, 'Fresh filesystem is not empty')


def scan_keys(image, stock_apks=None):
    # Actual PEM/OpenSSH key material, not the marker strings in crypto libraries.
    pattern = re.compile(rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=]{32,}')
    tail = b''
    position = 0
    offsets = set()
    with image.open('rb') as f:
        while data := f.read(8 * 1024**2):
            offsets.update(position - len(tail) + m.start() for m in pattern.finditer(tail + data))
            position += len(data)
            tail = data[-1024:]
    verified = set()
    for offset in sorted(offsets):
        # Some pristine proprietary APKs themselves include key-shaped test
        # resources. Preserve their signatures; allow only exact input APK bytes.
        mapping = dbg(image, 'icheck ' + str(offset // 4096)).strip().splitlines()
        require(len(mapping) == 2 and mapping[-1].split()[-1].isdigit(),
                'Unmapped private key material; publication refused')
        inode = mapping[-1].split()[-1]
        names = dbg(image, 'ncheck ' + inode).strip().splitlines()
        require(len(names) == 2, 'Ambiguous private key file; publication refused')
        path = names[-1].split(None, 1)[-1]
        require(stock_apks and path in stock_apks, 'Unrecognized private key file; publication refused')
        if path not in verified:
            with tempfile.TemporaryDirectory(dir=image.parent) as tmp:
                apk = Path(tmp) / 'stock.apk'
                dbg(image, 'dump ' + quote(path) + ' ' + quote(apk))
                require(hashlib.sha256(apk.read_bytes()).hexdigest() == stock_apks[path],
                        'Stock APK identity mismatch; publication refused')
            verified.add(path)
    return sorted(verified)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('disk', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--serial', required=True, help='Exact verified USB disk serial')
    p.add_argument('--size-bytes', type=int, default=15360000000)
    a = p.parse_args()
    disk, output = a.disk.resolve(), a.output.resolve()
    require(os.geteuid() == 0 and stat.S_ISBLK(disk.stat().st_mode), 'Root and a block disk required')
    require(a.serial.strip() and a.serial != 'YOUR_SSD_SERIAL', 'Explicit serial required')
    require(not output.exists(), 'Output already exists')
    require(not any(c in str(output) for c in '\n\r"\\ '), 'Use an output path without spaces/quotes')
    require(not output.with_suffix('.release.json').exists(), 'Manifest already exists')
    for tool in ['lsblk', 'sfdisk', 'blockdev', 'e2image', 'debugfs', 'dumpe2fs',
                 'e2fsck', 'mke2fs', 'tune2fs', 'mkfs.fat', 'fsck.fat', 'mcopy', 'mtype']:
        require(shutil.which(tool), 'Missing tool: ' + tool)
    info = json.loads(run('lsblk', '--tree', '-J', '-b', '-o',
                          'NAME,SERIAL,TRAN,MOUNTPOINTS', disk))['blockdevices'][0]
    require(info['serial'] == a.serial and info['tran'] == 'usb', 'USB disk identity mismatch')
    def unused(node):
        return not any(node.get('mountpoints') or []) and all(unused(c) for c in node.get('children', []))
    require(unused(info), 'Source or a child partition is mounted')
    require(str(disk) not in Path('/proc/swaps').read_text(), 'Source is active swap')
    table = json.loads(run('sfdisk', '--json', disk))['partitiontable']
    require(table['label'] == 'dos' and table['sectorsize'] == 512, 'Expected MBR/512-byte sectors')
    prefix = str(disk) + ('p' if disk.name[-1].isdigit() else '')
    parts = {int(x['node'][len(prefix):]): x for x in table['partitions']}
    require(set(parts) == {1, 2, 3, 5, 6, 7}, 'Unexpected partitions')
    require(parts[1]['size'] * 512 == 134217728 and parts[5]['size'] * 512 == 8589934592
            and parts[6]['size'] * 512 == 402653184 and parts[7]['size'] * 512 == 16777216,
            'This tool targets the tested Pi5 port partition layout')
    require(a.size_bytes % 4096 == 0, 'Image size must be 4096-byte aligned')
    data_sectors = a.size_bytes // 512 - parts[3]['start']
    require(data_sectors * 512 >= 2 * 1024**3, 'Insufficient space for fresh data')
    require(all(v['start'] + v['size'] <= parts[3]['start'] for n, v in parts.items() if n != 3),
            'Cannot compact this partition layout')
    output.parent.mkdir(parents=True, exist_ok=True)
    require(shutil.disk_usage(output.parent).free > 24 * 1024**3, 'Need 24GiB free working space')
    with tempfile.TemporaryDirectory(prefix='.release-private-', dir=output.parent) as tmp:
        stage = Path(tmp)
        print('Checking source filesystems (read-only)', flush=True)
        for n in [5, 6]:
            run('e2fsck', '-fn', prefix + str(n))
        print('Capturing boot files; rebuilding FAT with empty free space', flush=True)
        bootfiles = stage / 'bootfiles'
        bootfiles.mkdir()
        run('mcopy', '-s', '-i', prefix + '1', '::*', bootfiles)
        cmdline = bootfiles / 'cmdline.txt'
        original = cmdline.read_text()
        words = [w for w in original.split() if not re.match(
            r'(?:smsc95xx|smscgenet)\.macaddr=|(?:androidboot\.)?serialno=|macaddr=|androidboot\.selinux=|selinux=|enforcing=', w)]
        # The Aluminium user init already enforces policy despite old bring-up
        # cmdline flags. Make the release request explicit, on the copy only.
        words.append('androidboot.selinux=enforcing')
        cmdline.write_text(' '.join(words) + '\n')
        require('androidboot.selinux=permissive' not in words and 'selinux=0' not in words,
                'Release source uses permissive/disabled SELinux; stop')
        config = (bootfiles / 'config.txt').read_text()
        require(not re.search(r'^\s*dtoverlay=disable-bt\s*$', config, re.M), 'Bluetooth remains disabled')
        boot = stage / 'p1.img'
        with boot.open('xb') as f:
            f.truncate(parts[1]['size'] * 512)
        run('mkfs.fat', '-F', '32', '-n', 'boot', boot)
        for file in sorted(bootfiles.iterdir()):
            run('mcopy', '-s', '-i', boot, file, '::/')
        run('fsck.fat', '-n', boot)
        images = {1: boot}
        for n in [5, 6]:
            print(f'Capturing allocated ext4 blocks: p{n}', flush=True)
            image = stage / f'p{n}.img'
            run('e2image', '-ra', prefix + str(n), image)
            print(f'Recovering p{n} COPY and clearing old journal history', flush=True)
            normalize_ext4_copy(image)
            images[n] = image
        system = images[5]
        print('Removing workstation SSH endpoint from image copy', flush=True)
        removed = ['/system/etc/init/portssh.rc', '/system/bin/port-sshd',
                   '/system/etc/portssh', '/system/lib64/portssh']
        for path in removed:
            remove_tree(system, path)
            require(not exists(system, path), 'SSH path still present')
        check_ext4(system)
        clean = stage / 'p5-clean.img'
        # Re-copy only allocated blocks after unlink: freed SSH key blocks become holes.
        run('e2image', '-ra', system, clean)
        images[5] = clean
        require(exists(clean, '/system_ext/app/PortServiceability/PortServiceability.apk'),
                'Reset-safe Task Manager provider is absent')
        prop = stage / 'build.prop'
        dbg(clean, 'dump /system/build.prop ' + quote(prop))
        require('persist.user.hsum_boot_strategy=0' in prop.read_text(), 'Desktop boot default missing')
        cpu = stage / 'cpu.rc'
        dbg(images[6], 'dump /etc/init/hoshino-cpu-profile.rc ' + quote(cpu))
        require('schedutil' in cpu.read_text(), 'Expected CPU profile missing')
        for n, label in [(3, 'userdata'), (7, 'metadata')]:
            print('Creating fresh ' + label + '; source user data is never copied', flush=True)
            image = stage / f'p{n}.img'
            size = (data_sectors if n == 3 else parts[n]['size']) * 512
            fresh_ext4(prefix + str(n), image, size, label)
            images[n] = image
        print('Checking image copies for private key material', flush=True)
        stock_apks = json.loads((Path(__file__).resolve().parents[1] /
                                 'manifests/stock-apks.json').read_text())
        stock_matches = []
        for n in [5, 6]:
            check_ext4(images[n])
            stock_matches.extend(scan_keys(images[n], stock_apks))
        # Construct fresh MBR/EBRs, never copy any source gaps or deleted data.
        with output.open('xb') as f:
            f.truncate(a.size_bytes)
        output.chmod(0o600)
        lines = ['label: dos', 'label-id: 0x4853484f', 'unit: sectors', 'sector-size: 512', '']
        for n in [1, 2, 3, 5, 6, 7]:
            v = parts[n]
            size = data_sectors if n == 3 else v['size']
            line = f'{output}{n}: start={v["start"]}, size={size}, type={v["type"]}'
            if v.get('bootable'):
                line += ', bootable'
            lines.append(line)
        r = subprocess.run(['sfdisk', '--no-reread', '--no-tell-kernel', str(output)],
                           input='\n'.join(lines) + '\n', text=True, capture_output=True)
        require(r.returncode == 0, 'Output partition table failed: ' + r.stdout + r.stderr)
        for n, image in sorted(images.items()):
            print(f'Writing sanitized p{n} to release image', flush=True)
            sparse_copy(image, output, parts[n]['start'] * 512)
        final = json.loads(run('sfdisk', '--json', output))['partitiontable']
        for v in final['partitions']:
            v['node'] = Path(v['node']).name
        final.pop('device', None)
        manifest = {'format_version': 1, 'image': output.name, 'image_size': a.size_bytes,
                    'partition_table': final, 'source_disk_modified': False,
                    'userdata': 'fresh; source data never copied', 'metadata': 'fresh',
                    'ssh': 'configured endpoint, client authorization and host key removed',
                    'deleted_blocks': 'not copied; fresh MBR/gaps/FAT/data/metadata',
                    'journals': 'recovered on copies, then recreated empty before sanitization',
                    'stock_apk_key_resources': stock_matches,
                    'checks': ['source and image ext4 fsck', 'FAT fsck', 'private key material scan',
                               'Task Manager provider', 'HSUM boot default', 'CPU schedutil',
                               'Bluetooth enabled', 'no permissive/disabled SELinux cmdline'],
                    'validation': 'tested component baseline; assembled fresh image not yet boot-tested'}
        output.with_suffix('.release.json').write_text(json.dumps(manifest, indent=2) + '\n')
        with output.open('rb') as f:
            os.fsync(f.fileno())
        uid = int(os.environ.get('SUDO_UID', os.getuid()))
        gid = int(os.environ.get('SUDO_GID', os.getgid()))
        for path in [output, output.with_suffix('.release.json')]:
            os.chown(path, uid, gid)
            path.chmod(0o644)
    print('Release image prepared; source disk untouched. Physical release boot test pending.', flush=True)


if __name__ == '__main__':
    main()
