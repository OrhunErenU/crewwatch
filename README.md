# CrewWatch

On-board early warning for crew wearables. NASA Space Apps Challenge 2026, challenge
*Create Health Monitoring Software for Astronauts on Space Missions*.

On a Mars mission, Earth is 3–22 light-minutes away and sometimes out of reach. CrewWatch runs on the
spacecraft computer. It flags wearable sensor faults that per-channel limit checks cannot see
(frozen or silent sensors) and tells the astronaut what to check. Every score comes from
integer-only, bit-reproducible flight C code (no FPU needed).

**Start here:** [`PROGRESS.md`](PROGRESS.md) · results [`eval/RESULTS.md`](eval/RESULTS.md) ·
limits [`LIMITATIONS.md`](LIMITATIONS.md) · decisions [`DECISIONS.md`](DECISIONS.md) ·
prior work [`PRIOR_WORK.md`](PRIOR_WORK.md) · AI use [`AI_USE.md`](AI_USE.md) ·
sources [`data/SOURCES.md`](data/SOURCES.md)

## Run the panel
Open `web/index.html` in any browser. It works offline. Scores are pre-computed by the flight code
(`web/export_demo.py`). The browser only plays them back.

## Reproduce (WSL/Linux, gcc + python3 + numpy for data prep only)
```bash
bash scripts/setup_vendor.sh      # clones prior-work repos (pinned), prints GECTI, runs C + bridge tests
python3 sim/fetch_donki.py        # NASA DONKI SEP events
bash scripts/prep_dalia.sh        # PPG-DaLiA (UCI #495) -> data/dalia_1hz
python3 model/build_model.py
python3 eval/evaluate.py --k-events 15 && python3 eval/report.py
python3 web/export_demo.py
```

## Layout
`features/` HOLD transform (C, new) + ctypes bridge · `sim/` data prep, crew split, fault injector ·
`model/` integer Mahalanobis tables · `eval/` three-detector comparison · `explain/` alert text ·
`web/` panel · `board/` generated cFS table sources · `docs/` submission drafts ·
`vendor/` (git-ignored) tinyinfer + cfs-m2s150, unmodified.

## License
Apache-2.0 for code written here (same as the vendor repos). Derived data in `data/dalia_1hz/` is
CC BY 4.0 (PPG-DaLiA, Reiss et al. 2019).
