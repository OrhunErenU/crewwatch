#!/usr/bin/env bash
# Builds and runs the HOLD host test, then the shared library used by
# features/bridge.py. Run inside WSL (gcc). Vendor code is compiled as-is.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/vendor/cfs-m2s150/apps/tlm_watch"
INC="-I$ROOT/features -I$APP/fsw/src -I$APP/config -I$APP/unit-test/host/stubinc -I$ROOT/vendor/tinyinfer/fsw/inc"
SRC="$ROOT/features/crewwatch_hold.c $ROOT/features/crewwatch_checkin.c $APP/fsw/src/tlm_watch_feature.c $APP/fsw/src/tlm_watch_window.c"
CFLAGS="-O2 -std=gnu99 -Wall -Wextra -Werror"
OUT="${TMPDIR:-/tmp}/crewwatch_test_hold"
gcc $CFLAGS $INC -o "$OUT" "$ROOT/features/test_hold.c" $SRC
"$OUT"
gcc $CFLAGS $INC -o "${OUT}_checkin" "$ROOT/features/test_checkin.c" "$ROOT/features/crewwatch_checkin.c"
"${OUT}_checkin"
gcc $CFLAGS -fPIC -shared $INC -o "$ROOT/features/libcrewwatch_feat.so" $SRC
echo "built features/libcrewwatch_feat.so"
