# DRAFT — rewrite in your own words

Guide limit if the slides ARE the demo: **≤ 7 slides including title and intro**. English.

1. **Title.** CrewWatch: on-board early warning for crew wearables. Team, Ankara, TEDÜ.
2. **Problem.** Mars light time 3–22 min one way, plus blackouts. NASA's own direction is
   Earth-Independent Medical Operations (EIMO, NTRS refs). Today on ISS, wearable data
   (e.g. Bio-Monitor) is downlinked and analysed on the ground.
3. **The gap.** Per-channel limit checks (cFS Limit Checker style) cannot see a sensor that is frozen
   or silent: every value stays "in range". Board evidence from prior work: 316 samples, 0 alarms.
   Wearable sensor faults → false alarms and wrong conclusions (literature).
4. **Solution.** Packets → features (level, HOLD = "unchanged for N s", AGE = "silent for N s") →
   integer Mahalanobis in a 162-byte int8 table → alert card in plain words. Same C code on the ground
   computer and in the browser; browser (wasm32) vs ground (x86-64): 67 388 / 67 388 scores identical; integer vs float decisions differ on 0.024 % of seconds.
   *(Diagram: wearable → cFS feature code → tinyinfer → alert card)*
5. **Live demo.** Panel: frozen HR on Crew A (limit check quiet, CrewWatch alerts in 10 s);
   silent strap on Crew D (3 s).
6. **Honest results.** The table from `eval/RESULTS.md`, with chance levels. Say it out loud:
   limit check wins on bradycardia; nobody beats chance on slow drift; CrewWatch catches sensor
   faults, with 8× fewer false alarms on new people.
7. **Limits and next step.** Earth data, not astronauts. No SpO₂/respiration channel. Core written
   before the hackathon (disclosed). No board during the hackathon: the engine was board-measured in prior work, CrewWatch itself was
   not run on hardware (`board/RUNBOOK.md`).
   Slow drift needs a better exertion signal and longer-horizon features. Model is updated on the
   ground; only a small table is uplinked.

Background facts for Q&A (from `data/SOURCES.md`): RAD cruise 1.84 mSv/day, surface 0.64 mSv/day;
ISS sleep 6.1 h vs 8.5 h scheduled; bone loss 1–1.5 %/month; board-measured inference 0.64 % of a
1 Hz budget, F = 25 model (prior work, engine only; CrewWatch not run on the board).
