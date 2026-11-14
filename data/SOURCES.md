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

## Panel numbers (context, not model inputs)

| What | Value | Source / status |
|---|---|---|
| Earth–Mars one-way light time | ~3 to ~22 min | Standard orbital geometry (closest ~55 M km, farthest ~400 M km); NASA Mars missions pages. **To confirm** exact figure used on the slide |
| Earth–Moon one-way light time | ~1.3 s | 384 400 km / c. Physics. |
| Cruise dose equivalent (MSL/RAD, Earth→Mars) | 1.84 mSv/day | Zeitlin et al., *Science* 340:1080, 2013. **Verified** (press coverage of the paper) |
| Mars surface dose equivalent (RAD, Gale crater) | 0.64 mSv/day | Hassler et al., *Science* 343:1244797, 2014. **Verified** (press coverage) |
| Bone loss (areal BMD) | 1–1.5 %/month (Mir DXA); ISS hip QCT 1.6–2.7 %/month | Review in *Curr Osteoporos Rep* 2013 (doi:10.1007/s11914-013-0136-5); Lang et al. *JBMR* 2004 (UCSF/Baylor). **To confirm** primary values |
| In-flight sleep | 6.09 h/night ISS, 5.96 h shuttle (8.5 h scheduled) | Barger et al., *Lancet Neurol* 13:904, 2014, doi:10.1016/S1474-4422(14)70122-X. **Verified** (press release) |
| Activity metric | ENMO = max(0, ‖acc‖ − 1 g), 30-s epoch mean | van Hees et al., *PLoS ONE* 8(4):e61691, 2013. **To confirm** |

## Positioning (slides)

| Claim | Source |
|---|---|
| Earth-Independent Medical Operations (EIMO) | NTRS 20250000009, NTRS 20240001402 (from roadmap §4.1 — **to confirm** titles) |
| Wearable sensor faults cause false alarms | IEEE Systems Journal 2018, Bayesian-network approach (roadmap §4.1 — **to confirm** citation) |
