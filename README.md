# CrewWatch

On-board early warning for crew wearables. NASA Space Apps Challenge 2026, challenge
*Create Health Monitoring Software for Astronauts on Space Missions*.

On a Mars mission, Earth is 3–22 light-minutes away and sometimes out of reach. CrewWatch runs on the
spacecraft computer. It flags wearable sensor faults that per-channel limit checks cannot see
(frozen or silent sensors) and tells the astronaut what to check. When it suspects a sensor, it asks
the astronaut for a 15-second hand pulse count and says which one to trust. The same panel takes a
daily self check-in (blood pressure, temperature, glucose, sleep, mood) against published thresholds. Every score comes from
integer-only, bit-reproducible flight C code (no FPU needed).

**Demo video (29 s):** [`docs/crewwatch-demo.mp4`](docs/crewwatch-demo.mp4), a screen recording of the panel
(`web/index.html?demo`), recorded automatically with `scripts/record_demo.js`.

**Start here:** [`PROGRESS.md`](PROGRESS.md) · results [`eval/RESULTS.md`](eval/RESULTS.md) ·
limits [`LIMITATIONS.md`](LIMITATIONS.md) · decisions [`DECISIONS.md`](DECISIONS.md) ·
prior work [`PRIOR_WORK.md`](PRIOR_WORK.md) · AI use [`AI_USE.md`](AI_USE.md) ·
sources [`data/SOURCES.md`](data/SOURCES.md)

## Run the panel
Open `web/index.html` in any browser. It works offline. Scores are pre-computed by the flight code
(`web/export_demo.py`). On load, the browser also **recomputes every score** with the same flight C
compiled to WebAssembly (`web/crewwatch_wasm.js`, 4.3 KB) and shows that the two match bit for bit
(`node tests/test_wasm_bitexact.js` checks the same thing from the command line).

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
`web/` panel · `board/` generated cFS table sources (not run on hardware, see `board/RUNBOOK.md`) · `docs/` submission drafts ·
`vendor/` (git-ignored) tinyinfer + cfs-m2s150, unmodified.

## License
Apache-2.0 for code written here (same as the vendor repos). Derived data in `data/dalia_1hz/` is
CC BY 4.0 (PPG-DaLiA, Reiss et al. 2019).
