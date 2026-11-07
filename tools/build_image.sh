#!/usr/bin/env bash
# Build a clean Raspberry Vanilla baseline; do not point this at an ALOS tree.
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=aosp_env.sh
source "$SCRIPT_DIR/aosp_env.sh"

usage() {
    printf 'Usage: %s AOSP_WORKSPACE [TARGET] [--package]\n' "${0##*/}"
    printf 'Default target: aosp_rpi5-cp2a-userdebug\n'
    printf 'JOBS environment variable controls make parallelism (default: 4).\n'
}
if (($# == 1)) && [[ $1 == -h || $1 == --help ]]; then
    usage
    exit 0
fi
(($# >= 1 && $# <= 3)) || { usage >&2; exit 2; }
workspace=$(realpath "$1")
target=${2:-aosp_rpi5-cp2a-userdebug}
package=0
if [[ ${2:-} == --package ]]; then
    target=aosp_rpi5-cp2a-userdebug
    package=1
elif [[ ${3:-} == --package ]]; then
    package=1
elif (($# == 3)); then
    usage >&2
    exit 2
fi
[[ -f $workspace/build/envsetup.sh ]] || { printf 'Not an AOSP workspace: %s\n' "$workspace" >&2; exit 1; }
[[ -f $workspace/device/brcm/rpi5/BoardConfig.mk ]] || { printf 'Raspberry Pi 5 BSP is missing\n' >&2; exit 1; }
jobs=${JOBS:-4}
cd "$workspace"
# shellcheck disable=SC1091
source build/envsetup.sh
lunch "$target"
make bootimage systemimage vendorimage -j"$jobs"
for image in boot.img system.img vendor.img; do
    [[ -f $ANDROID_PRODUCT_OUT/$image ]] || { printf 'Missing output: %s\n' "$ANDROID_PRODUCT_OUT/$image" >&2; exit 1; }
done
if ((package)); then
    command -v sudo >/dev/null 2>&1 || { printf 'Image packaging requires sudo\n' >&2; exit 1; }
    ./rpi5-mkimg.sh
fi
printf 'Known-good candidate outputs: %s\n' "$ANDROID_PRODUCT_OUT"
printf 'Boot and validate this unmodified baseline before integrating AluminiumOS.\n'
