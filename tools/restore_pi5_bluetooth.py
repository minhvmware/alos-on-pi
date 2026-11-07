#!/usr/bin/env python3
"""Remove the debug-era Bluetooth disable overlay from the known SSD."""
from ssd_identity import expected_ssd_serial
import subprocess, json, pathlib, os, datetime

def run(*a):
    return subprocess.run(a, check=True, capture_output=True).stdout
assert os.geteuid()==0
info=json.loads(run('lsblk','-J','-o','SERIAL,TRAN,MOUNTPOINTS','/dev/sda'))['blockdevices'][0]
assert info['serial']==expected_ssd_serial() and info['tran']=='usb'
def unused(n):
    return not any(n.get('mountpoints') or []) and all(unused(c) for c in n.get('children',[]))
assert unused(info)
old=run('mtype','-i','/dev/sda1','::config.txt')
assert old.splitlines().count(b'dtoverlay=disable-bt')==1
assert b'dtparam=uart0=on' in old and b'dtparam=uart0_console' in old
backup=pathlib.Path(__file__).resolve().parents[1]/'work'/('bluetooth-restore-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir()
(backup/'config.txt.before').write_bytes(old)
new=old.replace(b'# Free UART0 from Bluetooth for serial console',b'# Pi 5 Bluetooth uses a separate UART; keep it enabled')
new=new.replace(b'dtoverlay=disable-bt',b'# Removed debug-only disable-bt overlay')
(backup/'config.txt.after').write_bytes(new)
run('mcopy','-o','-i','/dev/sda1',str(backup/'config.txt.after'),'::config.txt')
assert run('mtype','-i','/dev/sda1','::config.txt')==new
assert b'dtoverlay=disable-bt' not in new
check=subprocess.run(['fsck.fat','-n','/dev/sda1'],capture_output=True)
(backup/'fat-check.log').write_bytes(check.stdout+check.stderr)
assert check.returncode==0, 'Config applied; FAT check needs review. See backup log.'
run('sync')
run('blockdev','--flushbufs','/dev/sda')
print('PASS: Bluetooth disable removed; UART console preserved. Backup:',backup)
