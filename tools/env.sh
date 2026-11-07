#!/usr/bin/env bash
# Source this file to use the project-local, unprivileged host toolchain.
_ALUMINIUM_TOOLS_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ALUMINIUM_RPI5_ROOT=$(cd -- "$_ALUMINIUM_TOOLS_DIR/.." && pwd)
export ALUMINIUM_RPI5_ROOT
export PATH="$ALUMINIUM_RPI5_ROOT/toolchain/bin:$PATH"
export LD_LIBRARY_PATH="$ALUMINIUM_RPI5_ROOT/toolchain/fedora-erofs/usr/lib64:$ALUMINIUM_RPI5_ROOT/toolchain/fedora-analysis/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
unset _ALUMINIUM_TOOLS_DIR
