## Reading this table honestly

*(Written after looking at the numbers, with AI assistance; see `AI_USE.md`.)*

**What our plan expected:** types 1–2 caught by the simple rule too, types 3–4 caught only by the
joint model, type 5 fastest with the range check.

**What we measured:**

1. **Types 1–2 (sensor frozen / strap silent):** CrewWatch and the simple "range + HOLD" rule both catch
   **100 %**. The simple rule is as good as CrewWatch here (latency 9 s vs 10 s for frozen HR). For
   silence CrewWatch is faster (3 s vs 8 s) because the AGE feature reacts before any value has been
   unchanged for 9 ticks. The plain range check is at its chance level: blind to both, as on the board
   (316 samples, 0 alarms).
2. **Type 5 (bradycardia, real range violation):** the range check wins clearly (77 % vs 32 %).
   Expected: a single channel leaving its range is exactly what a limit check is for. Earlier we saw
   CrewWatch at 100 % here, but that came from an artefact (the injected plateau was a constant value,
   so HOLD fired). With realistic jitter on the plateau, that advantage went away.
3. **Types 3–4 (HR not following activity, slow fever-like drift):** **no detector does better than
   chance**, CrewWatch included. The fever-like drift sweep stays flat for CrewWatch from 0.5 to 3 °C.
   Our main hypothesis is **not supported** by this data at 1 Hz. Likely reasons: (a) a wrist
   accelerometer is a weak proxy for exertion (cycling barely moves the wrist while HR is high), so the
   HR↔activity coupling the model would need is weak in the training data; (b) a +8.5 bpm shift is small
   next to the ±50 bpm swings that normal daily activity causes.
4. **False alarms on new people:** with every threshold matched to 0.1 % on validation, on the 4 test
   people CrewWatch alarms on **0.35 %** of ticks (12.5 alarm-seconds/h) and the personal range check on
   **2.9 %** (104/h). One test person's skin temperature and conductance sat outside the range seen in
   training. CrewWatch's per-person feature table absorbs that kind of level shift better. Neither
   detector holds its validation budget exactly, so both rates are worse than tuned.
5. **Integer = float:** decisions differ on 7 of 28 894 clean ticks (0.024 %). The int8 table is not the
   source of the misses.

**What this means for the pitch:** the two layers *do* complement each other, but not in the way the
plan guessed. Limit checks handle clear range violations. CrewWatch handles **sensor-health faults**
(frozen or silent wearables, which limit checks cannot see) with a deterministic integer model that
raised fewer false alarms on new people. **Slow physiological drift is not solved by a 1 Hz per-tick
model with these sensors.** We say so, and list it as the next problem (better exertion signal,
e.g. chest-ACC or respiration; longer-horizon features).

**How we got here (iteration log, for transparency):**
- v1: vendor DIFF features → feature means off by 15 000 LSB. Root cause: DIFF has counter semantics
  (D-13). Removed.
- v2: activity/temp/EDA HOLD → natural multi-minute holds dominated validation (D-15). Removed.
- v3: packet-loss spikes in HOLD/AGE set the threshold (all top-0.1 % validation ticks). Rescaled the
  counters and raised the ridge, choosing settings from **validation** diagnostics only (D-17).
- v4: event metric was contaminated by false alarms in long windows → added chance levels; brady
  plateau got jitter (it had been tripping HOLD); range limits made personal so the comparison with
  CrewWatch's personal tables is fair (D-18).
- v5: added the SLOW instance (flight 64-tick window mean) **after** seeing the type 3–5 test results.
  It gave no detection gain (disclosed; it lowered test false alarms from 0.42 % to 0.35 %).
  After v5 the model was frozen. No further changes were made while looking at test numbers.
