# PROGRESS — read this first when you wake up

## TL;DR (Sat 14 Nov, Claude Code) — engineering done, team steps listed below

**P0 done.** Pipeline runs end to end on real data; panel opens offline.
**The headline result is not the one the roadmap expected. Read `eval/RESULTS.md` → "Reading this table honestly" before writing the pitch.**

| Fault | Range | Range+HOLD | CrewWatch | verdict |
|---|---|---|---|---|
| 1 frozen HR | 13 % (chance 12) | **100 %** | **100 %** | simple rule = CrewWatch |
| 2 silent strap | 8 % (12) | **100 %** | **100 %** (3 s vs 8 s) | simple rule ≈ CrewWatch, CW faster |
| 3 HR ignores activity | 21 % (12) | 21 % (14) | 5 % (4) | **nobody** clearly above chance |
| 4 fever-like drift | 40 % (43) | 43 % (52) | 22 % (26) | **nobody** above chance |
| 5 bradycardia | **77 %** | **77 %** | 32 % | range check wins (expected) |
| false alarms, new people | 2.9 % | 2.9 % | **0.35 %** | CrewWatch ~8× fewer |

What CrewWatch can honestly claim: sensor-health faults (frozen/silent wearable) in one deterministic
integer model, with ~8× fewer false alarms on unseen people, int = float (0.024 % decision difference).
What it cannot claim: catching slow physiological drift at 1 Hz with wrist sensors.
**Team decision needed:** pitch around this (DECISIONS D-20).

## Checklist

### P0
- [x] Setup + `verify_ctypes.py` **GECTI** — `bash scripts/setup_vendor.sh`
- [x] PPG-DaLiA (15 people) → 1 Hz, person-wise split — `bash scripts/prep_dalia.sh`, see `data/DATASETS.md`
- [x] Fault injector on real recordings, 5 types, every parameter sourced or labelled — `sim/faults.py`, `data/SOURCES.md`
- [x] Integer Mahalanobis tables + thresholds via ctypes — `python3 model/build_model.py` (F = 9 → 162 B per model; fast + slow)
- [x] `eval/RESULTS.md` three detectors, matched budget, chance levels — `python3 eval/evaluate.py && python3 eval/report.py`
- [x] Offline panel — `python3 web/export_demo.py`, then open `web/index.html` (works from file://)

### P1
- [x] HOLD in C + host test (15/15) + bridge test (7/7)
- [x] `explain/` astronaut language, self-test PASS (every sentence carries a number, no diagnosis words)
- [x] DONKI radiation panel (214 SEP events), bone + sleep reference panels (labelled "not crew data")
- [x] `docs/` drafts (DRAFT-marked): `PROJECT_PAGE_DRAFT.md`, `VIDEO_SCRIPT.md` (≤ 30 s), `SLIDES_OUTLINE.md` (≤ 7)

### P2
- [x] **WASM bit-exact** — `node tests/test_wasm_bitexact.js` → `PASS -- browser (wasm32) and host (x86-64 gcc) give bit-identical scores on 67388 score slots` (67 136 non-null; negative control: Bias+1 LSB → 15 630 differ). Panel re-runs this live in the browser (45 ms) and shows the count. Build: `bash scripts/install_emsdk.sh` once, then `bash web/wasm/build_wasm.sh` (WSL).
- [x] ~~Board run~~ — **closed: no board access** (D-23). Table sources are generated (`board/*.c`). `board/RUNBOOK.md` now lists exactly what may and may not be claimed, plus the steps left for anyone who has a board later. The video shows the panel only.

## Engineering status: DONE (Sat 14 Nov)
- `bash scripts/run_all.sh` (WSL) re-runs model → eval → panel → wasm → all tests. A full re-run
  reproduced `model.json`, `results.json`, `data.js`, `crewwatch.wasm` and both board tables
  **byte for byte** (sha256 identical).
- `data/SOURCES.md`: no "to confirm" rows left (EIMO NTRS, IEEE Sys J 2018, van Hees 2013, Lang 2004,
  Mars light time all checked). A wrong bone-loss figure was corrected (ISS hip trabecular 2.2–2.7 %/month).
- Panel checked at 1009 px and at phone width (375 px): no horizontal scroll, controls usable.
- Fixed: on screens with display scaling ≠ 100 % the chart canvas grew by that factor on every frame
  until it went blank (seen at 125 %). Fixed by reading the logical height once.
- Added a 30-s scripted demo mode for recording (`?demo`, or the header button).

## What only the team can do (in this order)
1. **Decide the pitch** around the measured result (D-20, `eval/READING.md`). Don't use the roadmap's
   original "types 3–4 only the joint model catches" line; the data does not support it.
2. **Rewrite** `docs/PROJECT_PAGE_DRAFT.md`, `docs/VIDEO_SCRIPT.md`, `docs/SLIDES_OUTLINE.md`,
   `eval/READING.md` in your own words (they start with `DRAFT — rewrite…`).
3. **Record the 30-s video:** open `web/index.html?demo&team=YourTeamName`, press F11, start Win+Alt+R,
   press F5. The built-in demo runs exactly 30 s with English captions (`docs/VIDEO_SCRIPT.md`). Panel only,
   no board. Upload, make the link public, test it in a private window.
4. ~~GitHub~~ **done:** pushed to https://github.com/OrhunErenU/crewwatch- (public). The repo name ends with
   a hyphen; renaming it to `crewwatch` in GitHub Settings is safe (GitHub redirects the old URL).
   `vendor/` and `data/raw/` are git-ignored by design. The internal plan, the local asset list and
   `.claude/` were removed from the public repo (kept locally, git-ignored) and from the whole git
   history (rewritten and force-pushed on 14 Nov; a pre-rewrite bundle is kept outside the repo).
5. **Space Apps page:** paste the rewritten fields; NASA data = DONKI + RAD; SI question from
   `AI_USE.md`; tick "Confirm All Work is Original" only after reading `PRIOR_WORK.md` together.
6. Submit before **Sun 15 Nov 21:00** (the roadmap's buffer; hard deadline 23:59 local).

## Things found on the way (all in DECISIONS.md)
- **D-13** vendor `DIFF` = counter semantics (unsigned, masked): a 1-LSB drop reads +65535. Fine for counters, wrong for HR. Not used.
- **D-08** PPG-DaLiA has no SpO₂, so fault 5 runs on HR.
- **D-17/18** thresholds were being set by packet-loss spikes. Fixed using validation only. Range limits made personal for fairness.
- Panel bug fixed: range limits were not shifted to the person's baseline in the export.

## Reproduce everything (WSL Ubuntu, ~3 min after download)

```bash
cd /mnt/c/Users/orhun/crewwatch
bash scripts/setup_vendor.sh          # GECTI + 15/15 + 7/7 + window mean
python3 sim/fetch_donki.py
bash scripts/prep_dalia.sh            # needs data/raw/dalia/data.zip (UCI #495)
python3 model/build_model.py
python3 eval/evaluate.py --k-events 15
python3 eval/report.py
python3 web/export_demo.py
bash web/wasm/build_wasm.sh           # needs scripts/install_emsdk.sh once
node tests/test_wasm_bitexact.js      # Windows node or emsdk's node
```
