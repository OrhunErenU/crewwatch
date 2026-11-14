#!/usr/bin/env bash
# Installs the official Emscripten SDK into ~/emsdk at a PINNED version.
# No sudo, nothing outside ~/emsdk. Run inside WSL.
set -euo pipefail
EMSDK_VERSION="${EMSDK_VERSION:-3.1.74}"
if [ ! -d "$HOME/emsdk/.git" ]; then
  git clone -q https://github.com/emscripten-core/emsdk.git "$HOME/emsdk"
fi
cd "$HOME/emsdk"
./emsdk install "$EMSDK_VERSION"
./emsdk activate "$EMSDK_VERSION"
source ./emsdk_env.sh >/dev/null
emcc --version | head -1
