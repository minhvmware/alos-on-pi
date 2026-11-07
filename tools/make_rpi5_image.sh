#!/usr/bin/env bash
# Rootless equivalent of device/brcm/rpi5/mkimg.sh. No loop device or sudo.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=aosp_env.sh
source "$SCRIPT_DIR/aosp_env.sh"

usage() {
    cat <<'EOF'
Usage: make_rpi5_image.sh AOSP_WORKSPACE [OUTPUT_DIR]

Requires boot.img, system.img, vendor.img from a completed aosp_rpi5 build.
Creates a 15,360,000,000-byte MBR image with p1 boot, p5 system, p6 vendor,
p7 metadata and p3 userdata, then writes a .sha256 file.
EOF
}
(($# >= 1 && $# <= 2)) || { usage >&2; exit 2; }
workspace=$(realpath "$1")
output_dir=${2:-"$SCRIPT_DIR/../work/images"}
[[ -f $workspace/build/envsetup.sh ]] || { printf 'Not an AOSP workspace: %s\n' "$workspace" >&2; exit 1; }
for tool in fdisk sfdisk python3 mkfs.ext4 dd truncate sha256sum blkid; do
    command -v "$tool" >/dev/null 2>&1 || { printf 'Missing tool: %s\n' "$tool" >&2; exit 1; }
done

mkdir -p "$output_dir"
cd "$workspace"
# shellcheck disable=SC1091
source build/envsetup.sh
lunch aosp_rpi5-cp2a-userdebug >/dev/null
for image in boot.img system.img vendor.img; do
    [[ -f $ANDROID_PRODUCT_OUT/$image ]] || { printf 'Missing build output: %s\n' "$ANDROID_PRODUCT_OUT/$image" >&2; exit 1; }
done

img_name="RaspberryVanillaAOSP17-$(date +%Y%m%d)-rpi5.img"
img="$output_dir/$img_name"
[[ ! -e $img ]] || { printf 'Refusing existing image: %s\n' "$img" >&2; exit 1; }
img_size=15360000000
truncate -s "$img_size" "$img"

fdisk "$img" >/dev/null 2>&1 <<'EOF'
o
n
p
1

+128M
n
e
2

+3476M
n
l

+3072M
n
l

+384M
n
l

+16M
n
p
3


t
1
c
a
1
w
EOF

mapfile -t partitions < <(python3 - "$img" <<'PY'
import json, subprocess, sys
table = json.loads(subprocess.run(["sfdisk", "--json", sys.argv[1]], check=True,
                                  capture_output=True, text=True).stdout)["partitiontable"]
sector = int(table.get("sectorSize", 512))
for part in table["partitions"]:
    number = part["node"].rsplit("img", 1)[-1].lstrip("p")
    print(number, int(part["start"]) * sector, int(part["size"]) * sector)
PY
)
declare -A offset size
for row in "${partitions[@]}"; do
    read -r number start length <<<"$row"
    offset[$number]=$start
    size[$number]=$length
done
for number in 1 3 5 6 7; do
    [[ -n ${offset[$number]:-} ]] || { printf 'Partition p%s missing\n' "$number" >&2; exit 1; }
done

copy_partition() {
    local source=$1 number=$2
    ((offset[$number] % 1048576 == 0)) || { printf 'p%s offset is not MiB aligned\n' "$number" >&2; exit 1; }
    ((size[$number] >= $(stat -c %s "$source"))) || { printf '%s does not fit p%s\n' "$source" "$number" >&2; exit 1; }
    dd if="$source" of="$img" bs=1M seek=$((offset[$number] / 1048576)) \
        conv=notrunc,sparse status=none
}
copy_partition "$ANDROID_PRODUCT_OUT/boot.img" 1
copy_partition "$ANDROID_PRODUCT_OUT/system.img" 5
copy_partition "$ANDROID_PRODUCT_OUT/vendor.img" 6
mkfs.ext4 -q -F -L metadata -I 512 -b 4096 -E offset="${offset[7]}" "$img" $((size[7] / 4096))
mkfs.ext4 -q -F -L userdata -I 512 -b 4096 -E offset="${offset[3]}" "$img" $((size[3] / 4096))
sync

sha256sum "$img" | tee "$img.sha256"
printf 'Image: %s\n' "$img"
printf 'Partitions:\n'
sfdisk --dump "$img" | sed -n '1,40p'
