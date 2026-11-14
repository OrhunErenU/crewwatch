# PRIOR_WORK — what existed before the hackathon vs. what was built in the 48 h

Space Apps asks teams to confirm their work is original. The core engine was
written **before** the event (Orhun's TÜBİTAK UZAY internship, Jul–Aug 2026)
and is open source. We reuse it unchanged and say so.

## Before 14 Nov 2026 (reused, not modified)

| Item | Origin | How CrewWatch uses it |
|---|---|---|
| `tinyinfer` (int8×int16 inference kernel, 428 B `.text`) | github.com/OrhunErenU/tinyinfer @ 4ebb2d5 | Every CrewWatch score is computed by this C code via ctypes |
| `tlm_watch_feature.c` (RAW/DIFF/FLAG/AGE transforms) | github.com/OrhunErenU/cfs-m2s150 @ 00b4513 | All feature values except HOLD's counter |
| `ground/` tools: `tinyinfer_ctypes.py`, `features_ctypes.py`, `quantize.py`, `evaluate.py` (Mahalanobis), `build_maha.py` algebra | same repo | imported as-is from `vendor/` |
| Board measurements (bit-exact 11/11, 0.64 % of 1 Hz budget, stack 3 416 B) | internship, documented in cfs-m2s150 README | quoted, not re-measured |
| Board telemetry dataset | doi:10.5281/zenodo.22045173 | reference only |

## Built during the hackathon (14–15 Nov 2026)

| Path | What |
|---|---|
| `features/crewwatch_hold.{c,h}`, `features/test_hold.c` | **HOLD** transform (new), host test |
| `features/bridge.py` | ctypes engine adding HOLD to the vendor feature flow |
| `sim/prep_dalia.py` | PPG-DaLiA → 1 Hz wearable channels |
| `sim/faults.py` | 5 fault/condition types injected on real recordings |
| `sim/crew.py` | channels, packets, crew split, replay loop |
| `sim/fetch_donki.py` | NASA DONKI SEP download |
| `model/build_model.py` | per-astronaut feature tables + shared Mahalanobis model (adapted from `build_maha.py`) |
| `eval/` | 3-detector comparison at matched false-alarm budget |
| `explain/`, `web/`, `docs/` | astronaut-language alerts, offline panel, submission drafts |
| `web/wasm/cw_glue.c`, `web/wasm/build_wasm.sh`, `web/crewwatch_engine.js`, `tests/test_wasm_bitexact.js` | flight C → wasm32, in-browser recomputation, bit-exact test |
| `features/crewwatch_checkin.{c,h}`, `features/test_checkin.c`, `tests/make_checkin_ref.py` | astronaut self check-in + pulse-vs-wearable cross-check (integer C), host test, host/wasm reference |
| `scripts/record_demo.js`, `scripts/record_server.py` | automatic 30-s demo recording |

Generated with AI assistance (Claude Code) — see `AI_USE.md`.
