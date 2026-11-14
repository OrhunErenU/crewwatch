# DECISIONS — one line each, newest last

Made while the team lead was asleep (ROADMAP: "pick the most reasonable reading, write it here, continue").

| # | When | Decision | Why |
|---|---|---|---|
| D-01 | 11-14 | Repo lives at `C:\Users\orhun\crewwatch`, branch `main`, no remote. | Same place as other projects; Orhun opens GitHub. |
| D-02 | 11-14 | `vendor/` is git-ignored; `scripts/setup_vendor.sh` clones `tinyinfer@4ebb2d5` + `cfs-m2s150@00b4513` and adds the `libs/tinyinfer` symlink (untracked, inside the clone only). | Rule 7: vendor repos untouched; pinned commits keep it reproducible. |
| D-03 | 11-14 | All Python that calls C runs in WSL Ubuntu (gcc 13, python3.12, numpy 2.5 system). numpy is used **only** for dataset loading/resampling, never for scores. | Roadmap §1.1; rule 1. |
| D-04 | 11-14 | HOLD is **not** added to vendor `tlm_watch_feature.c`. New `features/crewwatch_hold.c` keeps only the counter; scaling is delegated to the vendor AGE path (`TLM_WATCH_ApplyTransform` with `XFORM_AGE`). | Rule 7 (no vendor edits) + rule 1 (no arithmetic written twice). In flight this becomes `XFORM_HOLD=4` in the same switch. |
| D-05 | 11-14 | Space Apps guide (read 11-14): demo = **video ≤ 30 s or ≤ 7 slides**; deadline Sun 15 Nov 23:59 local; English; ≥ 1 NASA data/resource needed for Global Award; SI (AI) use must be acknowledged in descriptive text **and metadata** for code/data; SI must not be used to come up with the idea. | Drives `docs/` drafts and `AI_USE.md`. |
| D-06 | 11-14 | NASA data in the product: DONKI SEP events (CCMC) for the radiation panel, NASA HRP/NTRS sources for parameters. Moved DONKI from "P1 nice-to-have" to "must ship". | Global Award eligibility (D-05). |
| D-07 | 11-14 | Primary dataset: **PPG-DaLiA** (UCI, CC BY 4.0, 15 subjects, ~2.5 h each, daily activities). Channels used: HR (ECG ground truth), HRV-RMSSD (from provided R-peaks), skin temp + EDA + activity (wrist). | Only open set with activity↔HR coupling *and* temperature in one recording. |
| D-08 | 11-14 | **No SpO₂ channel** (DaLiA has none; inventing one is forbidden). Fault type 5 "explicit range violation" is done on **HR** (bradycardia ramp below the learned lower limit) instead of SpO₂. | Roadmap: "eksik kanal varsa F'yi küçült, kanal uydurma". |
