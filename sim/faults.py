"""
Fault / condition injector. Works ON TOP OF REAL RECORDINGS (team decision
decision): normal behaviour is never generated, only the fault is.

Every parameter is listed in data/SOURCES.md with a source or 'assumption'.

Types
  1 frozen      HR stuck at its value at onset, packets keep arriving
  2 silence     chest-strap packets stop (HR + HRV latched at last value)
  3 decoupled   activity rises (real), HR stays near onset value (loose electrode)
  4 drift       slow joint shift: HR +8.5 bpm, skin temp +0.5 degC, RMSSD -25 %,
                EDA +10 %, 30 min ramp + 30 min plateau, each channel stays in range
  5 brady       HR ramps to 35 bpm in 60 s and stays (control: range check should win)
Written with AI assistance (Claude Code), see AI_USE.md.
"""
import random

import crew as C

TYPES = {
    1: ("frozen", "HR sensor frozen", 300),
    2: ("silence", "chest strap silent", 300),
    3: ("decoupled", "HR not following activity", 300),
    4: ("drift", "slow joint drift (fever-like)", 3600),
    5: ("brady", "HR below range (bradycardia)", 300),
}

FEVER_DEGC = 1.0             # assumption
HR_PER_DEGC_X10 = 85         # 8.5 bpm/degC, Karjalainen & Viitasalo 1986
SKIN_RISE_X100 = 50          # assumption
RMSSD_FACTOR = 0.75          # assumption
EDA_FACTOR = 1.10            # assumption
BRADY_X10 = 350              # assumption: below every training minimum (checked in eval)
JITTER_X10 = 5.0             # assumption: 0.5 bpm AR(1) jitter on a decoupled HR
VIGOROUS = (2, 3, 4, 7)      # DaLiA activities: stairs, table soccer, cycling, walking


def inject(rec, ftype, onset, seed=0, fever_degc=None):
    """-> (modified record copy, suppress dict, label list[0/ftype])"""
    r = C.copy_rec(rec)
    n = len(r["t"])
    dur = TYPES[ftype][2]
    end = min(n, onset + dur)
    label = [0] * n
    for i in range(onset, end):
        label[i] = ftype
    suppress = {}
    hr = r["hr_x10"]

    if ftype == 1:
        v = hr[onset]
        for i in range(onset, end):
            hr[i] = v
    elif ftype == 2:
        suppress[0] = set(range(onset, end))
    elif ftype == 3:
        rnd = random.Random(seed * 7919 + onset)
        base = hr[onset]
        x = 0.0
        a = 0.9
        e = JITTER_X10 * (1 - a * a) ** 0.5
        for i in range(onset, end):
            x = a * x + rnd.gauss(0.0, e)
            hr[i] = int(round(base + x))
    elif ftype == 4:
        deg = FEVER_DEGC if fever_degc is None else fever_degc
        ramp = 1800
        for i in range(onset, end):
            f = min(1.0, (i - onset) / float(ramp))
            hr[i] = int(round(hr[i] + f * HR_PER_DEGC_X10 * deg))
            r["temp_x100"][i] = int(round(r["temp_x100"][i] + f * SKIN_RISE_X100 * deg))
            r["rmssd_x10"][i] = int(round(r["rmssd_x10"][i] * (1 - f * min(0.9, (1 - RMSSD_FACTOR) * deg))))
            r["eda_x1000"][i] = int(round(r["eda_x1000"][i] * (1 + f * (EDA_FACTOR - 1) * deg)))
    elif ftype == 5:
        # same AR(1) jitter as type 3, so the plateau is not a constant value
        # (a constant would trip the HOLD rule for the wrong reason)
        rnd = random.Random(seed * 7919 + onset + 5)
        v0 = hr[onset]
        x = 0.0
        a = 0.9
        e = JITTER_X10 * (1 - a * a) ** 0.5
        for i in range(onset, end):
            f = min(1.0, (i - onset) / 60.0)
            x = a * x + rnd.gauss(0.0, e)
            hr[i] = int(round(v0 + f * (BRADY_X10 - v0) + x))
    else:
        raise ValueError(ftype)
    return r, suppress, label


def onsets(rec, ftype, k, seed=0, pre=300, post=120):
    """Pick up to k non-overlapping onsets after the personal baseline window."""
    n = len(rec["t"])
    dur = TYPES[ftype][2]
    lo = C.BASELINE_S + pre
    hi = n - dur - post
    if hi <= lo:
        return []
    rnd = random.Random(seed * 31 + ftype * 1000 + rec["subject"])
    if ftype == 3:
        # real activity rises: 30-s activity goes from < 100 mg to >= +80 mg
        # within 60 s (the label switch alone gave only ~2 events/person).
        # Candidates at least 300 s apart.
        act = rec["act_mg"]
        cand = []
        for i in range(lo, min(hi, n - 60)):
            if act[i] < 100 and act[i + 60] - act[i] >= 80 and (not cand or i - cand[-1] >= 300):
                cand.append(i)
        rnd.shuffle(cand)
        return sorted(cand[:k])
    # Each event is replayed on its OWN copy of the record, so onsets may
    # share background; they only need to be distinct (>= 120 s apart).
    out = []
    tries = 0
    while len(out) < k and tries < 10000:
        tries += 1
        c = rnd.randint(lo, hi)
        if all(abs(c - o) >= 120 for o in out):
            out.append(c)
    return sorted(out)
