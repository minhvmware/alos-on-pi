#!/usr/bin/env python3
"""Compare image xattrs with libselinux file_contexts; emit an offline repair plan.

Mount IMAGE read-only with fuse2fs first. Unmount it before applying repair.dbg.
The mounted view supplies paths and modes only: host SELinux may replace xattrs
in the FUSE view, so existing labels are read directly through debugfs.
"""
import argparse
import ctypes
import ctypes.util
import json
import os
from pathlib import Path
import re
import subprocess


class Option(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int), ('value', ctypes.c_char_p)]


def quote(value):
    if any(c in value for c in '\n\r"\\'):
        raise ValueError(f'Unsupported debugfs path: {value!r}')
    return '"' + value + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('mount', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    image, mount, out = args.image.resolve(), args.mount.resolve(), args.output.resolve()
    out.mkdir(exist_ok=False)
    contexts = b'\n'.join((mount / part / 'etc/selinux' / filename).read_bytes()
                          for part, filename in [
                              ('system', 'plat_file_contexts'),
                              ('system_ext', 'system_ext_file_contexts'),
                              ('product', 'product_file_contexts')])
    context_path = out / 'combined_file_contexts'
    context_path.write_bytes(contexts + b'\n')
    lib = ctypes.CDLL(ctypes.util.find_library('selinux'), use_errno=True)
    lib.selabel_open.argtypes = [ctypes.c_uint, ctypes.POINTER(Option), ctypes.c_uint]
    lib.selabel_open.restype = ctypes.c_void_p
    lib.selabel_lookup_raw.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                                     ctypes.c_char_p, ctypes.c_int]
    lib.selabel_lookup_raw.restype = ctypes.c_int
    lib.freecon.argtypes = [ctypes.c_void_p]
    lib.selabel_close.argtypes = [ctypes.c_void_p]
    options = (Option * 1)(Option(3, os.fsencode(context_path)))  # SELABEL_OPT_PATH
    handle = lib.selabel_open(0, options, 1)  # SELABEL_CTX_FILE
    if not handle:
        raise OSError(ctypes.get_errno(), 'selabel_open failed')
    entries = [('/', os.lstat(mount).st_mode)]
    for root, dirs, files in os.walk(mount, followlinks=False):
        for name in dirs + files:
            path = Path(root) / name
            entries.append(('/' + str(path.relative_to(mount)), os.lstat(path).st_mode))
    expected, unmatched = {}, []
    try:
        for path, mode in entries:
            context = ctypes.c_void_p()
            if lib.selabel_lookup_raw(handle, ctypes.byref(context), os.fsencode(path), mode):
                unmatched.append(path)
                continue
            expected[path] = ctypes.string_at(context).decode()
            lib.freecon(context)
    finally:
        lib.selabel_close(handle)
    queries = out / 'query.dbg'
    queries.write_text(''.join(f'ea_get {quote(path)} security.selinux\n' for path in expected))
    result = subprocess.run(['debugfs', '-f', str(queries), str(image)],
                            check=True, capture_output=True, text=True)
    (out / 'xattrs.txt').write_text(result.stdout + result.stderr)
    actual, current = {}, None
    for line in result.stdout.splitlines():
        if line.startswith('debugfs: ea_get '):
            current = line[len('debugfs: ea_get '):].removesuffix(' security.selinux').strip('"')
            actual[current] = None
        elif current and 'security.selinux' in line:
            found = re.search(r'= "([^"]+)"', line)
            if found:
                actual[current] = found[1].removesuffix('\\000')
    if set(actual) != set(expected):
        raise RuntimeError('Incomplete debugfs xattr query')
    changes = [dict(path=path, actual=actual[path], expected=label)
               for path, label in expected.items() if actual[path] != label]
    (out / 'changes.json').write_text(json.dumps(changes, indent=2) + '\n')
    (out / 'unmatched.json').write_text(json.dumps(unmatched, indent=2) + '\n')
    (out / 'repair.dbg').write_text(''.join(
        f'ea_set {quote(row["path"])} security.selinux {quote(row["expected"])}\n'
        for row in changes))
    print(f'{len(entries)} paths, {len(changes)} label differences, {len(unmatched)} unmatched')
    print('Unmount the image before applying repair.dbg.')


if __name__ == '__main__':
    main()
