#!/usr/bin/env bash
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/../.." && pwd)
root=$(dirname -- "$project")
cc="$root/aosp-rpi5/prebuilts/clang/host/linux-x86/clang-r596125/bin/clang"
sdk="$root/aosp-rpi5/prebuilts/runtime/mainline/runtime/sdk/android/arm64/lib"
mkdir -p "$project/work/vulkan"
"$cc" --target=aarch64-linux-android37 -ffreestanding -fPIE -pie -nostdlib -fuse-ld=lld -Wall -Wextra -Werror \
 -I "$root/aosp-rpi5/external/vulkan-headers/include" \
 -Wl,-dynamic-linker,/system/bin/linker64 \
 "$sdk/crtbegin_dynamic.o" "$project/tools/vulkan/v3dv_smoke.c" \
 -L "$sdk" -lc -ldl "$sdk/crtend_android.o" -o "$project/work/vulkan/v3dv-smoke"
file "$project/work/vulkan/v3dv-smoke"
