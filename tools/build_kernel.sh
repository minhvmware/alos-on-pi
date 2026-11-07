#!/usr/bin/env bash
# Build the unmodified Raspberry Vanilla Android 17 Pi 5 kernel.
set -euo pipefail

if (($# != 1)) || [[ $1 == -h || $1 == --help ]]; then
    printf 'Usage: %s KERNEL_WORKSPACE\n' "${0##*/}"
    printf 'Initialize/sync common-android17-6.18-lts in that workspace first.\n'
    exit "$(($# == 1 ? 0 : 2))"
fi
workspace=$(realpath "$1")
[[ -d $workspace/.repo ]] || { printf 'Missing repo workspace: %s\n' "$workspace" >&2; exit 1; }
[[ -x $workspace/tools/bazel ]] || { printf 'Missing executable tools/bazel\n' >&2; exit 1; }
cd "$workspace"
tools/bazel build --config=fast --config=stamp //common:rpi5
out=$workspace/bazel-bin/common/rpi5/arch/arm64/boot
[[ -f $out/Image ]] || { printf 'Build ended without %s/Image\n' "$out" >&2; exit 1; }
compgen -G "$out/bcm2712*-rpi-*.dtb" >/dev/null || {
    printf 'Build ended without a BCM2712 DTB in %s\n' "$out" >&2
    exit 1
}
compgen -G "$out/overlays/vc4-kms-v3d*.dtbo" >/dev/null || {
    printf 'Build ended without a VC4 KMS V3D overlay in %s/overlays\n' "$out" >&2
    exit 1
}
printf 'Kernel artifacts:\n%s\n' "$out"
find "$out" -maxdepth 2 -type f \( -name Image -o -name '*.dtb' -o -name '*.dtbo' \) -print | sort
