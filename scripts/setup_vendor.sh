#!/usr/bin/env bash
# Clones the two prior-work repos at pinned commits (unmodified), links
# tinyinfer into the cFS layout tinyinfer_ctypes.py expects, builds the
# CrewWatch feature library and runs both bridge proofs.
# Run inside WSL/Linux (gcc + python3).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/vendor"
clone() { # url dir commit
  if [ ! -d "$ROOT/vendor/$2/.git" ]; then git clone -q "$1" "$ROOT/vendor/$2"; fi
  git -C "$ROOT/vendor/$2" checkout -q "$3"
}
clone https://github.com/OrhunErenU/tinyinfer   tinyinfer  4ebb2d5
clone https://github.com/OrhunErenU/cfs-m2s150  cfs-m2s150 00b4513
mkdir -p "$ROOT/vendor/cfs-m2s150/libs"
[ -e "$ROOT/vendor/cfs-m2s150/libs/tinyinfer" ] || ln -s ../../tinyinfer "$ROOT/vendor/cfs-m2s150/libs/tinyinfer"
( cd "$ROOT/vendor/cfs-m2s150/apps/tlm_watch/ground" && python3 verify_ctypes.py )
bash "$ROOT/features/build_host.sh"
python3 "$ROOT/features/bridge.py"
