#!/usr/bin/env bash
# Reclaim disk after the Pi image is built and verified. Dry-run by default.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: cleanup_pi_build.sh [--analysis] [--out] [--repo] [--source-all]
                           [--ota] [--toolchain-cache] [--all] [--yes]

Always kept: raspberry-vanilla/images/*.img and *.sha256, project docs/tools,
toolchain/bin binaries, logs/evidence text files.
Dry-run unless --yes is given.
EOF
}
do_analysis=0 do_out=0 do_repo=0 do_source_all=0 do_ota=0 do_toolchain=0 confirm=0
(($#)) || { usage >&2; exit 2; }
while (($#)); do
    case "$1" in
        --analysis) do_analysis=1 ;;
        --out) do_out=1 ;;
        --repo) do_repo=1 ;;
        --source-all) do_source_all=1 ;;
        --ota) do_ota=1 ;;
        --toolchain-cache) do_toolchain=1 ;;
        --all) do_analysis=1; do_out=1; do_repo=1; do_ota=1; do_toolchain=1 ;;
        --yes) confirm=1 ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

ROOT=${HOSHINO_WORKSPACE:?Set HOSHINO_WORKSPACE to the workspace to clean}
WORKSPACE=$ROOT/aosp-rpi5
ANALYSIS=$ROOT/aluminium-analysis
IMAGES=$ROOT/raspberry-vanilla/images
OTA=$ROOT/91b269229318b3dae45e08966e69e2991e52c039.zip
TOOLCHAIN=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)/toolchain

if ! compgen -G "$IMAGES/*.img" >/dev/null; then
    printf 'Refusing cleanup: no image found in %s\n' "$IMAGES" >&2
    exit 1
fi
if ! compgen -G "$IMAGES/*.sha256" >/dev/null; then
    printf 'Refusing cleanup: image SHA256 file missing in %s\n' "$IMAGES" >&2
    exit 1
fi

targets=()
((do_analysis)) && targets+=("$ANALYSIS"/*/ota "$ANALYSIS"/*/images "$ANALYSIS"/*/extracted "$ANALYSIS"/*/apex-images "$ANALYSIS"/*/apex-extracted)
((do_out)) && targets+=("$WORKSPACE/out")
((do_repo)) && targets+=("$WORKSPACE/.repo")
((do_source_all)) && targets+=("$WORKSPACE")
((do_ota)) && targets+=("$OTA")
((do_toolchain)) && targets+=("$TOOLCHAIN/go-mod-cache" "$TOOLCHAIN/go-build-cache" "$TOOLCHAIN/android-sdk" "$TOOLCHAIN/src")

printf '%s\n' '== current sizes =='
du -sh "$WORKSPACE" "$ANALYSIS" "$TOOLCHAIN" "$OTA" 2>/dev/null || true
printf '%s\n' '== targets =='
for target in "${targets[@]}"; do
    [[ -e $target ]] || continue
    du -sh "$target" 2>/dev/null || true
done
if ((confirm == 0)); then
    printf '\nDry-run only. Re-run with --yes to delete the listed targets.\n'
    exit 0
fi
for target in "${targets[@]}"; do
    [[ -e $target ]] || continue
    printf 'Removing %s\n' "$target"
    rm -rf -- "$target"
done
printf '\nCleanup done. Kept: %s\n' "$IMAGES"
df -h /home | tail -1
