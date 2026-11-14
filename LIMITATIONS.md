# LIMITATIONS — say these before the jury does

1. **No astronaut data.** Normal behaviour comes from PPG-DaLiA: 15 people on
   Earth, ~2.5 h each, daily activities. Microgravity changes resting HR, fluid
   distribution and HRV; we discuss this in text only and do **not** shift the
   data to "make it spacey".
2. **Faults are injected, not observed.** Each fault type is a model of a
   failure (frozen sensor, silent strap, loose electrode, slow joint drift,
   bradycardia). Results mean "detected the same injected fault type again",
   not "proven in flight".
3. **Missing channels.** No SpO₂, no respiration rate, no sleep stage in the
   data we used. Fault type 5 uses HR instead of SpO₂ (DECISIONS D-08). The
   sleep and bone panels show published reference values, not crew data.
4. **Radiation panel** shows real NASA DONKI SEP event times and a constant
   GCR dose rate (MSL/RAD cruise). It does not model SEP dose.
5. **Packet loss** (1 % i.i.d.) is an assumption, added so the model does not
   learn "packets never drop".
6. **Small crew test set** (4 test subjects, 3 validation, 8 training). Rates
   have wide confidence intervals; event counts are shown next to percentages.
7. **No medical expert on the team.** Alert text is "check the sensor / note
   how you feel", never a diagnosis.
8. **Board run not repeated for CrewWatch.** What was measured on the
   SmartFusion2 board (bit-exact 11/11, 0.64 % of a 1 Hz budget, F=25 model)
   applies because CrewWatch keeps the same model shape (F ≤ 25, two matvecs
   + SqErr, int8 weights, int16 activations). **Not shown on the board:**
   loading the CrewWatch tables, HOLD running on the board, wearable data
   entering flight software. Next step: board run (`board/RUNBOOK.md`).
9. **The core is pre-existing work** (see `PRIOR_WORK.md`).
10. **Model updates happen on the ground**; only the small table is uplinked.
    There is no training in orbit.
