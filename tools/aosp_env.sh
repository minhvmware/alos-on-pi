#!/usr/bin/env bash
# Source in the AOSP workspace shell to use project-local host build tools.
_ALUMINIUM_TOOLS_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ALUMINIUM_RPI5_ROOT=$(cd -- "$_ALUMINIUM_TOOLS_DIR/.." && pwd)
_BUILD_DEPS="$ALUMINIUM_RPI5_ROOT/toolchain/fedora-builddeps"
export ALUMINIUM_RPI5_ROOT
export PATH="$ALUMINIUM_RPI5_ROOT/toolchain/bin:$_BUILD_DEPS/usr/bin:$PATH"
export CPATH="$_BUILD_DEPS/usr/include${CPATH:+:$CPATH}"
export LIBRARY_PATH="$_BUILD_DEPS/usr/lib64:$_BUILD_DEPS/usr/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export PKG_CONFIG_PATH="$_BUILD_DEPS/usr/lib64/pkgconfig:$_BUILD_DEPS/usr/share/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export CCACHE_DIR="$ALUMINIUM_RPI5_ROOT/toolchain/ccache"
unset _ALUMINIUM_TOOLS_DIR _BUILD_DEPS
