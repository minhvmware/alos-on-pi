#!/usr/bin/env bash
# Update only the two capture files in an unmounted ext4 image/partition.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
image=$(realpath "${1:?usage: update_portdiag.sh IMAGE BACKUP_DIR}")
backup=${2:?usage: update_portdiag.sh IMAGE BACKUP_DIR}
mkdir -p "$backup"
backup=$(realpath "$backup")
[[ $image != *'"'* && $backup != *'"'* && $project != *'"'* ]]
[[ ! -e $backup/portdiag.rc.before && ! -e $backup/portdiag.sh.before ]]
for entry in 'portdiag.rc /system/etc/init/zzz-logcap.rc' 'portdiag.sh /system/etc/portdiag.sh'; do
    read -r source target <<< "$entry"
    debugfs -R "dump $target $backup/$source.before" "$image"
    [[ -s $backup/$source.before ]]
done
for entry in 'portdiag.rc /system/etc/init/zzz-logcap.rc' 'portdiag.sh /system/etc/portdiag.sh'; do
    read -r source target <<< "$entry"
    debugfs -w -R "rm $target" "$image"
    debugfs -w -R "write $project/device/brcm/rpi5/$source $target" "$image"
    debugfs -w -R "sif $target mode 0100644" "$image"
    debugfs -w -R "sif $target uid 0" "$image"
    debugfs -w -R "sif $target gid 0" "$image"
    debugfs -w -R "ea_set $target security.selinux u:object_r:system_file:s0" "$image"
    debugfs -R "dump $target $backup/$source.after" "$image"
    cmp "$project/device/brcm/rpi5/$source" "$backup/$source.after"
    metadata=$(debugfs -R "stat $target" "$image" 2>/dev/null)
    [[ $metadata == *'Mode:  0644'* && $metadata == *'User:     0   Group:     0'* ]]
    label=$(debugfs -R "ea_get $target security.selinux" "$image" 2>/dev/null)
    [[ $label == *'u:object_r:system_file:s0'* ]]
done
e2fsck -fn "$image"
echo 'Capture configuration updated and checked; boot test pending.'
