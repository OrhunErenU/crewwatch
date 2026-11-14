#!/usr/bin/env bash
# Re-runs the whole CrewWatch pipeline from the 1 Hz data onward and every test.
# Run inside WSL from anywhere. Prerequisites: scripts/setup_vendor.sh done,
# data/dalia_1hz present (scripts/prep_dalia.sh), emsdk for the wasm step.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "== C + bridge tests";        bash features/build_host.sh && python3 features/bridge.py
echo "== flight bridge proof";     ( cd vendor/cfs-m2s150/apps/tlm_watch/ground && python3 verify_ctypes.py | tail -2 )
echo "== explain self-test";       python3 explain/explain.py | tail -1
echo "== model";                   python3 model/build_model.py
echo "== evaluation";              python3 eval/evaluate.py --k-events 15 && python3 eval/report.py
echo "== panel data";              python3 web/export_demo.py
echo "== check-in reference";      python3 tests/make_checkin_ref.py
if [ -f "$HOME/emsdk/emsdk_env.sh" ]; then
  echo "== wasm build";            bash web/wasm/build_wasm.sh
  source "$HOME/emsdk/emsdk_env.sh" >/dev/null 2>&1
  echo "== wasm bit-exact";        node tests/test_wasm_bitexact.js
else
  echo "== wasm skipped (no ~/emsdk; run scripts/install_emsdk.sh)"
fi
