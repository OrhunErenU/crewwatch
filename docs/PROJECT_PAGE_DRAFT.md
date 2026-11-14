# DRAFT — rewrite in your own words

> Space Apps 2026 project page fields. English is required. Judges notice LLM-sounding text, so
> rewrite every paragraph yourselves and keep only the facts. Numbers come from `eval/RESULTS.md`; if
> you re-run the evaluation, update them here.

## Project name
CrewWatch

## High-level project summary
*(what / how it addresses the challenge / why it matters — 3 sentences)*

- On a Mars mission a message to Earth takes 3–22 minutes one way, and some periods have no link at all.
  Health warnings therefore have to be produced on board.
- CrewWatch watches the crew's wearable data on the spacecraft computer. It flags two kinds of
  problem: sensor faults (frozen or silent sensors, which per-channel limit checks cannot see) and
  clear limit violations. It tells the astronaut what to check, in plain words.
- It is integer-only, bit-reproducible C code built on an inference engine that was measured on a
  flight-class processor without an FPU in earlier work. The same input gives the same decision on
  the ground computer and in the browser (67 388 / 67 388 scores identical).

## Link to project demo
TODO (30-second video or ≤ 7 slides, public link)

## Link to final project
TODO (GitHub repo, opened by Orhun)

## Detailed project description
**What it does.** Wearable channels (heart rate, HRV, activity, skin temperature, skin conductance)
arrive as packets. Every second CrewWatch builds a small feature vector (levels, "how long has
this value not changed", "how long since this sensor last spoke"). It scores the vector with a
Mahalanobis model compressed to a 162-byte int8 table, and raises an alert card that says what
to check ("Heart rate has read exactly 115.9 bpm for 98 s while data keeps arriving: re-seat the
chest strap").

**How we tested it — honestly.** Normal behaviour comes from real recordings (PPG-DaLiA, 15 people, daily
activities). We do not simulate normal data. We inject five fault types on top of 4 held-out
people, and compare three detectors at the same false-alarm budget: per-channel range check,
range + a "value unchanged" rule, and CrewWatch.

| | Range | Range + HOLD | CrewWatch |
|---|---|---|---|
| frozen HR sensor | blind | 100 % | 100 % |
| silent chest strap | blind | 100 % (8 s) | 100 % (3 s) |
| bradycardia (limit violation) | **77 %** | **77 %** | 32 % |
| HR not following activity / slow drift | not above chance | not above chance | not above chance |
| false alarms on unseen people | 2.9 % of seconds | 2.9 % | **0.35 %** |

What we learned: a limit check is the right tool for clear limit violations. Sensor faults need
something that looks at "unchanged" and "silent". CrewWatch does that in one deterministic model,
with far fewer false alarms on new people. Slow physiological drift is **not** solved at 1 Hz with
wrist sensors, by us or by the baselines. We report that as the next problem, not as a success.

**Benefits.** Works without Earth. Deterministic: the same C code compiled for the ground computer
(x86-64, gcc) and for the browser (WebAssembly) gives bit-identical scores on all 67 388 scored
slots of our demo. The panel re-checks this live when it opens. The same inference engine was
measured bit-exact on a flight-class board during prior work. We had no board during the hackathon,
so CrewWatch itself was not run on hardware; that is the next step. Integer and float decisions differ on
0.024 % of seconds. Small: 162 B per model table. Updating the model
means uplinking a new table; it is updated on the ground, not trained in orbit.

**Tools.** C (flight inference `tinyinfer`, cFS feature code), Python (ctypes bridge, evaluation, no ML
framework), plain HTML/JS panel (offline, no build step), WSL/gcc.

**Prior work (disclosed).** The integer inference engine and cFS feature code were written before the
hackathon during a TÜBİTAK UZAY internship and are open source. We reused them unchanged. In the
hackathon we built the HOLD transform, the wearable pipeline, the fault injector, the evaluation and
the panel. See `PRIOR_WORK.md`.

## Use of Super Intelligence (SI)
We used an AI coding assistant (Claude Code) to write most of the hackathon code and first drafts of
the documents. The team designed the approach, reviewed and ran everything, and rewrote the text.
Files that were written with AI help say so in their header; full list in `AI_USE.md`. No AI-generated
images, audio or data.

## NASA data
- **NASA CCMC DONKI** — Solar Energetic Particle events 2024–2026 (214 events), shown on the radiation panel.
- **MSL/RAD** published dose rates (Zeitlin et al. 2013, Hassler et al. 2014) for the dose baseline.
- NASA Human Research Program / NTRS literature for context (EIMO, sleep, bone loss) — see `data/SOURCES.md`.

## Space agency partner data and other references
- PPG-DaLiA (Reiss et al. 2019, CC BY 4.0) — all normal physiological data.
- Board telemetry dataset, doi:10.5281/zenodo.22045173 (CC BY 4.0, team's own prior work).
- Full reference list: `data/SOURCES.md`.
