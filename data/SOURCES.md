# SOURCES — every number in the simulator and the panel

Rule 3: each physiological range/rate links to a source or is labelled **assumption**.
"Verified" = the number was checked against the cited abstract/press release on 2026-11-14.
"To confirm" = a secondary source quotes it; the team should open the primary paper before quoting it on a slide.

## Data

| ID | What | Source | License |
|---|---|---|---|
| S-DALIA | PPG-DaLiA: 15 subjects, ~2.5 h each, daily-life activities; chest RespiBAN (ECG/Resp/ACC 700 Hz), wrist E4 (ACC 32 Hz, BVP 64 Hz, EDA 4 Hz, TEMP 4 Hz); HR ground truth from ECG | Reiss, Indlekofer, Schmidt, Van Laerhoven, "Deep PPG: Large-Scale Heart Rate Estimation with Convolutional Neural Networks", *Sensors* 19(14):3079, 2019. Dataset: doi:10.24432/C53890 (UCI #495) | CC BY 4.0 |
| S-DONKI | Solar Energetic Particle events 2024-01-01 … 2026-11-14 (214 events) | NASA CCMC DONKI, `https://ccmc.gsfc.nasa.gov/DONKI-API/get/SEP` — fetched by `sim/fetch_donki.py` | NASA open data |
| S-ZEN | Board telemetry with injected producer death (reference for fault type 2) | Uluağaçlı, cfs-hk-telemetry v1.1.0, doi:10.5281/zenodo.22045173 | CC BY 4.0 |

## Fault parameters

| Parameter | Value used | Source / status |
|---|---|---|
| Fever: HR rise per +1 °C body temperature | 8.5 bpm/°C | Karjalainen & Viitasalo, "Fever and cardiac rhythm", *Arch Intern Med* 146(6):1169-71, 1986 (PMID 2424378). **Verified** (abstract). |
| Fault 4 core-temperature rise | +1.0 °C over 30 min | **assumption** (low-grade fever onset; size chosen so every channel stays inside its own range) |
| Fault 4 skin-temperature rise | +0.5 °C | **assumption** — skin is not core; half the core rise is a conservative guess |
| Fault 4 HRV (RMSSD) drop | −25 % | **assumption** — direction is well documented for infection/stress; magnitude is ours |
| Fault 4 EDA rise | +10 % | **assumption** (sympathetic activation direction; magnitude ours) |
| Fault 5 bradycardia floor | 35 bpm, reached over 60 s | **assumption**: value below every training subject's minimum HR so it *is* a range violation by construction (that is the point of the control case) |
| Fault 1/2 duration | 300 s | **assumption** |
| Fault 3 (loose electrode): HR output | frozen-ish: last good value + its own small jitter (±0.5 bpm) while real activity rises | **assumption** about electrode failure mode; mechanism (motion artefact/contact loss) is well known |

## Self check-in thresholds (`features/crewwatch_checkin.c`)

| What | Threshold | Source / status |
|---|---|---|
| Blood pressure categories | normal < 120/< 80; elevated 120–129/< 80; stage 1 130–139 or 80–89; stage 2 ≥ 140 or ≥ 90; crisis > 180 and/or > 120; higher category wins | Whelton et al., 2017 ACC/AHA Hypertension Guideline, *Hypertension* 71:e13 (doi:10.1161/HYP.0000000000000065); AHA "Top things to know". **Verified** (AHA summary). Crisis advice "rest 5 min, measure again" is AHA patient guidance: **to confirm wording** |
| Fever | oral ≥ 38.0 °C (100.4 °F) | CDC definition, quoted by Cleveland Clinic / Penn Medicine pages. **Verified** (secondary) |
| Low blood glucose | level 1 < 70 mg/dL, level 2 < 54 mg/dL; treat with 15 g fast-acting carbohydrate, re-check after 15 min | ADA Standards of Care, Section 6 (Glycemic goals and hypoglycemia). Thresholds **verified** (secondary summaries); "15 g / 15 min" rule **to confirm wording** |
| Sleep | adults ≥ 7 h per night | Watson et al., AASM/SRS consensus, *Sleep* 38:843, 2015. **Verified** |
| Low mood | ≤ 2 on a 1–5 self rating; 3 in a row → suggest a private talk | **assumption** (no validated cut-off for a 1-item scale; the tool only reports streaks) |
| Pulse vs wearable agreement | within 10 bpm or 10 % of the hand count | **assumption** (a 15-s count × 4 is quantised to 4 bpm) |
| Demo hand count | round(true HR / 4) beats in 15 s, from the original PPG-DaLiA HR before the fault was injected | derived from data, no invented number |

## Panel numbers (context, not model inputs)

| What | Value | Source / status |
|---|---|---|
| Earth–Mars one-way light time | ~3 to ~22 min (average ~12.5 min; up to ~44 min round trip) | Orbital geometry: 54.6 M km → 3.0 min, ~400 M km → 22.3 min. NASA-affiliated review NTRS 20250000703 quotes up to 44-min round trip. **Verified** (geometry; the panel's 3/12.5/22 min options use these). |
| Earth–Moon one-way light time | ~1.3 s | 384 400 km / c. Physics. |
| Cruise dose equivalent (MSL/RAD, Earth→Mars) | 1.84 mSv/day | Zeitlin et al., *Science* 340:1080, 2013. **Verified** (press coverage of the paper) |
| Mars surface dose equivalent (RAD, Gale crater) | 0.64 mSv/day | Hassler et al., *Science* 343:1244797, 2014. **Verified** (press coverage) |
| Bone loss | 1–1.5 %/month areal BMD (Mir DXA, review); ISS hip (QCT, 14 crew, 4–6 months): integral vBMD 1.2–1.5 %/month, trabecular 2.2–2.7 %/month, areal 1.4–1.5 %/month | Review: *Curr Osteoporos Rep* 2013, doi:10.1007/s11914-013-0136-5. Lang et al., "Cortical and trabecular bone mineral loss from the spine and hip in long-duration spaceflight", *J Bone Miner Res* 19(6):1006–12, 2004 (PMID 15125798). **Verified** (abstract). The panel band 1–1.5 %/month matches both. |
| In-flight sleep | 6.09 h/night ISS, 5.96 h shuttle (8.5 h scheduled) | Barger et al., *Lancet Neurol* 13:904, 2014, doi:10.1016/S1474-4422(14)70122-X. **Verified** (press release) |
| Activity metric | ENMO = max(0, ‖acc‖ − 1 g), 30-s epoch mean | van Hees et al., "Separating movement and gravity components in an acceleration signal…", *PLoS ONE* 8(4):e61691, 2013, doi:10.1371/journal.pone.0061691. **Verified** (ENMO definition). The 30-s epoch is our choice (assumption). |

## Positioning (slides)

| Claim | Source |
|---|---|
| Earth-Independent Medical Operations (EIMO) | NASA HRP ExMC, "Earth-Independent Medical Operations (EIMO) Concept of Operations", Feb 2024, NTRS 20240001402 (650–900+ day Mars mission, no real-time comms in blackouts, no evacuation); 2025 revision NTRS 20250000009 (gradual move of medical decision-making from Earth to the spacecraft). **Verified** (NTRS records). |
| Wearable sensor faults cause false alarms | Zhang, Liu, Kato, "Threshold Tuning-Based Wearable Sensor Fault Detection for Reliable Medical Monitoring Using Bayesian Network Model", *IEEE Systems Journal* 12(2):1886–1896, 2018. **Verified** (bibliographic record; check IEEE Xplore before quoting). |
