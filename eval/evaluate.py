#!/usr/bin/env python3
"""
Honest comparison, three detectors on the SAME replayed telemetry:

  (a) RANGE      per-channel [lo, hi] on the last received value (cFS Limit
                 Checker style). lo/hi = train min/max widened by k*(max-min);
                 k tuned on validation to the matched false-alarm budget.
  (b) RANGE+HOLD (a) OR "value unchanged for >= N_c ticks" per channel.
                 N_c = 1 + largest HOLD seen on train+val normal data.
  (c) CREWWATCH  integer Mahalanobis score from the flight C code > threshold
                 (threshold chosen on validation at the same budget).

Faults are injected into the 4 test subjects (the crew) only.

    python3 eval/evaluate.py [--k-events 12]      (WSL)
Outputs eval/results.json, eval/RESULTS.md, eval/*.svg
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
    qm = Q.model_to_tinyinfer(m["quant"], ti=ti)
    return m, qm


def defs_for(m, k):
    t = m["tables"][str(k)]
    return C.feature_defs(t["bias"], t["scale"], t["shift"])


class Detectors(object):
    def __init__(self, m, qm, limits, hold_n):
        self.m, self.qm = m, qm
        self.limits = limits
        self.hold_n = hold_n
        self.thr = m["threshold_int"]

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
        if tk.vec is None:
            score, contrib, cw = None, None, False
        else:
            score, contrib, _ = self.qm.score(tk.vec)
            cw = score > self.thr
        return rng, rng or hold, cw, score, contrib


def run(rec, defs, det, start, stop, suppress=None, seed=0):
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
    for k in C.SPLIT["train"]:
        for tk in C.replay(recs[k], defs_for(m, k)):
            for ci, v in enumerate(tk.latched):
                if v is not None:
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
                val_lat.append(tk.latched)

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
    Ms = m["Ms"]
    F = len(Ms)
    for k in C.SPLIT["test"]:
        for tk, ra, rb, rc, score, _ in run(recs[k], defs_for(m, k), det, 0, None):
            if tk.t < C.BASELINE_S or tk.vec is None:
                continue
            clean["ticks"] += 1
            clean["range"] += ra
            clean["range_hold"] += rb
            clean["crewwatch"] += rc
            fs = sum(sum(Ms[i][j] * tk.vec[j] for j in range(F)) ** 2 for i in range(F))
            clean["disagree"] += (fs > m["threshold_float"]) != rc
    fa = {meth: clean[meth] / float(clean["ticks"]) for meth in ("range", "range_hold", "crewwatch")}
    print("clean test ticks %d, FA %s, int/float disagreement %.3f %%" % (
        clean["ticks"], {k: "%.3f%%" % (100 * v) for k, v in fa.items()},
        100.0 * clean["disagree"] / clean["ticks"]))

    # ---- faults
    events = []
    contrib_acc = {}
    for ftype in sorted(FT.TYPES):
        name, desc, dur = FT.TYPES[ftype]
        kk = a.k_events if ftype != 4 else max(2, a.k_events // 4)
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
        print("type %d %-34s n=%3d  range %5.1f%%  range+hold %5.1f%%  crewwatch %5.1f%%" % (
            ftype, desc, s["range"]["n"], 100 * s["range"]["rate"], 100 * s["range_hold"]["rate"],
            100 * s["crewwatch"]["rate"]))

    res = {"limits": tl, "clean": clean, "fa": fa, "events": events,
           "by_type": {t: summarise([e for e in events if e["type"] == t]) for t in FT.TYPES},
           "top_contributor_at_first_alarm": contrib_acc,
           "model": {"F": F, "weight_bytes": m["weight_bytes"], "threshold_int": m["threshold_int"],
                     "fa_budget": m["fa_budget"], "val_int_float_agreement": m["val_int_float_agreement"]}}
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("wrote eval/results.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
