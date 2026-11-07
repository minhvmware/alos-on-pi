# Offline ownership and SELinux repair

Use a private regular8GiB ext4 system image, with a complete backup. The
original integration merged Aluminium root/system, product and system_ext;
copying extracted host files flattened Android ownership and labels. These
repairs were essential to get init/logd/audio services running.

```bash
mkdir -p work/system-view
fuse2fs -o ro work/system-copy.img work/system-view
python3 tools/fix_fsconfig.py work/system-copy.img work/system-view \
  --src /absolute/path/aosp-rpi5 --plan work/owners.dbg
python3 tools/audit_image_labels.py work/system-copy.img work/system-view \
  work/label-audit
fusermount -u work/system-view

debugfs -w -f work/owners.dbg work/system-copy.img
debugfs -w -f work/label-audit/repair.dbg work/system-copy.img
e2fsck -fn work/system-copy.img
```

Generate a fresh label audit after the repair and require no unexpected
differences. The old regex-only relabeler is not the authoritative matcher;
use libselinux through audit_image_labels.py. Read full xattrs with `ea_get`,
as `ea_list` can truncate displayed values.

`fix_fsconfig.py` defaults to uid/gid repair while preserving existing modes.
It exposes optional mode changes, but does not implement capability-xattr
restoration. Do not describe it as a complete replacement for AOSP e2fsdroid.
Patch installers must retain root ownership, exact modes, Android labels and
Android policy-cache digests, then pass fsck. The policy digest is functional
Android metadata; it is independent of whole-disk checksum preferences.

The installed release already has these repairs. Running the historical M1
repair sequence on it without inspecting its current metadata is unnecessary.
