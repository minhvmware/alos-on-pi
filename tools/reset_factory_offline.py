#!/usr/bin/env python3
"""Authorized Pi factory reset after verified private backup; preserve boot/system/vendor layout."""
from ssd_identity import expected_ssd_serial
import argparse,json,os,pathlib,re,stat,subprocess
from backup_factory_reset import run

def quote(v):
 s=str(v)
 if any(c in s for c in '\n\r"\\'):raise ValueError('Unsupported path')
 return '"'+s+'"'

def header(text):return {a.strip():b.strip() for line in text.splitlines() if ':' in line for a,b in [line.split(':',1)]}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('disk',type=pathlib.Path);p.add_argument('backup',type=pathlib.Path);a=p.parse_args()
 disk=a.disk.resolve();b=a.backup.resolve();assert os.geteuid()==0 and stat.S_ISBLK(disk.stat().st_mode)
 assert (b/'BACKUP_COMPLETE').is_file() and not (b/'RESET_COMPLETE').exists()
 info=json.loads(run('lsblk','--tree','-J','-b','-o','NAME,SERIAL,TRAN,SIZE,MOUNTPOINTS',str(disk)).stdout)['blockdevices'][0]
 assert info['serial']==expected_ssd_serial() and info['tran']=='usb'
 def unused(n):return not any(n.get('mountpoints') or []) and all(unused(c) for c in n.get('children',[]))
 assert unused(info) and str(disk) not in pathlib.Path('/proc/swaps').read_text()
 assert run('sfdisk','--dump',str(disk)).stdout==(b/'table.sfdisk').read_text()
 prefix=str(disk)+('p' if disk.name[-1].isdigit() else '')
 assert int(run('blockdev','--getsize64',prefix+'3').stdout)==50870509568
 assert int(run('blockdev','--getsize64',prefix+'5').stdout)==8589934592
 assert int(run('blockdev','--getsize64',prefix+'7').stdout)==16777216
 project=pathlib.Path(__file__).resolve().parents[1]
 fsplans=[]
 for name,num in [('userdata','3'),('metadata','7')]:
  # Backup checks already passed; require their actual clean summaries.
  assert (b/(name+'-backup-fsck.log')).is_file() and (b/(name+'.img')).is_file()
  h=header((b/(name+'-superblock.txt')).read_text());assert h['Filesystem volume name']==name
  features=h['Filesystem features'].split();assert 'needs_recovery' not in features
  block=int(h['Block size']);blocks=int(h['Block count']);assert block==4096
  opts=['nodiscard','lazy_itable_init=0','lazy_journal_init=0']
  if 'casefold' in features:opts+=['encoding='+h['Character encoding']]
  reserved=100*int(h['Reserved block count'])/blocks
  args=['mke2fs','-F','-t','ext4','-b',str(block),'-I',h['Inode size'],'-N',h['Inode count'],'-m',str(reserved),'-L',name,'-U',h['Filesystem UUID'],'-O','none,'+','.join(features),'-E',','.join(opts)]
  if 'has_journal' in features:args+=['-J','size='+str(int(h['Total journal blocks'])*block//1048576)]
  trial=b/(name+'-fresh-trial.img');assert not trial.exists()
  with trial.open('xb') as f:f.truncate(block*blocks)
  print('Preparing fresh filesystem trial:',name,flush=True)
  r=run(*args,str(trial),str(blocks));(b/(name+'-trial-mkfs.log')).write_text(r.stdout+r.stderr)
  r=run('e2fsck','-fn',str(trial));(b/(name+'-trial-fsck.log')).write_text(r.stdout+r.stderr)
  fresh=header(run('dumpe2fs','-h',str(trial)).stdout)
  for k in ['Filesystem volume name','Filesystem UUID','Block count','Block size','Inode size']:
   assert fresh[k]==h[k],(name,k)
  assert set(fresh['Filesystem features'].split())==set(features)
  if 'casefold' in features:assert fresh['Character encoding']==h['Character encoding']
  fsplans.append((name,num,args,blocks))
 # Port fixes installed in system before wiping data.
 r=run('e2fsck','-p',prefix+'5',allowed=(0,1));(b/'system-fsck-before.log').write_text(r.stdout+r.stderr)
 def dbg(cmd,write=False):return run('debugfs',*(['-w'] if write else []),'-R',cmd,prefix+'5')
 plat=b/'plat-policy.before';dbg('dump /system/etc/selinux/plat_sepolicy.cil '+quote(plat))
 assert plat.read_bytes()==(project/'work/m12-p5-media-fmq-access.patch-files/plat_sepolicy.cil').read_bytes()
 prop=b/'system-build.prop.before';dbg('dump /system/build.prop '+quote(prop));old=prop.read_text()
 key='persist.user.hsum_boot_strategy';pattern=r'^'+re.escape(key)+r'=.*$'
 new=re.sub(pattern,key+'=0',old,flags=re.M) if re.search(pattern,old,re.M) else old.rstrip()+'\n\n# HoshinoOS headless desktop boot default\n'+key+'=0\n'
 patched=b/'system-build.prop.after';patched.write_text(new)
 apk=project.parent/'aluminium-analysis/91b269229318b3dae45e08966e69e2991e52c039/extracted/extracted/vendor/priv-app/vendor.google.desktop.serviceability/vendor.google.desktop.serviceability.apk'
 assert apk.is_file()
 target='/system_ext/app/PortServiceability/PortServiceability.apk'
 entry=dbg('stat '+quote(target));assert 'File not found' in entry.stderr,'Provider already preinstalled: inspect first'
 directory='/system_ext/app/PortServiceability';dbg('mkdir '+directory,True)
 for k,v in [('mode','040755'),('uid','0'),('gid','0')]:dbg('sif '+directory+' '+k+' '+v,True)
 dbg('ea_set '+directory+' security.selinux u:object_r:system_file:s0',True)
 for src,dst,replace in [(apk,target,False),(patched,'/system/build.prop',True)]:
  if replace:dbg('rm '+quote(dst),True)
  dbg('write '+quote(src)+' '+quote(dst),True)
  for k,v in [('mode','0100644'),('uid','0'),('gid','0')]:dbg('sif '+quote(dst)+' '+k+' '+v,True)
  dbg('ea_set '+quote(dst)+' security.selinux u:object_r:system_file:s0',True)
  check=b/(src.name+'.system-readback');dbg('dump '+quote(dst)+' '+quote(check));assert check.read_bytes()==src.read_bytes()
  meta=dbg('stat '+quote(dst)).stdout;assert 'Mode:  0644' in meta and 'User:     0   Group:     0' in meta
  assert 'u:object_r:system_file:s0' in dbg('ea_get '+quote(dst)+' security.selinux').stdout
 r=run('e2fsck','-fn',prefix+'5');(b/'system-fsck-after.log').write_text(r.stdout+r.stderr)
 (b/'SYSTEM_PREPARED').write_text('Original signed serviceability APK preinstalled as ordinary system app; default HSUM strategy0. M12 policy unchanged.\n')
 # Destructive part: explicitly requested factory reset, ONLY p3 and p7.
 for name,num,args,blocks in fsplans:
  assert unused(json.loads(run('lsblk','--tree','-J','-o','NAME,MOUNTPOINTS',str(disk)).stdout)['blockdevices'][0])
  print('Factory reset:',name,prefix+num,flush=True)
  r=run(*args,prefix+num,str(blocks));(b/(name+'-reset-mkfs.log')).write_text(r.stdout+r.stderr)
  r=run('e2fsck','-fn',prefix+num);(b/(name+'-reset-fsck.log')).write_text(r.stdout+r.stderr)
  check=header(run('dumpe2fs','-h',prefix+num).stdout);old=header((b/(name+'-superblock.txt')).read_text())
  assert check['Filesystem UUID']==old['Filesystem UUID'] and check['Filesystem volume name']==name
  assert set(check['Filesystem features'].split())==set(old['Filesystem features'].split())
 assert run('sfdisk','--dump',str(disk)).stdout==(b/'table.sfdisk').read_text()
 run('sync');run('blockdev','--flushbufs',str(disk))
 (b/'RESET_COMPLETE').write_text('Userdata p3 and metadata p7 reformatted with checked ext4 features. Partition table unchanged, p1/p6 untouched, system preparation checked.\n')
 print('FACTORY RESET COMPLETE. Physical first boot/setup validation required.',flush=True)
if __name__=='__main__':main()
