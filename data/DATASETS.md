# DATASETS — candidates checked, what was used

| Dataset | Access | License | Rate | Used? | Why / why not |
|---|---|---|---|---|---|
| **PPG-DaLiA** (UCI #495, doi:10.24432/C53890) | open download, 2.86 GB zip, no login | CC BY 4.0 | chest 700 Hz (ECG, Resp, ACC), wrist ACC 32 Hz, EDA/TEMP 4 Hz, BVP 64 Hz; HR label every 2 s; R-peaks given | **Yes, the only normal data** | Daily activities (stairs, cycling, walking, driving, lunch…) give real activity↔HR coupling; HR ground truth from ECG; R-peaks → RMSSD; skin temp and EDA in the same recording |
| WESAD (UCI #465) | open, ~2 GB | CC BY 4.0 (UCI page) | same sensor pair (RespiBAN + E4) | No (time) | Mostly seated stress/amusement protocol, less activity variety. Good next candidate: would add respiration rate. |
| PhysioNet BIDMC PPG and Respiration | open | ODC-By | 1 Hz numerics: HR, PULSE, RESP, **SpO₂** | No | ICU patients, 8-min records, no activity/temperature. Would be the source for an SpO₂ channel (fault type 5 as written in the roadmap). |
| Board telemetry (Zenodo 22045173) | open | CC BY 4.0 | 1 Hz cFS housekeeping | reference | Same failure class as fault 2 (producer death); not physiological. |

## What `sim/prep_dalia.py` produces (`data/dalia_1hz/S*.csv`, derived, CC BY 4.0, attribution: Reiss et al. 2019)

One row per second after all channels are valid (≥ 60 s of R-peaks for RMSSD):

| Column | Unit | Derivation |
|---|---|---|
| `hr_x10` | 0.1 bpm | DaLiA ECG-derived label (8-s windows, 2-s shift, centred at 2k+4 s), linear interpolation to 1 Hz |
| `rmssd_x10` | 0.1 ms | RMSSD over trailing 60 s of R-R intervals; R-R kept if 300–2000 ms and successive change ≤ 20 % (assumption) |
| `act_mg` | mg | ENMO = max(0, ‖acc‖ − 1 g) from wrist ACC (pickle already in g), mean of trailing 30 s |
| `temp_x100` | 0.01 °C | wrist skin temp, last 4 Hz sample of each second |
| `eda_x1000` | 0.001 µS | wrist EDA, last 4 Hz sample of each second |
| `activity` | id | DaLiA activity label (0 transient, 1 sitting, 2 stairs, 3 table soccer, 4 cycling, 5 driving, 6 lunch, 7 walking, 8 working) |

Split (person-wise, fixed before results, D-09): train S1–S8, validation S9–S11, test/crew S12–S15.

Reproduce: `bash scripts/prep_dalia.sh` (WSL; streams one pickle at a time out of `data/raw/dalia/data.zip`).
