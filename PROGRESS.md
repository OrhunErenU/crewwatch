# PROGRESS — read this first when you wake up

## Status (Sat 14 Nov, updated by Claude Code)

### P0
- [x] **Setup + `verify_ctypes.py` GECTI** — `bash scripts/setup_vendor.sh` (WSL) clones vendor @ pinned commits, prints `GECTI`, builds HOLD lib, runs both self-tests.
- [x] **HOLD transform in C + host test** (P1 item, done early because the features need it) — `bash features/build_host.sh` → `crewwatch_hold: 15/15 checks passed`; `python3 features/bridge.py` → `7/7 ticks match`.
- [ ] Real dataset (PPG-DaLiA) downloaded → 1 Hz → person-wise split
- [ ] Fault injector on real recordings + SOURCES.md (code done: `sim/faults.py`, sources: `data/SOURCES.md`)
- [ ] Model table + integer threshold (code done: `model/build_model.py`)
- [ ] `eval/RESULTS.md` (code done: `eval/evaluate.py`, `eval/report.py`)
- [ ] Offline panel (code done: `web/index.html`, data: `web/export_demo.py`)

### Also done
- NASA DONKI SEP events fetched (214 events, 2024-01 … 2026-11): `data/nasa/donki_sep.json` — needed for Global Award eligibility.
- Space Apps guide checked → see DECISIONS D-05 (30-s video, SI disclosure).
- `ASSETS.md`, `PRIOR_WORK.md`, `LIMITATIONS.md`, `AI_USE.md`, `DECISIONS.md`.

## How to reproduce everything (WSL Ubuntu)

```bash
cd /mnt/c/Users/orhun/crewwatch
bash scripts/setup_vendor.sh
python3 sim/fetch_donki.py
# PPG-DaLiA: data/raw/dalia/ppg_dalia.zip from UCI #495, unzip, then:
python3 sim/prep_dalia.py --raw data/raw/dalia/PPG_FieldStudy --out data/dalia_1hz
python3 model/build_model.py
python3 eval/evaluate.py
python3 eval/report.py
python3 web/export_demo.py
# open web/index.html in a browser (works offline, file://)
```
