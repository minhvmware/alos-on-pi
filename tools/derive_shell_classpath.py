#!/usr/bin/env python3
"""Generate Android shell classpaths from the running Pi's active APEX fragments.

Uses the optional key-pinned SSH endpoint. No classpath from another user's
device is bundled. Output is local; install it explicitly if needed.
"""
import argparse
import io
from pathlib import Path
import shlex
import subprocess
import tarfile
import xml.etree.ElementTree as ET


def varint(data, pos):
    result = shift = 0
    while pos < len(data) and shift < 70:
        byte = data[pos]
        pos += 1
        result |= (byte & 127) << shift
        if not byte & 128:
            return result, pos
        shift += 7
    raise ValueError('Invalid protobuf varint')


def fields(data):
    pos = 0
    while pos < len(data):
        key, pos = varint(data, pos)
        wire = key & 7
        if wire == 0:
            value, pos = varint(data, pos)
        elif wire == 2:
            size, pos = varint(data, pos)
            if pos + size > len(data):
                raise ValueError('Truncated protobuf field')
            value, pos = data[pos:pos + size], pos + size
        else:
            raise ValueError('Unsupported classpath protobuf wire type')
        yield key >> 3, value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('host')
    p.add_argument('output', type=Path)
    a = p.parse_args()
    if a.output.exists():
        p.error('Output already exists')
    helper = Path(__file__).resolve().parent / 'pi_ssh.sh'
    def ssh(command):
        return subprocess.check_output(['bash', str(helper), a.host, command])
    sdk = int(ssh('getprop ro.build.version.sdk').strip())
    root = ET.fromstring(ssh('cat /apex/apex-info-list.xml'))
    names = sorted({e.get('moduleName') for e in root if e.get('isActive') == 'true'})
    paths = ['/apex/com.android.art/etc/classpaths/bootclasspath.pb',
             '/system/etc/classpaths/bootclasspath.pb']
    paths += [f'/apex/{n}/etc/classpaths/bootclasspath.pb' for n in names if n != 'com.android.art']
    command = ('for fragment in ' + ' '.join(map(shlex.quote, paths)) +
               '; do if [ -r "$fragment" ]; then printf "%s\\n" "$fragment"; fi; done')
    found = ssh(command).decode().splitlines()
    if not found:
        raise RuntimeError('No readable classpath fragments')
    data = ssh('tar -cf - ' + ' '.join(map(shlex.quote, found)))
    cp = {1: [], 3: []}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for item in archive:
            if not item.isfile():
                continue
            for number, jar in fields(archive.extractfile(item).read()):
                if number != 1:
                    continue
                entry = dict(fields(jar))
                kind = entry.get(2, 0)
                if kind not in cp:
                    continue
                minimum, maximum = entry.get(3, b'').decode(), entry.get(4, b'').decode()
                if minimum and (not minimum.isdigit() or int(minimum) > sdk):
                    continue
                if maximum and (not maximum.isdigit() or int(maximum) < sdk):
                    continue
                path = entry[1].decode()
                if path not in cp[kind]:
                    cp[kind].append(path)
    if not cp[1] or not cp[3]:
        raise RuntimeError('Incomplete classpath')
    values = {'ANDROID_ROOT': '/system', 'ANDROID_DATA': '/data',
              'ANDROID_RUNTIME_ROOT': '/apex/com.android.runtime',
              'ANDROID_ART_ROOT': '/apex/com.android.art',
              'ANDROID_I18N_ROOT': '/apex/com.android.i18n',
              'ANDROID_TZDATA_ROOT': '/apex/com.android.tzdata',
              'BOOTCLASSPATH': ':'.join(cp[1]), 'DEX2OATBOOTCLASSPATH': ':'.join(cp[3])}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(''.join('export ' + k + '=' + shlex.quote(v) + '\n' for k, v in values.items()))
    print('Generated classpath counts:', {k: len(v) for k, v in cp.items()})


if __name__ == '__main__':
    main()
