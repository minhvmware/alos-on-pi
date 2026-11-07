#!/usr/bin/env python3
"""Install one reversible vendor init CPU-governor trial on the known SSD."""
from ssd_identity import expected_ssd_serial
import argparse, datetime, json, os, pathlib, stat, subprocess

def run(*args,allowed=(0,)):
 r=subprocess.run(args,capture_output=True,text=True)
 if r.returncode not in allowed:raise RuntimeError(r.stdout+r.stderr)
 return r

def quote(p):
 p=str(p)
 if any(c in p for c in '\n\r"\\'):raise ValueError('Unsupported path')
 return '"'+p+'"'

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('partition',type=pathlib.Path);ap.add_argument('backup',type=pathlib.Path);a=ap.parse_args()
 part=a.partition.resolve();assert os.geteuid()==0 and stat.S_ISBLK(part.stat().st_mode)
 parent=run('lsblk','-ndo','PKNAME',str(part)).stdout.strip();disk=pathlib.Path('/dev')/parent
 expected=str(disk)+('p6' if disk.name[-1].isdigit() else '6')
 assert str(part)==expected and int(run('blockdev','--getsize64',str(part)).stdout)==402653184
 info=json.loads(run('lsblk','--tree','-J','-o','NAME,SERIAL,TRAN,MOUNTPOINTS',str(disk)).stdout)['blockdevices'][0]
 assert info['serial']==expected_ssd_serial() and info['tran']=='usb'
 def unused(n):return not any(n.get('mountpoints') or []) and all(unused(c) for c in n.get('children',[]))
 assert unused(info) and str(disk) not in pathlib.Path('/proc/swaps').read_text()
 backup=a.backup.resolve();backup.mkdir(exist_ok=False)
 r=run('e2fsck','-p',str(part),allowed=(0,1));(backup/'fsck-before.log').write_text(r.stdout+r.stderr)
 def dbg(cmd,write=False):return run('debugfs',*(['-w'] if write else []),'-R',cmd,str(part))
 target='/etc/init/hoshino-cpu-profile.rc'
 old=dbg('stat '+quote(target));assert 'File not found' in old.stderr, 'Target already exists; inspect before modifying'
 directory=dbg('stat /etc/init');assert 'Type: directory' in directory.stdout
 (backup/'init-dir-before.txt').write_text(directory.stdout+directory.stderr)
 dbg('dump /build.prop '+quote(backup/'vendor-build.prop'))
 assert (backup/'vendor-build.prop').is_file()
 project=pathlib.Path(__file__).resolve().parents[1];source=project/'patches/performance/hoshino-cpu-profile.rc'
 (backup/'target-was-absent.txt').write_text(target+'\nRollback: remove only this newly added file while offline.\n')
 dbg('write '+quote(source)+' '+quote(target),True)
 for k,v in [('mode','0100644'),('uid','0'),('gid','0')]:dbg('sif '+quote(target)+' '+k+' '+v,True)
 ctx='u:object_r:vendor_configs_file:s0';dbg('ea_set '+quote(target)+' security.selinux '+ctx,True)
 readback=backup/'hoshino-cpu-profile.rc.readback';dbg('dump '+quote(target)+' '+quote(readback))
 assert readback.read_bytes()==source.read_bytes()
 meta=dbg('stat '+quote(target)).stdout;assert 'Mode:  0644' in meta and 'User:     0   Group:     0' in meta
 assert ctx in dbg('ea_get '+quote(target)+' security.selinux').stdout
 r=run('e2fsck','-fn',str(part));(backup/'fsck-after.log').write_text(r.stdout+r.stderr)
 run('sync');run('blockdev','--flushbufs',str(disk))
 print('CPU schedutil trial installed. Xung limits unchanged. Boot and benchmark still required.')
if __name__=='__main__':main()
