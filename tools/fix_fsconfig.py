#!/usr/bin/env python3
"""Restore AOSP uid/gid/mode on an Android ext4 image, offline.

Why: the p5 image (the whole Android root, 8 GiB) was populated from a host
copy of the build tree, so every inode lost its ownership and became
root:root.  Modes survived (e.g. /system/bin/logd is still 0550), but init
starts services with setuid/setgid *before* execve, so a 0550 file that
should be root:logd is not executable by uid 1036:

    init: cannot execv('/system/bin/logd') ... Permission denied
    init: Service 'logd' (pid 786) exited with status 127

No `avc: denied` is logged for that, because SELinux is not the blocker:
the unix perms are.  With logd dead there is no logcat at all, which is why
the boot hang was hard to see.

This tool reproduces libcutils' fs_config() lookup - the same data the build
uses when it creates system.img/vendor.img - and writes the result with
debugfs, so no read-write mount and no host SELinux involvement is needed.

Lookup order (identical to system/core/libcutils/fs_config.cpp):
  1. <partition>/etc/fs_config_files (or _dirs) shipped inside the image,
     in conf[] order: system, vendor, oem, odm, product, system_ext
  2. compiled-in android_files[] / android_dirs[] tables
  3. fallback: 0:0, 0755 for directories, 0644 for files

Usage:
  fuse2fs -o ro work/m1-p5-labeled.img /tmp/p5mnt
  tools/fix_fsconfig.py work/m1-p5-labeled.img /tmp/p5mnt --report
  tools/fix_fsconfig.py work/m1-p5-labeled.img /tmp/p5mnt --apply

Options:
  --src DIR     AOSP tree (default /path/to/aosp-rpi5)
  --fields LIST which attributes to set: uid,gid,mode (default "uid,gid")
  --plan FILE   write the debugfs script to FILE (do not touch the image)
  --only PREFIX restrict to paths starting with PREFIX
  --top N       how many differing paths to print (default 20)

Two-step use, because the image must not be written while fuse2fs holds it:

  fuse2fs -o ro work/m1-p5-labeled.img /tmp/p5mnt
  tools/fix_fsconfig.py work/m1-p5-labeled.img /tmp/p5mnt --plan /tmp/fsfix.dbg
  fusermount -u /tmp/p5mnt
  debugfs -w -f /tmp/fsfix.dbg work/m1-p5-labeled.img
"""
import argparse
import fnmatch
import os
import re
import stat
import struct
import subprocess
import sys
import tempfile

DEFAULT_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'aosp-rpi5'))
CPP_REL = 'system/core/libcutils/fs_config.cpp'
HDR_REL = 'system/core/libcutils/include/private/android_filesystem_config.h'

# conf[] order in fs_config.cpp
CONF_PARTITIONS = ['system', 'vendor', 'oem', 'odm', 'product', 'system_ext']

# struct fs_path_config_from_file, packed: len, mode, uid, gid, capabilities
CONF_HDR = struct.Struct('<4H2I')
CONF_HDR_SIZE = 16

# fs_config.cpp: is_partition() / kLogicalPartitions
PARTITIONS = ('odm/', 'oem/', 'product/', 'system_ext/', 'vendor/')
LOGICAL = ('system/product/', 'system/system_ext/', 'system/vendor/', 'vendor/odm/')

TYPE_LETTER = [
    (stat.S_ISLNK, 'l'), (stat.S_ISDIR, 'd'), (stat.S_ISCHR, 'c'),
    (stat.S_ISBLK, 'b'), (stat.S_ISFIFO, 'p'), (stat.S_ISSOCK, 's'),
    (stat.S_ISREG, 'f'),
]

CAP_NUMBERS = {
    'CHOWN': 0, 'DAC_OVERRIDE': 1, 'DAC_READ_SEARCH': 2, 'FOWNER': 3, 'FSETID': 4,
    'KILL': 5, 'SETGID': 6, 'SETUID': 7, 'SETPCAP': 8, 'LINUX_IMMUTABLE': 9,
    'NET_BIND_SERVICE': 10, 'NET_BROADCAST': 11, 'NET_ADMIN': 12, 'NET_RAW': 13,
    'IPC_LOCK': 14, 'IPC_OWNER': 15, 'SYS_MODULE': 16, 'SYS_RAWIO': 17,
    'SYS_CHROOT': 18, 'SYS_PTRACE': 19, 'SYS_PACCT': 20, 'SYS_ADMIN': 21,
    'SYS_BOOT': 22, 'SYS_NICE': 23, 'SYS_RESOURCE': 24, 'SYS_TIME': 25,
    'SYS_TTY_CONFIG': 26, 'MKNOD': 27, 'LEASE': 28, 'AUDIT_WRITE': 29,
    'AUDIT_CONTROL': 30, 'SETFCAP': 31, 'MAC_OVERRIDE': 32, 'MAC_ADMIN': 33,
    'SYSLOG': 34, 'WAKE_ALARM': 35, 'BLOCK_SUSPEND': 36, 'AUDIT_READ': 37,
}


def load_aids(path):
    aids = {}
    with open(path, errors='replace') as f:
        for line in f:
            m = re.match(r'\s*#define\s+(AID_\w+)\s+(\d+)\b', line)
            if m:
                aids[m.group(1)] = int(m.group(2))
    return aids


def load_consts(text):
    """static const char NAME[] = "value"; -> {'NAME': 'value'}"""
    return dict(re.findall(r'static const char (\w+)\[\]\s*=\s*"([^"]*)"', text))

def load_table(text, name, aids, consts):
    """Parse one `static const struct fs_path_config NAME[] = { ... };` block."""
    m = re.search(r'static const struct fs_path_config %s\[\]\s*=\s*\{' % name, text)
    if not m:
        sys.exit('table %s not found in %s' % (name, CPP_REL))
    end = text.find('\n};', m.end())
    body = re.sub(r'//[^\n]*', '', text[m.end():end]).replace('\n', ' ')
    entries = []
    for raw in re.findall(r'\{([^{}]*)\}', body):
        fields = [f.strip() for f in raw.split(',')]
        if len(fields) < 5:
            continue
        mode_s, uid_s, gid_s = fields[0], fields[1], fields[2]
        caps_s = ','.join(fields[3:-1])
        pat_s = fields[-1].strip()
        try:
            mode = int(mode_s, 8)
            uid = aids[uid_s]
            gid = aids[gid_s]
        except (ValueError, KeyError) as e:
            print('skip entry %r (%s)' % (raw.strip(), e), file=sys.stderr)
            continue
        caps = 0
        for cap in re.findall(r'CAP_MASK_LONG\(CAP_(\w+)\)', caps_s):
            caps |= 1 << CAP_NUMBERS.get(cap, 0)
        if pat_s.startswith('"'):
            pat = pat_s.strip('"')
        else:
            cm = re.match(r'(\w+)\s*\+\s*1', pat_s)
            pat = consts[cm.group(1)].lstrip('/') if cm else None
        if not pat:
            print('skip weird pattern %r' % pat_s, file=sys.stderr)
            continue
        entries.append((mode, uid, gid, caps, pat))
    return entries


def load_conf_blob(blob):
    """Parse a compiled fs_config_{files,dirs} blob (first match wins)."""
    out = []
    off = 0
    while off + CONF_HDR_SIZE <= len(blob):
        ln, mode, uid, gid, cap_lo, cap_hi = CONF_HDR.unpack_from(blob, off)
        if ln < CONF_HDR_SIZE or off + ln > len(blob):
            break
        rest = blob[off + CONF_HDR_SIZE:off + ln]
        name = rest.split(b'\0', 1)[0].decode('utf-8', 'replace')
        if name:
            out.append((mode, uid, gid, (cap_hi << 32) | cap_lo, name))
        off += ln
    return out


def is_partition(path):
    return any(path.startswith(p) for p in PARTITIONS)


def fs_config_cmp(directory, pattern, path):
    """Port of fs_config_cmp() from libcutils/fs_config.cpp."""
    if directory:
        if not path.endswith('/'):
            path += '/'
        if not pattern.endswith('/*'):
            pattern = pattern + ('*' if pattern.endswith('/') else '/*')
    if fnmatch.fnmatchcase(path, pattern):
        return True
    for logical in LOGICAL:
        if path.startswith(logical):
            inner = path[path.find('/') + 1:]
            if is_partition(inner) and fnmatch.fnmatchcase(inner, pattern):
                return True
    return False


def lookup(path, is_dir, conf_dirs, conf_files, dirs_table, files_table):
    for mode, uid, gid, _caps, pattern in (conf_dirs if is_dir else conf_files):
        if fs_config_cmp(is_dir, pattern, path):
            return mode, uid, gid, pattern
    for mode, uid, gid, _caps, pattern in (dirs_table if is_dir else files_table):
        if fs_config_cmp(is_dir, pattern, path):
            return mode, uid, gid, pattern
    return (0o755 if is_dir else 0o644), 0, 0, '<default>'


def walk(mount):
    out = [('/', 'd')]
    for root, dirnames, filenames in os.walk(mount, topdown=True, followlinks=False):
        rel = os.path.relpath(root, mount)
        base = '' if rel == '.' else '/' + rel
        keep = []
        for name in dirnames + filenames:
            try:
                st = os.lstat(os.path.join(root, name))
            except OSError:
                continue
            ftype = 'f'
            for test, letter in TYPE_LETTER:
                if test(st.st_mode):
                    ftype = letter
                    break
            out.append((base + '/' + name, ftype))
            if ftype == 'd' and name != 'lost+found':
                keep.append(name)
        dirnames[:] = keep
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('mount')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--src', default=DEFAULT_SRC)
    ap.add_argument('--fields', default='uid,gid')
    ap.add_argument('--plan', default='')
    ap.add_argument('--only', default='')
    ap.add_argument('--top', type=int, default=20)
    args = ap.parse_args()
    fields = [f.strip() for f in args.fields.split(',') if f.strip()]
    bad = set(fields) - {'uid', 'gid', 'mode'}
    if bad:
        sys.exit('bad --fields: %s' % ','.join(sorted(bad)))

    aids = load_aids(os.path.join(args.src, HDR_REL))
    cpp = open(os.path.join(args.src, CPP_REL), errors='replace').read()
    consts = load_consts(cpp)
    dirs_table = load_table(cpp, 'android_dirs', aids, consts)
    files_table = load_table(cpp, 'android_files', aids, consts)
    print('tables: %d dirs, %d files, %d AIDs'
          % (len(dirs_table), len(files_table), len(aids)))

    conf_dirs, conf_files, found = [], [], []
    for part in CONF_PARTITIONS:
        for kind, sink in (('dirs', conf_dirs), ('files', conf_files)):
            rel = '%s/etc/fs_config_%s' % (part, kind)
            try:
                blob = open(os.path.join(args.mount, rel), 'rb').read()
            except OSError:
                continue
            entries = load_conf_blob(blob)
            if entries:
                sink.extend(entries)
                found.append('%s(%d)' % (rel, len(entries)))
    print('image config: %s' % (', '.join(found) if found else 'none'))

    entries = walk(args.mount)
    if args.only:
        entries = [e for e in entries if e[0].startswith(args.only)]
    print('paths: %d' % len(entries))

    changes = []
    stats = {'uid': 0, 'gid': 0, 'mode': 0}
    for path, ftype in entries:
        if ftype == 'l' or path == '/lost+found':
            continue
        is_dir = ftype == 'd'
        mode, uid, gid, pattern = lookup(
            path.lstrip('/'), is_dir, conf_dirs, conf_files,
            dirs_table, files_table)
        try:
            st = os.lstat(args.mount + path)
        except OSError:
            continue
        diff = {}
        if 'uid' in fields and st.st_uid != uid:
            diff['uid'] = uid
            stats['uid'] += 1
        if 'gid' in fields and st.st_gid != gid:
            diff['gid'] = gid
            stats['gid'] += 1
        if 'mode' in fields and stat.S_IMODE(st.st_mode) != mode:
            diff['mode'] = mode
            stats['mode'] += 1
        if diff:
            changes.append((path, st.st_mode, diff, pattern))

    print('differing paths: %d  (uid %d, gid %d, mode %d)'
          % (len(changes), stats['uid'], stats['gid'], stats['mode']))
    for path, _mode, diff, pattern in changes[:args.top]:
        desc = ' '.join(('mode=0%o' % v) if k == 'mode' else ('%s=%d' % (k, v))
                        for k, v in sorted(diff.items()))
        print('  %-58s %-24s <- %s' % (path, desc, pattern))
    if len(changes) > args.top:
        print('  ... %d more' % (len(changes) - args.top))

    if not changes:
        return

    lines = []
    for path, cur_mode, diff, _pattern in changes:
        q = '"%s"' % path
        if 'mode' in diff:
            lines.append('sif %s mode 0%o'
                         % (q, stat.S_IFMT(cur_mode) | diff['mode']))
        if 'uid' in diff:
            lines.append('sif %s uid %d' % (q, diff['uid']))
        if 'gid' in diff:
            lines.append('sif %s gid %d' % (q, diff['gid']))

    if args.plan:
        with open(args.plan, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        print('wrote %d debugfs commands to %s' % (len(lines), args.plan))
    if not args.apply:
        return

    with tempfile.NamedTemporaryFile('w', suffix='.dbg', delete=False) as f:
        f.write('\n'.join(lines) + '\n')
        script = f.name
    print('applying %d debugfs commands to %s ...' % (len(lines), args.image))
    res = subprocess.run(['debugfs', '-w', '-f', script, args.image],
                         capture_output=True, text=True)
    os.unlink(script)
    out = res.stdout + res.stderr
    bad = [ln for ln in out.splitlines()
           if 'not found' in ln or 'Invalid' in ln or 'No space' in ln]
    print('debugfs exit=%d, suspicious lines=%d' % (res.returncode, len(bad)))
    for ln in bad[:10]:
        print('  ' + ln)


main()
