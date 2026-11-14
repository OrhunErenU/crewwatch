#!/usr/bin/env python3
"""
PPG-DaLiA -> 1 Hz integer channels, the way a wearable would transmit them.

This is the "sensor side". It runs once, offline, with numpy. It produces NO
model features and NO scores -- those come from the flight C code later.

Per second t (1 Hz grid, t = 0 is recording start):

  src 0 (chest strap)
    hr_x10     HR in 0.1 bpm. DaLiA label = ECG-derived HR on 8-s windows
               shifted by 2 s; window k is centred at 2k+4 s; linear
               interpolation to the 1 Hz grid.
    rmssd_x10  RMSSD in 0.1 ms over the trailing 60 s of R-R intervals
               (DaLiA ships R-peak indices at 700 Hz). R-R kept if 300..2000 ms
               and |dRR| <= 20 % of previous (simple artefact rule, assumption).
  src 1 (wrist)
    act_mg     ENMO = max(0, |acc| - 1 g) in milli-g, mean of trailing 30 s
               (pickle ACC is in g).
    temp_x100  skin temperature in 0.01 degC: LAST 4 Hz sample of the second
               (latch semantics -- keeps the sensor's real resolution, so a
               naturally steady value really repeats).
    eda_x1000  EDA in 0.001 uS, last 4 Hz sample of the second.
  label
    activity   DaLiA activity id (last 4 Hz sample of the second)

    python3 sim/prep_dalia.py --raw data/raw/dalia/PPG_FieldStudy --out data/dalia_1hz
Written with AI assistance (Claude Code), see AI_USE.md.
"""
import argparse
import csv
import os
import pickle
import sys

import numpy as np

CHEST_FS = 700
ACC_FS = 32
SLOW_FS = 4

ACTIVITY = {0: "transient", 1: "sitting", 2: "stairs", 3: "table soccer", 4: "cycling",
            5: "driving", 6: "lunch", 7: "walking", 8: "working"}

COLS = ["t", "hr_x10", "rmssd_x10", "act_mg", "temp_x100", "eda_x1000", "activity"]


def rmssd_series(rpeaks, n_sec, win=60):
    rp = np.asarray(rpeaks, dtype=np.int64)
    t_peak = rp / float(CHEST_FS)
    rr = np.diff(t_peak) * 1000.0           # ms, timestamp = second peak
    t_rr = t_peak[1:]
    ok = (rr >= 300) & (rr <= 2000)
    ok[1:] &= np.abs(np.diff(rr)) <= 0.2 * rr[:-1]
    out = np.full(n_sec, np.nan)
    for t in range(win, n_sec):
        m = (t_rr > t - win) & (t_rr <= t)
        r = rr[m]
        g = ok[m]
        # successive differences only between two consecutive GOOD intervals
        d = np.diff(r)[(g[1:] & g[:-1])]
        if len(d) >= 10:
            out[t] = np.sqrt(np.mean(d * d))
    return out


def last_per_second(x, fs, n_sec):
    idx = np.arange(1, n_sec + 1) * fs - 1
    idx = np.clip(idx, 0, len(x) - 1)
    return np.asarray(x)[idx]


def process(path):
    with open(path, "rb") as f:
        d = pickle.load(f, encoding="latin1")
    wrist = d["signal"]["wrist"]
    n_sec = int(len(wrist["TEMP"]) // SLOW_FS)

    label = np.asarray(d["label"], dtype=float)
    centers = 2.0 * np.arange(len(label)) + 4.0
    t = np.arange(n_sec, dtype=float)
    hr = np.interp(t, centers, label, left=np.nan, right=np.nan)

    rmssd = rmssd_series(d["rpeaks"], n_sec)

    acc = np.asarray(wrist["ACC"], dtype=float)  # already in g in the pickle (checked: median norm 1.013)
    enmo = np.maximum(0.0, np.sqrt((acc * acc).sum(axis=1)) - 1.0) * 1000.0
    n_acc_sec = len(enmo) // ACC_FS
    per_sec = enmo[: n_acc_sec * ACC_FS].reshape(n_acc_sec, ACC_FS).mean(axis=1)
    act = np.full(n_sec, np.nan)
    c = np.cumsum(np.concatenate([[0.0], per_sec]))
    for s in range(30, min(n_sec, n_acc_sec) + 1):
        act[s - 1] = (c[s] - c[s - 30]) / 30.0

    temp = last_per_second(np.asarray(wrist["TEMP"]).ravel(), SLOW_FS, n_sec)
    eda = last_per_second(np.asarray(wrist["EDA"]).ravel(), SLOW_FS, n_sec)
    actv = last_per_second(np.asarray(d["activity"]).ravel(), SLOW_FS, n_sec)

    rows = []
    for s in range(n_sec):
        v = (hr[s], rmssd[s], act[s])
        if any(np.isnan(x) for x in v):
            continue
        rows.append([s, int(round(hr[s] * 10)), int(round(rmssd[s] * 10)), int(round(act[s])),
                     int(round(float(temp[s]) * 100)), int(round(float(eda[s]) * 1000)), int(actv[s])])
    return rows, d.get("subject", os.path.basename(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", help="folder holding S1/S1.pkl ... S15/S15.pkl")
    ap.add_argument("--pkl", help="one pickle (use with --subject); lets a script unzip one at a time")
    ap.add_argument("--subject", type=int)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    todo = [(a.subject, a.pkl)] if a.pkl else \
        [(k, os.path.join(a.raw, "S%d" % k, "S%d.pkl" % k)) for k in range(1, 16)]
    for k, p in todo:
        if not os.path.exists(p):
            print("missing %s" % p, file=sys.stderr)
            continue
        rows, subj = process(p)
        out = os.path.join(a.out, "S%d.csv" % k)
        with open(out, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            w.writerows(rows)
        hr = np.array([r[1] for r in rows]) / 10.0
        rm = np.array([r[2] for r in rows]) / 10.0
        print("S%-2d %5d s  HR %5.1f..%5.1f  RMSSD %5.1f..%6.1f  act %4d..%4d  temp %.2f..%.2f" % (
            k, len(rows), hr.min(), hr.max(), rm.min(), rm.max(),
            min(r[3] for r in rows), max(r[3] for r in rows),
            min(r[4] for r in rows) / 100, max(r[4] for r in rows) / 100))
    return 0


if __name__ == "__main__":
    sys.exit(main())
