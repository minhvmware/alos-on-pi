#!/usr/bin/env python3
"""Offline, guarded backup of Pi userdata+metadata before authorized factory reset. Does not format."""
from ssd_identity import expected_ssd_serial
import argparse,json,os,pathlib,shutil,stat,subprocess

def run(*args,allowed=(0,),**kw):
 r=subprocess.run(args,text=True,capture_output=True,**kw)
 if r.returncode not in allowed:raise RuntimeError(r.stdout+r.stderr)
 return r

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('disk',type=pathlib.Path);p.add_argument('backup',type=pathlib.Path);a=p.parse_args()
 disk=a.disk.resolve();assert os.geteuid()==0 and stat.S_ISBLK(disk.stat().st_mode)
 info=json.loads(run('lsblk','--tree','-J','-b','-o','NAME,SERIAL,TRAN,SIZE,MOUNTPOINTS',str(disk)).stdout)['blockdevices'][0]
 assert info['serial']==expected_ssd_serial() and info['tran']=='usb'
 def unused(n):return not any(n.get('mountpoints') or []) and all(unused(c) for c in n.get('children',[]))
 assert unused(info) and str(disk) not in pathlib.Path('/proc/swaps').read_text()
 prefix=str(disk)+('p' if disk.name[-1].isdigit() else '')
 data=prefix+'3';metadata=prefix+'7'
 assert int(run('blockdev','--getsize64',data).stdout)==50870509568
 assert int(run('blockdev','--getsize64',metadata).stdout)==16777216
 backup=a.backup.resolve();backup.mkdir(mode=0o700,exist_ok=False)
 # Have room even for an entirely allocated raw userdata image.
 assert shutil.disk_usage(backup).free>52*1024**3, 'Need at least52GiB free for conservative backup reservation'
 (backup/'partitions.json').write_text(json.dumps(info,indent=2))
 (backup/'table.sfdisk').write_text(run('sfdisk','--dump',str(disk)).stdout)
 for dev,name in [(data,'userdata'),(metadata,'metadata')]:
  r=run('e2fsck','-p',dev,allowed=(0,1));(backup/(name+'-fsck-before.log')).write_text(r.stdout+r.stderr)
  (backup/(name+'-superblock.txt')).write_text(run('dumpe2fs','-h',dev).stdout)
  (backup/(name+'-blkid.txt')).write_text(run('blkid',dev).stdout)
  print('Backing up',name,flush=True)
  with (backup/(name+'-e2image.log')).open('w') as log:
   subprocess.run(['e2image','-rap',dev,str(backup/(name+'.img'))],check=True,stdout=log,stderr=log)
  r=run('e2fsck','-fn',str(backup/(name+'.img')));(backup/(name+'-backup-fsck.log')).write_text(r.stdout+r.stderr)
 (backup/'BACKUP_COMPLETE').write_text('Userdata and metadata backups verified with e2fsck. No format performed.\n')
 run('sync');print('BACKUP COMPLETE; no userdata format yet. Backup:',backup,flush=True)
if __name__=='__main__':main()
