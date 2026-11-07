> Historical research/bring-up note. See [current status](STATUS.md). Local evidence and extracted inputs are not included.

# Authorized factory reset — 2026-11-07

## Completed offline; final verification 18:25 UTC+7

Reset succeeded on Hynix V2 USB SSD serial YOUR_SSD_SERIAL (/dev/sda).
Only p3 userdata and p7 metadata were reformatted. Userdata retains 47.4 GiB.
Exact filesystem features (including casefold/quota/verity), block/inode sizes,
labels, UUIDs and partition table were preserved. Laptop NVMe was not targeted.

Private root-owned 0700 backup directory:
`aluminium-rpi5/work/factory-reset-20261107/backup/`.
Contains sparse allocated-data userdata.img, metadata.img, original unrepaired
images, partition/filesystem headers, repair and verification logs.
BACKUP_COMPLETE, SYSTEM_PREPARED and RESET_COMPLETE are present.

The old userdata had orphan-list inconsistencies caught during backup checks.
Original images were retained; forced repair was performed on backup images
only. Repaired backups passed full read-only fsck. Four linked package,
settings and Chrome state files matched the source byte-for-byte. This checks
filesystem consistency and selected files, not all file contents.

Before reset, the original signed serviceability provider was preinstalled at
`/system_ext/app/PortServiceability/PortServiceability.apk` as an ordinary
system app. Original signature, root0644/system_file and byte readback checked.
Default `persist.user.hsum_boot_strategy=0` was saved in /system/build.prop.
M12 policy checked unchanged during preparation. Boot p1 and vendor p6 were
untouched. Final vendor CPU schedutil rc matches the project copy.

Fresh trial filesystems passed before format. Actual userdata, metadata and
prepared system passed e2fsck -fn. Fresh data/metadata root directories contain
only dot entries and lost+found. Partition table matches backup; sync and
whole-device buffer flush completed. Evidence: work/factory-reset-20261107/
reset-run.log and backup/*-reset-fsck.log, system-fsck-after.log. No disk SHA.
After final verification, repeated unmounted/serial guard and flush, then
udisksctl power-off succeeded. SSD is safe to unplug; root maintenance shell closed.

### Next physical boot

1. Reconnect SSD to Pi, then power on. First boot/provisioning NOT validated.
   Preserve original Google/Aluminium Setup Wizard; do not mark setup complete
   through shell as a shortcut.
2. Reconnect Wi-Fi or Ethernet. SSH files/keys/config survive in system;
   data-held Wi-Fi credentials were erased.
3. Check boot completion, actual user IDs, launcher stability, Bluetooth,
   Task Manager provider and CPU governor schedutil. Capture fatal/ANR logs
   before changes. Reset is not proof that crashes are cured.
4. After setup reapply density160, pointer speed+5 and prior animation/name
   preferences. Data overrides and installed app updates were erased,
   including Chrome157 and Diagnostics APK; system Chrome150 returns.
5. Re-bootstrap documented Chrome GLES compatibility for the installed
   version, then test Gmail and YouTube/TikTok. Runtime command-line file and
   profile flags were erased. Keep backup; do not rerun reset or restore old
   userdata merely to recover preferences.

The notes below describe pre-reset preparation, not pending reset work.

User explicitly requested trying a factory reset. Scope is Pi userdata(p3)
and Android metadata(p7); retain firmware/boot,p5system,p6vendor and expanded
partition layout. Never target host NVMe. User informed this deletes apps,
accounts and user data. No extra confirmation is required for this scope.

Before format: exact Hynix USB serial, sizes and unmounted checks; save sparse
raw e2image backups of userdata and metadata, verify each with e2fsck; retain
partition table and filesystem features. Host has77GiB free, enough for the
conservative52GiB reservation. Backup private directory0700. No diskSHA.
Tools/backup_factory_reset.py implements backup phase only, no format.

Preparation findings:
- SSH code/config/authorized key/host key are in system, not data; they survive.
  Wi-Fi credentials/settings will be erased; user reconnects after reset.
- vendor.google.desktop.serviceability is currently a data APK. Preserve the
  original signed provider as an ordinary preinstalled system_ext/app package,
  using its original bytes/signature and current M12 package-specific seapp
  mapping. Do not introduce sharedUserId or resign it. It already uses the
  platform system UID/signature. Inspect manifest before preinstallation.
- Preserve sys_boot headless strategy0 via system default property if absent;
  its current persist setting resides in data and would be lost.
- Chrome profile/non-rooted command-line flag/data flags are lost; source
  compatibility configuration is saved. Re-bootstrap after fresh setup.
  System Chrome150 comes back; updated157 is in data and will be erased.
- User requested original Google/Aluminium setup earlier; clean provisioning
  should restore original component states. Do not silently mark setup complete.
- Encryption property currently unsupported, so userdata backup is directly
  readable offline; metadata backup is still taken for complete rollback.
- CPU schedutil init file is vendor and will survive. M12 audio policy is
  system and will survive. Desktop density/mouse overrides will need reapply
  after setup according to existing user preferences160/+5.

Reset phase will be prepared from actual filesystem feature/superblock dump,
not generic mkfs defaults. Do not proceed without BACKUP_COMPLETE plus passing
backup filesystem checks. Preserve filesystem label and partition starts.
After reset verify filesystem, labels, clean boot, setup/user10, SSH, Bluetooth,
TaskManager, Gmail compatibility and video. Keep backup for rollback.
