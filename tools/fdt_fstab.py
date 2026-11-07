#!/usr/bin/env python3
"""Dump the Android DT fstab (firmware/android/fstab/*) of a .dtbo/.dtb.

Usage: tools/fdt_fstab.py <dtbo-or-dtb>
"""
import struct
import sys

ALIGN = lambda n: (n + 3) & ~3


def parse(path):
    d = open(path, 'rb').read()
    magic, tot, off_s, off_str, off_rsv, ver, last, cpuid, sz_str, sz_st = \
        struct.unpack('>10I', d[:40])
    if magic != 0xd00dfeed:
        raise SystemExit('%s: not a flattened device tree' % path)
    strs = d[off_str:off_str + sz_str]
    p = off_s
    end = off_s + sz_st
    out = []

    def cstr(b, pos):
        e = b.index(b'\0', pos)
        return b[pos:e].decode('utf-8', 'replace'), e + 1

    stack = []
    while p < end:
        tok = struct.unpack('>I', d[p:p + 4])[0]
        p += 4
        if tok == 1:
            name, e = cstr(d, p)
            p = ALIGN(e)
            stack.append(name if name else '/')
        elif tok == 2:
            stack.pop()
        elif tok == 3:
            ln, noff = struct.unpack('>II', d[p:p + 8])
            p += 8
            nm, _ = cstr(strs, noff)
            val = d[p:p + ln]
            p = ALIGN(p + ln)
            out.append(('/'.join(stack), nm, val))
        elif tok == 9:
            break
    return out


def main():
    path = sys.argv[1]
    for node, name, val in parse(path):
        if '/firmware/android/fstab' not in node:
            continue
        part = node.rsplit('/', 1)[-1]
        if 'fstab' in part:
            continue
        try:
            shown = val.rstrip(b'\0').decode()
        except UnicodeDecodeError:
            shown = val.hex()
        print('%-10s %-12s %r' % (part, name, shown))


main()
