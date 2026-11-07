#!/usr/bin/env bash
# Capture Vulkan capabilities and exercise real Broadcom GPU work via existing SSH.
set -euo pipefail
project=$(cd -- "$(dirname -- "$0")/../.." && pwd)
host=${1:?usage: check_live.sh PI_IP}
out="$project/work/vulkan/live-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out"
ssh_tool="$project/tools/pi_ssh.sh"
bash "$project/tools/vulkan/build.sh" > "$out/build.log"
"$ssh_tool" "$host" 'cat > /data/local/tmp/hoshino-v3dv-smoke; chmod 755 /data/local/tmp/hoshino-v3dv-smoke' < "$project/work/vulkan/v3dv-smoke"
"$ssh_tool" "$host" 'getprop ro.hardware.vulkan; getprop ro.vulkan.apex; pm list features' > "$out/features.txt"
"$ssh_tool" "$host" 'cmd gpu vkjson' > "$out/vkjson.json" 2> "$out/vkjson.stderr"
"$ssh_tool" "$host" 'timeout 45 /data/local/tmp/hoshino-v3dv-smoke' > "$out/smoke.log" 2>&1
cat "$out/smoke.log"
grep -q '^PASS: Broadcom Vulkan device' "$out/smoke.log"
printf 'Evidence: %s\n' "$out"
