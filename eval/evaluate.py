#!/usr/bin/env python3
"""
Honest comparison, three detectors on the SAME replayed telemetry:

  (a) RANGE      per-channel [lo, hi] on the last received value (cFS Limit
                 Checker style), PERSONAL like CrewWatch's feature table:
                 limit = person's baseline + [min, max] of (value - baseline)
                 over train, widened by k*(max-min); k tuned on validation
                 to the matched false-alarm budget (D-18).
  (b) RANGE+HOLD (a) OR "value unchanged for >= N_c ticks" per channel.
                 N_c = 1 + largest HOLD seen on train+val normal data.
  (c) CREWWATCH  integer Mahalanobis scores from the flight C code: FAST model
                 on the 1 Hz vector OR SLOW model on the flight 64-tick window
                 mean; each threshold at half the budget on validation.

Faults are injected into the 4 test subjects (the crew) only.

    python3 eval/evaluate.py [--k-events 12]      (WSL)
Outputs eval/results.json, eval/RESULTS.md, eval/*.svg
Written with AI assistance (Claude Code), see AI_USE.md.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "sim"))
import crew as C  # noqa: E402
import faults as FT  # noqa: E402
import bridge as B  # noqa: E402
sys.path.insert(0, B.GROUND)
import quantize as Q  # noqa: E402
import tinyinfer_ctypes as TI  # noqa: E402

PRE = 300
POST = 120
GRACE = 60


def load_model():
    with open(os.path.join(ROOT, "model", "model.json")) as f:
        m = json.load(f)
    ti = TI.TinyInfer()
    qm = (Q.model_to_tinyinfer(m["fast"]["quant"], ti=ti), Q.model_to_tinyinfer(m["slow"]["quant"], ti=ti))
    return m, qm


def defs_for(m, k):
    t = m["tables"][str(k)]
    return C.feature_defs(t["bias"], t["scale"], t["shift"])


class Detectors(object):
    def __init__(self, m, qm, limits, hold_n):
        self.m, self.qm = m, qm
        self.dlimits = limits          # deltas from personal baseline
        self.limits = limits
        self.hold_n = hold_n
        self.thr = (m["fast"]["threshold_int"], m["slow"]["threshold_int"])

    def set_subject(self, k):
        b = self.m["tables"][str(k)]["baseline"]
        self.limits = [(lo + b[C.CHANNELS[i][0]], hi + b[C.CHANNELS[i][0]])
                       for i, (lo, hi) in enumerate(self.dlimits)]
        return self

    def step(self, tk):
        rng = False
        for ci, v in enumerate(tk.latched):
            if v is None:
                continue
            lo, hi = self.limits[ci]
            if v < lo or v > hi:
                rng = True
                break
        hold = any(tk.hold.get(ch, 0) >= n for ch, n in self.hold_n.items())
        # ratio = max over the two models of score / own threshold (> 1 = alarm)
        best = (None, None, None, None, None)      # ratio, contrib, which, raw, thr
        for which, x in ((0, tk.vec), (1, tk.wmean)):
            if x is None:
                continue
            sc, contrib, _ = self.qm[which].score(x)
            r = sc / float(self.thr[which])
            if best[0] is None or r > best[0]:
                best = (r, contrib, which, sc, self.thr[which])
        self.last = best
        cw = best[0] is not None and best[0] > 1.0
        return rng, rng or hold, cw, best[0], best[1]


def run(rec, defs, det, start, stop, suppress=None, seed=0):
    det.set_subject(rec["subject"])
    out = []
    for tk in C.replay(rec, defs, suppress=suppress, start=start, stop=stop, seed=seed):
        a, b, c, score, contrib = det.step(tk)
        out.append((tk, a, b, c, score, contrib))
    return out


def tune_limits(m, qm, recs):
    """Train min/max, then k on validation to the matched budget."""
    budget = m["fa_budget"]
    lo = [10 ** 9] * len(C.CHANNELS)
    hi = [-10 ** 9] * len(C.CHANNELS)
    hold_max = {ch: 0 for ch, xf in C.FEATURES if xf == B.XFORM_HOLD}
    def base(k):
        b = m["tables"][str(k)]["baseline"]
        return [b[c[0]] for c in C.CHANNELS]

    for k in C.SPLIT["train"]:
        bk = base(k)
        for tk in C.replay(recs[k], defs_for(m, k)):
            for ci, v in enumerate(tk.latched):
                if v is not None:
                    v = v - bk[ci]
                    lo[ci] = min(lo[ci], v)
                    hi[ci] = max(hi[ci], v)
            for ch in hold_max:
                hold_max[ch] = max(hold_max[ch], tk.hold.get(ch, 0))
    val_lat = []
    for k in C.SPLIT["val"]:
        for tk in C.replay(recs[k], defs_for(m, k), start=0):
            for ch in hold_max:
                hold_max[ch] = max(hold_max[ch], tk.hold.get(ch, 0))
            if tk.t >= C.BASELINE_S:
                bk = base(k)
                val_lat.append([None if v is None else v - bk[i] for i, v in enumerate(tk.latched)])

    def fa(kk):
        L = [(lo[i] - kk * (hi[i] - lo[i]), hi[i] + kk * (hi[i] - lo[i])) for i in range(len(lo))]
        bad = 0
        for lat in val_lat:
            if any(v is not None and (v < L[i][0] or v > L[i][1]) for i, v in enumerate(lat)):
                bad += 1
        return bad / float(len(val_lat)), L

    best = None
    for step in range(-30, 201):          # k from -0.30 to 2.00
        kk = step / 100.0
        r, L = fa(kk)
        if r <= budget:
            best = (kk, r, L)
            break
    if best is None:
        kk = 2.0
        r, L = fa(kk)
        best = (kk, r, L)
    hold_n = {ch: v + 1 for ch, v in hold_max.items()}
    return {"train_lo": lo, "train_hi": hi, "k": best[0], "val_fa": best[1],
            "limits": best[2], "hold_n": hold_n}


def fs_dec(mod, x):
    """float-model decision on the same int16 vector (for int-vs-float agreement)"""
    Ms = mod["Ms"]
    F = len(Ms)
    fs = sum(sum(Ms[i][j] * x[j] for j in range(F)) ** 2 for i in range(F))
    return fs > mod["threshold_float"]


def chance(clean_series, win):
    """P(at least one alarm in a fault-free window of `win` ticks), per method.
    A detection rate is only meaningful above this level."""
    out = {}
    for mi, meth in enumerate(("range", "range_hold", "crewwatch")):
        hit = tot = 0
        for ser in clean_series:
            for s0 in range(0, max(0, len(ser) - win), 30):
                tot += 1
                hit += any(ser[t][mi] for t in range(s0, s0 + win))
        out[meth] = hit / float(tot) if tot else float("nan")
    return out


def summarise(events):
    res = {}
    for meth in ("range", "range_hold", "crewwatch"):
        det = [e for e in events if e[meth]["detected"]]
        lat = sorted(e[meth]["latency"] for e in det)
        res[meth] = {"n": len(events), "detected": len(det),
                     "rate": len(det) / float(len(events)) if events else float("nan"),
                     "median_latency_s": lat[len(lat) // 2] if lat else None}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k-events", type=int, default=12, help="onsets per subject per fault type")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()

    m, qm = load_model()
    recs = {k: C.load(k) for k in C.SPLIT["train"] + C.SPLIT["val"] + C.SPLIT["test"]}
    tl = tune_limits(m, qm, recs)
    det = Detectors(m, qm, tl["limits"], tl["hold_n"])
    print("range k = %.2f (val FA %.3f %%), HOLD N = %s" % (tl["k"], 100 * tl["val_fa"], tl["hold_n"]))

    # ---- clean test data: realised false-alarm rates + int/float agreement
    clean = {"range": 0, "range_hold": 0, "crewwatch": 0, "ticks": 0, "disagree": 0}
    clean_series = []          # per subject: list of (range, range_hold, crewwatch) per scored tick
    F = len(m["Ms"])
    for k in C.SPLIT["test"]:
        ser = []
        clean_series.append(ser)
        for tk, ra, rb, rc, score, _ in run(recs[k], defs_for(m, k), det, 0, None):
            if tk.t < C.BASELINE_S or tk.vec is None:
                continue
            ser.append((ra, rb, rc))
            clean["ticks"] += 1
            clean["range"] += ra
            clean["range_hold"] += rb
            clean["crewwatch"] += rc
            dec_f = fs_dec(m["fast"], tk.vec)
            dec_s = fs_dec(m["slow"], tk.wmean) if tk.wmean is not None else False
            clean["disagree"] += (dec_f or dec_s) != rc
    fa = {meth: clean[meth] / float(clean["ticks"]) for meth in ("range", "range_hold", "crewwatch")}
    print("clean test ticks %d, FA %s, int/float disagreement %.3f %%" % (
        clean["ticks"], {k: "%.3f%%" % (100 * v) for k, v in fa.items()},
        100.0 * clean["disagree"] / clean["ticks"]))

    # ---- faults
    events = []
    contrib_acc = {}
    chance_by_type = {}
    for ftype in sorted(FT.TYPES):
        name, desc, dur = FT.TYPES[ftype]
        kk = a.k_events
        for k in C.SPLIT["test"]:
            for onset in FT.onsets(recs[k], ftype, kk, seed=a.seed):
                r2, sup, label = FT.inject(recs[k], ftype, onset, seed=a.seed)
                start = onset - PRE
                stop = onset + dur + POST
                rows = run(r2, defs_for(m, k), det, start, stop, suppress=sup, seed=a.seed + onset)
                ev = {"type": ftype, "subject": k, "onset": onset}
                for meth, col in (("range", 1), ("range_hold", 2), ("crewwatch", 3)):
                    hits = [r[0].t for r in rows if r[col] and onset <= r[0].t < onset + dur + GRACE]
                    pre_fa = sum(1 for r in rows if r[col] and r[0].t < onset)
                    ev[meth] = {"detected": bool(hits), "latency": (hits[0] - onset) if hits else None,
                                "pre_fa": pre_fa}
                # top contributor at first CrewWatch alarm (for explain/ sanity)
                first = next((r for r in rows if r[3] and r[0].t >= onset), None)
                if first:
                    top = max(range(F), key=lambda i: first[5][i])
                    contrib_acc.setdefault(ftype, {}).setdefault(m["features"][top]["name"], 0)
                    contrib_acc[ftype][m["features"][top]["name"]] += 1
                events.append(ev)
        s = summarise([e for e in events if e["type"] == ftype])
        ch = chance(clean_series, dur + GRACE)
        chance_by_type[ftype] = ch
        print("type %d %-34s n=%3d  range %5.1f%% (chance %4.1f)  range+hold %5.1f%% (%4.1f)  crewwatch %5.1f%% (%4.1f)" % (
            ftype, desc, s["range"]["n"], 100 * s["range"]["rate"], 100 * ch["range"],
            100 * s["range_hold"]["rate"], 100 * ch["range_hold"], 100 * s["crewwatch"]["rate"], 100 * ch["crewwatch"]))

    # ---- drift size sweep (type 4). 1.0 degC is the sourced case; the others
    #      are a labelled sensitivity sweep, not claims about real fevers.
    sweep = {}
    for deg in (0.5, 1.0, 2.0, 3.0):
        evs = []
        for k in C.SPLIT["test"]:
            for onset in FT.onsets(recs[k], 4, max(4, a.k_events // 2), seed=a.seed + 17):
                r2, sup, _ = FT.inject(recs[k], 4, onset, seed=a.seed, fever_degc=deg)
                rows = run(r2, defs_for(m, k), det, onset - PRE, onset + FT.TYPES[4][2] + POST, suppress=sup,
                           seed=a.seed + onset)
                ev = {}
                for meth, col in (("range", 1), ("range_hold", 2), ("crewwatch", 3)):
                    hits = [r[0].t for r in rows if r[col] and onset <= r[0].t < onset + FT.TYPES[4][2] + GRACE]
                    ev[meth] = {"detected": bool(hits), "latency": (hits[0] - onset) if hits else None}
                evs.append(ev)
        sweep[str(deg)] = summarise(evs)
        print("drift %.1f degC  n=%d  range %5.1f%%  range+hold %5.1f%%  crewwatch %5.1f%%" % (
            deg, len(evs), 100 * sweep[str(deg)]["range"]["rate"], 100 * sweep[str(deg)]["range_hold"]["rate"],
            100 * sweep[str(deg)]["crewwatch"]["rate"]))

    res = {"limits": tl, "clean": clean, "fa": fa, "events": events, "drift_sweep": sweep,
           "by_type": {t: summarise([e for e in events if e["type"] == t]) for t in FT.TYPES},
           "chance_by_type": chance_by_type,
           "chance_drift": chance(clean_series, FT.TYPES[4][2] + GRACE),
           "top_contributor_at_first_alarm": contrib_acc,
           "model": {"F": F, "weight_bytes": m["weight_bytes"], "threshold_int": m["threshold_int"],
                     "threshold_slow_int": m["slow"]["threshold_int"], "window_len": m["window_len"],
                     "fa_budget": m["fa_budget"], "val_int_float_agreement": m["val_int_float_agreement"]}}
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("wrote eval/results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
