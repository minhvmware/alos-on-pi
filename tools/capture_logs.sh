#!/usr/bin/env bash
# Capture host-side evidence without changing device configuration.
set -uo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

usage() {
    printf 'Usage: %s [-s SERIAL] [-o OUTPUT_DIR]\n' "${0##*/}"
}
serial=${ANDROID_SERIAL:-}
output=
while getopts ':s:o:h' opt; do
    case "$opt" in
        s) serial=$OPTARG ;;
        o) output=$OPTARG ;;
        h) usage; exit 0 ;;
        :) printf 'Missing value for -%s\n' "$OPTARG" >&2; exit 2 ;;
        *) usage >&2; exit 2 ;;
    esac
done
command -v adb >/dev/null 2>&1 || { printf 'adb is required\n' >&2; exit 1; }
adb_cmd=(adb)
[[ -z $serial ]] || adb_cmd+=(-s "$serial")
state=$("${adb_cmd[@]}" get-state 2>/dev/null) || {
    printf 'No online adb device selected (state: %s)\n' "${state:-unavailable}" >&2
    exit 1
}
[[ $state == device ]] || { printf 'Device is not online: %s\n' "$state" >&2; exit 1; }

if [[ -z $output ]]; then
    project=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
    output=$project/logs/$(date -u +%Y%m%dT%H%M%SZ)
fi
[[ ! -e $output ]] || { printf 'Refusing existing output path: %s\n' "$output" >&2; exit 1; }
mkdir -p "$output"/{boot,kernel,logcat,surfaceflinger,wifi,bluetooth,selinux,system}
output=$(realpath "$output")
status_log=$output/capture-status.tsv
printf 'artifact\texit_status\n' >"$status_log"

capture() {
    local relative=$1
    shift
    local destination=$output/$relative rc
    "$@" >"$destination" 2>"$destination.stderr"
    rc=$?
    printf '%s\t%s\n' "$relative" "$rc" >>"$status_log"
    if ((rc != 0)); then
        printf 'Capture failed (%s): %s\n' "$rc" "$relative" >&2
    fi
    return 0
}

{
    printf 'capture_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'serial=%s\n' "${serial:-default}"
    "${adb_cmd[@]}" get-serialno 2>/dev/null || true
} >"$output/metadata.txt"
capture boot/getprop.txt "${adb_cmd[@]}" shell getprop
capture boot/ps.txt "${adb_cmd[@]}" shell ps -A
capture boot/mounts.txt "${adb_cmd[@]}" shell cat /proc/mounts
capture boot/uptime.txt "${adb_cmd[@]}" shell cat /proc/uptime
capture kernel/dmesg.txt "${adb_cmd[@]}" shell dmesg
capture logcat/all.txt "${adb_cmd[@]}" logcat -b all -d
capture surfaceflinger/SurfaceFlinger.txt "${adb_cmd[@]}" shell dumpsys SurfaceFlinger
capture surfaceflinger/display.txt "${adb_cmd[@]}" shell dumpsys display
capture system/activity.txt "${adb_cmd[@]}" shell dumpsys activity
capture system/package.txt "${adb_cmd[@]}" shell dumpsys package
capture system/media-codec.txt "${adb_cmd[@]}" shell dumpsys media.codec
capture system/input.txt "${adb_cmd[@]}" shell dumpsys input
capture wifi/wifi.txt "${adb_cmd[@]}" shell dumpsys wifi
capture wifi/ip-link.txt "${adb_cmd[@]}" shell ip link
capture wifi/iw-dev.txt "${adb_cmd[@]}" shell iw dev
capture bluetooth/bluetooth_manager.txt "${adb_cmd[@]}" shell dumpsys bluetooth_manager
capture selinux/enforce.txt "${adb_cmd[@]}" shell getenforce

for source in kernel/dmesg.txt logcat/all.txt; do
    [[ -f $output/$source ]] || continue
    grep -i 'avc:.*denied' "$output/$source" >"$output/selinux/${source//\//_}.denials.txt" || true
done
printf 'Logs captured at %s; see capture-status.tsv for failures.\n' "$output"
