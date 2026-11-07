#!/usr/bin/env python3
"""Offline Chrome-only Vulkan disable trial; preserve GLES and all profile data."""
from ssd_identity import expected_ssd_serial
import json, os, pathlib, subprocess, datetime

def run(*a): return subprocess.run(a,check=True,capture_output=True,text=True).stdout
assert os.geteuid()==0
info=json.loads(run('lsblk','--tree','-J','-o','NAME,SERIAL,TRAN,MOUNTPOINTS','/dev/sda'))['blockdevices'][0]
assert info['serial']==expected_ssd_serial() and info['tran']=='usb'
def unused(n): return not any(n.get('mountpoints') or []) and all(unused(c) for c in n.get('children',[]))
assert unused(info) and '/dev/sda' not in pathlib.Path('/proc/swaps').read_text()
r=subprocess.run(['e2fsck','-p','/dev/sda3'],capture_output=True,text=True)
assert r.returncode in (0,1),r.stdout+r.stderr
backup=pathlib.Path(__file__).resolve().parents[1]/'work'/('chrome-vulkan-pref-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(mode=0o700)
(backup/'fsck-before.log').write_text(r.stdout+r.stderr)
mount=pathlib.Path('/run/hoshino-ssd-maint'); mount.mkdir(exist_ok=True)
run('mount','-t','ext4','-o','nosuid,nodev,noexec','/dev/sda3',str(mount))
try:
 p=mount/'user/10/com.android.chrome/app_chrome/Local State'
 assert p.is_file() and not p.is_symlink()
 old=p.read_bytes(); state=json.loads(old)
 flags=state.get('browser',{}).get('enabled_labs_experiments',[])
 assert 'use-angle@1' in flags, 'Unexpected ANGLE preference; stop for review'
 assert not any(s.startswith('enable-vulkan@') for s in flags), 'Existing Vulkan override; stop for review'
 (backup/'Local State.before').write_bytes(old)
 before=p.stat(); ctx=os.getxattr(p,'security.selinux')
 state['browser']['enabled_labs_experiments']=flags+['enable-vulkan@2']
 new=json.dumps(state,separators=(',',':'),ensure_ascii=False).encode()
 (backup/'Local State.after').write_bytes(new)
 try:
  with p.open('wb') as f: f.write(new); f.flush(); os.fsync(f.fileno())
  assert p.read_bytes()==new
  after=p.stat()
  assert (before.st_ino,before.st_uid,before.st_gid,before.st_mode)==(after.st_ino,after.st_uid,after.st_gid,after.st_mode)
  assert os.getxattr(p,'security.selinux')==ctx
  check=json.loads(p.read_bytes()); check['browser']['enabled_labs_experiments']=flags
  assert check==json.loads(old)
 except BaseException:
  with p.open('wb') as f: f.write(old); f.flush(); os.fsync(f.fileno())
  raise
finally: run('umount',str(mount))
(backup/'fsck-after.log').write_text(run('e2fsck','-fn','/dev/sda3'))
run('sync'); run('blockdev','--flushbufs','/dev/sda')
print('Chrome-only Vulkan disable preference applied; GLES retained, profile/metadata verified. Backup:',backup)
