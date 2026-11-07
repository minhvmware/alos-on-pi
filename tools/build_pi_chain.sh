#!/usr/bin/env bash
# Retry sync, build aosp_rpi5, then create the rootless SD image.
set -uo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=aosp_env.sh
source "$SCRIPT_DIR/aosp_env.sh"

workspace=${1:?usage: build_pi_chain.sh AOSP_WORKSPACE [OUTPUT_DIR]}
output_dir=${2:-"$SCRIPT_DIR/../work/images"}
max_sync_attempts=${MAX_SYNC_ATTEMPTS:-10}

[[ -f $workspace/build/envsetup.sh ]] || { printf 'Not an AOSP workspace: %s\n' "$workspace" >&2; exit 1; }

proxy_port=${PROXY_PORT:-8899}
if ! curl -sS -x "http://127.0.0.1:$proxy_port" -o /dev/null \
        --max-time 5 "https://android.googlesource.com/" >/dev/null 2>&1; then
    nohup python3 "$SCRIPT_DIR/local_proxy.py" --port "$proxy_port" \
        >/tmp/local-proxy.log 2>&1 &
    sleep 2
fi

sync_rc=1
attempt=0
while ((attempt < max_sync_attempts)); do
    attempt=$((attempt + 1))
    printf '=== sync attempt %s/%s ===\n' "$attempt" "$max_sync_attempts"
    # Keep tags enabled so repo can verify the android-17.0.0_r1 tag and stay
    # shallow. --no-tags/--optimized-fetch caused a full-history fallback.
    # Abort stalled HTTP fetches and use the AOSP mirror for reliability.
    (cd "$workspace" && \
        GIT_CONFIG_COUNT=5 \
        GIT_CONFIG_KEY_0=http.lowSpeedLimit GIT_CONFIG_VALUE_0=1000 \
        GIT_CONFIG_KEY_1=http.lowSpeedTime GIT_CONFIG_VALUE_1=30 \
        GIT_CONFIG_KEY_2=url.https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/.insteadOf \
        GIT_CONFIG_VALUE_2=https://android.googlesource.com/ \
        GIT_CONFIG_KEY_3=http.version GIT_CONFIG_VALUE_3=HTTP/1.1 \
        GIT_CONFIG_KEY_4=http.proxy GIT_CONFIG_VALUE_4=http://127.0.0.1:$proxy_port \
        repo sync -c -j4 --retry-fetches=10 --no-clone-bundle --prune)
    sync_rc=$?
    ((sync_rc == 0)) && break
    printf 'sync attempt %s failed rc=%s; retrying after 30s\n' "$attempt" "$sync_rc"
    sleep 30
done
if ((sync_rc != 0)); then
    printf 'Sync failed after %s attempts\n' "$attempt" >&2
    exit "$sync_rc"
fi

printf '=== build ===\n'
JOBS=${JOBS:-4} "$SCRIPT_DIR/build_image.sh" "$workspace"
build_rc=$?
((build_rc == 0)) || { printf 'Build failed rc=%s\n' "$build_rc" >&2; exit "$build_rc"; }

printf '=== package image ===\n'
"$SCRIPT_DIR/make_rpi5_image.sh" "$workspace" "$output_dir"
