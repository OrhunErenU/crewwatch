# Board run — NOT DONE in this hackathon (no board access)

**Status (14 Nov 2026): closed as future work.** The team no longer has access to the SmartFusion2
M2S150 board used during the internship. No CrewWatch table, feature, or packet was run on a
board in this hackathon, and nothing in the submission should suggest otherwise (DECISIONS D-23).

## What we can and cannot claim

| Claim | Status | Evidence |
|---|---|---|
| `tinyinfer` is bit-exact on a flight-class board without an FPU | **measured, prior work** (Aug 2026) | 11/11 end-to-end board ↔ ground, cfs-m2s150 README |
| An F=25 Mahalanobis model of this shape costs 0.64 % of a 1 Hz budget on that board; stack 3 416 / 16 384 B | **measured, prior work** | same |
| CrewWatch keeps that model shape (F = 9 ≤ 25, two matvecs + SqErr, int8 weights, int16 activations), so it fits the same budget | **argued, not re-measured** | `model/build_model.py` output: 162-byte tables |
| The same CrewWatch C code gives identical scores on two different machines | **measured, this hackathon** | x86-64 (gcc) vs wasm32 (emcc): 67 388 / 67 388 identical (`tests/test_wasm_bitexact.js`) |
| CrewWatch tables load and run on the board; HOLD runs on the board; wearable packets enter cFS over UART | **not shown** | — |

Suggested wording (rewrite in your own words):

> "The inference engine and model shape we use were measured on a flight-class board without an FPU
> during earlier work (bit-exact, 0.64 % of a 1 Hz budget). CrewWatch keeps the same model shape. We
> did not have the board during the hackathon, so CrewWatch itself was verified on two other platforms
> (ground computer and browser), which produce bit-identical scores."

The video shows the panel only. No board footage, old or new.

## Kept for whoever has a board later

Generated and ready:
- `board/tlm_watch_model_tbl.c` — FAST model, F = 9, 162 B, integer threshold (vendor `quantize.py` format)
- `board/tlm_watch_model_slow_tbl.c` — SLOW model (would also need the window-mean scoring path in the app)

Still to do before a board run:
1. A `tlm_watch_feat_tbl.c` for the wearable packet layout (`sim/crew.py`: src0 `<HHH`, src1 `<HHhH`,
   little-endian), with per-astronaut Bias from `model/model.json` → `tables`.
2. `XFORM_HOLD` (= 4) in `tlm_watch_feature.c`'s switch, calling `features/crewwatch_hold.c` — on a
   branch of cfs-m2s150, not in this repo.
3. A 1 Hz UART replay of the packets into `uart_io`.
4. Compare the board's evidence-packet scores with the host scores for the same replay. Target: bit-exact,
   the same check `tests/test_wasm_bitexact.js` already does for wasm32.
