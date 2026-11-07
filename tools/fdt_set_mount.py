#!/usr/bin/env python3
"""Rewrite mnt_point / mnt_flags of one fstab entry inside a .dtbo overlay.

Usage: tools/fdt_set_mount.py <src.dtbo> <dst.dtbo> <partition> <mnt_point> [mnt_flags]
Example: tools/fdt_set_mount.py android-usb.dtbo out.dtbo system /system rw,barrier=1
"""
import struct
import sys

ALIGN = lambda n: (n + 3) & ~3
FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP, FDT_END = 1, 2, 3, 4, 9


def parse(data):
    magic, total, off_struct, off_strings, off_rsv, ver, last, cpuid, sz_str, sz_struct = \
        struct.unpack('>10I', data[:40])
    assert magic == 0xd00dfeed, 'not a dtb/dtbo'
    strings = data[off_strings:off_strings + sz_str]
    p, end = off_struct, off_struct + sz_struct
    root = None
    stack = []

    def cstr(buf, pos):
        e = buf.index(b'\0', pos)
        return buf[pos:e].decode(), e + 1

    while p < end:
        tok = struct.unpack('>I', data[p:p + 4])[0]
        p += 4
        if tok == FDT_BEGIN_NODE:
            name, e = cstr(data, p)
            p = ALIGN(e)
            node = {'name': name, 'props': [], 'children': []}
            if stack:
                stack[-1]['children'].append(node)
            else:
                root = node
            stack.append(node)
        elif tok == FDT_END_NODE:
            stack.pop()
        elif tok == FDT_PROP:
            ln, noff = struct.unpack('>II', data[p:p + 8])
            p += 8
            name, _ = cstr(strings, noff)
            val = data[p:p + ln]
            p = ALIGN(p + ln)
            stack[-1]['props'].append([name, val])
        elif tok == FDT_NOP:
            pass
        elif tok == FDT_END:
            break
        else:
            raise RuntimeError('bad token %d at %#x' % (tok, p - 4))
    return root, (ver, last, cpuid)


def serialize(root, hdr):
    strings = bytearray()
    stroff = {}

    def nameoff(n):
        if n not in stroff:
            stroff[n] = len(strings)
            strings.extend(n.encode() + b'\0')
        return stroff[n]

    def emit(node, out):
        out.extend(struct.pack('>I', FDT_BEGIN_NODE))
        out.extend(node['name'].encode() + b'\0')
        out.extend(b'\0' * (ALIGN(len(out)) - len(out)))
        for name, val in node['props']:
            out.extend(struct.pack('>III', FDT_PROP, len(val), nameoff(name)))
            out.extend(val)
            out.extend(b'\0' * (ALIGN(len(out)) - len(out)))
        for child in node['children']:
            emit(child, out)
        out.extend(struct.pack('>I', FDT_END_NODE))

    st = bytearray()
    emit(root, st)
    st.extend(struct.pack('>I', FDT_END))
    off_rsv = 40
    off_struct = off_rsv + 16
    off_strings = off_struct + len(st)
    total = off_strings + len(strings)
    h = struct.pack('>10I', 0xd00dfeed, total, off_struct, off_strings, off_rsv,
                    hdr[0], hdr[1], hdr[2], len(strings), len(st))
    return h + b'\0' * 16 + bytes(st) + bytes(strings)


def find(node, path):
    if not path:
        return node
    for c in node['children']:
        if c['name'] == path[0]:
            return find(c, path[1:])
    return None


def set_prop(node, name, value):
    for prop in node['props']:
        if prop[0] == name:
            prop[1] = value.encode() + b'\0'
            return 'updated'
    node['props'].append([name, value.encode() + b'\0'])
    return 'added'


def main():
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    src, dst, part, point = sys.argv[1:5]
    flags = sys.argv[5] if len(sys.argv) > 5 else None
    root, hdr = parse(open(src, 'rb').read())
    fstab = None
    for child in root['children']:
        cand = find(child, ['__overlay__', 'firmware', 'android', 'fstab', part])
        if cand:
            fstab = cand
            break
    if not fstab:
        raise SystemExit('fstab entry %r not found in %s' % (part, src))
    print('%s.mnt_point: %s' % (part, set_prop(fstab, 'mnt_point', point)))
    if flags:
        print('%s.mnt_flags: %s' % (part, set_prop(fstab, 'mnt_flags', flags)))
    open(dst, 'wb').write(serialize(root, hdr))
    print('wrote %s (%d bytes)' % (dst, len(open(dst, 'rb').read())))


main()
