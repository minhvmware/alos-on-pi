#!/usr/bin/env bash
# Build the host validators referenced by the historical SELinux trial tools.
set -euo pipefail
project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
aosp=${1:?usage: build_policy_tools.sh AOSP_WORKSPACE}
[[ -f $aosp/external/selinux/secilc/secilc.c && -f $aosp/system/sepolicy/tools/check_seapp.c ]] || {
    echo 'Missing AOSP SELinux sources' >&2; exit 1;
}
mkdir -p "$project/work/mapper-review" "$project/work/taskmanager-review"
cc "$aosp/external/selinux/secilc/secilc.c" -lsepol \
    -o "$project/work/mapper-review/secilc"
cc -DLINK_SEPOL_STATIC -DHAVE_REALLOCARRAY -DPCRE2_CODE_UNIT_WIDTH=8 \
    -ffunction-sections -fdata-sections -Wl,--gc-sections \
    -I "$aosp/external/selinux/libsepol/include" \
    -I "$aosp/external/selinux/libsepol/src" \
    "$aosp/system/sepolicy/tools/check_seapp.c" \
    "$aosp/external/selinux/libsepol/src/ebitmap.c" \
    "$aosp/external/selinux/libsepol/src/hashtab.c" -lsepol -lpcre2-8 \
    -o "$project/work/taskmanager-review/checkseapp"
printf 'Built secilc and checkseapp under %s/work\n' "$project"
