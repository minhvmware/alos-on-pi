#!/usr/bin/env bash
# Explicit-device SD writer with safety checks. Requires --yes to write.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: flash_rpi5_sd.sh --image IMAGE --device /dev/sdX --yes [--boot-mode sd|usb] [--allow-non-removable]
       flash_rpi5_sd.sh --list

Never guesses the target device. Refuses mounted targets and undersized media.
--boot-mode usb patches /boot/config.txt in the image to use android-usb instead
of android-sdcard (for USB SSD/enclosure boot).
EOF
}

image=
device=
confirm=0
allow_non_removable=0
boot_mode=sd
while (($#)); do
    case "$1" in
        --image) image=${2:?missing value}; shift 2 ;;
        --device) device=${2:?missing value}; shift 2 ;;
        --boot-mode) boot_mode=${2:?missing value}; shift 2 ;;
        --yes) confirm=1; shift ;;
        --allow-non-removable) allow_non_removable=1; shift ;;
        --list) lsblk -o NAME,SIZE,TYPE,RM,RO,MODEL,TRAN,MOUNTPOINTS; exit 0 ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done
[[ $boot_mode == sd || $boot_mode == usb ]] || { printf 'Invalid --boot-mode: %s\n' "$boot_mode" >&2; exit 2; }
[[ -n $image && -n $device ]] || { usage >&2; exit 2; }
[[ -f $image ]] || { printf 'Image not found: %s\n' "$image" >&2; exit 1; }
[[ $device == /dev/* ]] || { printf 'Device must be /dev/*: %s\n' "$device" >&2; exit 1; }
[[ -b $device ]] || { printf 'Not a block device: %s\n' "$device" >&2; exit 1; }
((confirm)) || { printf 'Refusing to write without --yes\n' >&2; exit 1; }

name=${device##*/}
removable=$(lsblk -ndo RM "$device" | tr -d ' ')
size=$(lsblk -ndo SIZE -b "$device" | tr -d ' ')
image_size=$(stat -c %s "$image")
printf 'Target: %s removable=%s size=%s\n' "$device" "$removable" "$size"
lsblk -o NAME,SIZE,TYPE,RM,MOUNTPOINTS "$device"
if [[ $removable != 1 && $allow_non_removable -ne 1 ]]; then
    printf 'Target is not removable; pass --allow-non-removable after verifying it is the SD/SSD.\n' >&2
    exit 1
fi
if ((image_size > size)); then
    printf 'Image (%s) larger than target (%s)\n' "$image_size" "$size" >&2
    exit 1
fi
while IFS= read -r mountpoint; do
    [[ -n $mountpoint ]] || continue
    printf 'Target has mounted filesystem: %s\n' "$mountpoint" >&2
    exit 1
done < <(lsblk -nlo MOUNTPOINTS "$device")

if [[ $boot_mode == usb ]]; then
    command -v mcopy >/dev/null 2>&1 || {
        printf 'mcopy (mtools) is required for --boot-mode usb\n' >&2
        exit 1
    }
    tmpdir=$(mktemp -d)
    trap 'rm -rf "$tmpdir"' EXIT
    mcopy -i "$image@@1048576" ::/config.txt "$tmpdir/config.txt"
    sed -i \
        -e 's|^dtoverlay=android-sdcard|#dtoverlay=android-sdcard|' \
        -e 's|^#dtoverlay=android-usb|dtoverlay=android-usb|' \
        "$tmpdir/config.txt"
    mcopy -o -i "$image@@1048576" "$tmpdir/config.txt" ::/config.txt
    printf 'Patched boot config: android-usb enabled\n'
fi

printf 'Writing %s to %s ...\n' "$image" "$device"
sudo dd if="$image" of="$device" bs=4M status=progress conv=fsync
sync
printf 'Done. Remove the target and boot the Pi 5 (%s mode).\n' "$boot_mode"
