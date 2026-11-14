# Board RUNBOOK (P2) — DRAFT, not yet executed

Status: **table sources generated, nothing run on the board.** Until this is done, do not claim that
the CrewWatch tables or HOLD ran on the SmartFusion2 (LIMITATIONS §8).

What exists:
- `board/tlm_watch_model_tbl.c` — FAST model, F = 9, 162 B, integer threshold (vendor `quantize.py` format)
- `board/tlm_watch_model_slow_tbl.c` — SLOW model (needs the window-mean scoring path, not wired in the vendor app)

What is still missing before a board run (Orhun):
1. A feature table `tlm_watch_feat_tbl.c` for the wearable packet layout (`sim/crew.py`: src0 `<HHH`,
   src1 `<HHhH`, little-endian). Per-astronaut Bias comes from `model/model.json` → `tables`.
2. `XFORM_HOLD` (= 4) in `tlm_watch_feature.c`'s switch, calling `crewwatch_hold.c`. **This changes the
   vendor app.** Do it on a branch of cfs-m2s150, not in this repo.
3. A replay script that writes the packets to `uart_io` over COM13 at 1 Hz (reuse `cfs-drop/uart_echo.ps1`
   framing).
4. Compare the board's evidence-packet scores with `eval/` host scores for the same replay. Target: bit-exact.

If the board is not available, the video says "same C code on the host" and shows no board.
