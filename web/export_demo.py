#!/usr/bin/env python3
"""
Precompute the panel's replay data (ROADMAP rule 1: the browser does NOT
compute scores -- it plays back what the flight C code produced on the host).

Scenario: the 4 test subjects are the crew; one injected fault each (+ a
second one for Crew D). Everything else in the recordings is real PPG-DaLiA.

    python3 web/export_demo.py        (WSL, after model/ and eval/)
Writes web/data.js  (window.CREWWATCH = {...})
Written with AI assistance (Claude Code), see AI_USE.md.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "sim"))
sys.path.insert(0, os.path.join(ROOT, "eval"))
sys.path.insert(0, os.path.join(ROOT, "explain"))
import importlib.util  # noqa: E402
import crew as C  # noqa: E402
import faults as FT  # noqa: E402
import explain as X  # noqa: E402

# load OUR eval/evaluate.py by path (vendor ground/ also has an evaluate.py on sys.path)
_spec = importlib.util.spec_from_file_location("cw_evaluate", os.path.join(ROOT, "eval", "evaluate.py"))
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)

SCENARIO = {
    12: [(1, 2400)],
    13: [(3, None)],          # None -> first real activity onset after baseline
    14: [(4, 2400)],
    15: [(2, 2000), (5, 5400)],
}


def merge(rec, plan):
    r = rec
    sup = {}
    label = [0] * len(rec["t"])
    marks = []
    for ftype, onset in plan:
        if onset is None:
            onset = FT.onsets(rec, ftype, 1)[0]
        r, s, lab = FT.inject(r, ftype, onset)
        for src, ticks in s.items():
            sup.setdefault(src, set()).update(ticks)
        for i, v in enumerate(lab):
            if v:
                label[i] = v
        marks.append({"type": ftype, "name": FT.TYPES[ftype][1], "onset": onset,
                      "end": min(len(rec["t"]), onset + FT.TYPES[ftype][2])})
    return r, sup, label, marks


def main():
    m, qm = EV.load_model()
    with open(os.path.join(ROOT, "eval", "results.json")) as f:
        res = json.load(f)
    lim = res["limits"]
    det = EV.Detectors(m, qm, lim["limits"], lim["hold_n"])
    crew = []
    for k, plan in SCENARIO.items():
        rec = C.load(k)
        r, sup, label, marks = merge(rec, plan)
        tab = m["tables"][str(k)]
        series = {ch[0]: [] for ch in C.CHANNELS}
        score, a, b, c, alerts = [], [], [], [], []
        prev_c = False
        last_expl = -999
        det.set_subject(k)      # personal range limits (D-18) -- same as eval
        for tk in C.replay(r, EV.defs_for(m, k), suppress=sup, seed=k):
            ra, rb, rc, sc, contrib = det.step(tk)
            for ci, ch in enumerate(C.CHANNELS):
                series[ch[0]].append(tk.latched[ci])
            score.append(sc)
            a.append(int(ra))
            b.append(int(rb))
            c.append(int(rc))
            score[-1] = None if sc is None else round(sc, 4)      # ratio to own threshold, > 1 = alarm
            if rc and (not prev_c or tk.t - last_expl >= 30):
                ratio, _, which, raw, thr = det.last
                ev = {"score": raw, "threshold": thr, "contrib": contrib, "model": ("fast", "slow")[which],
                      "features": [f["name"] for f in m["features"]],
                      "latched": {ch[0]: tk.latched[ci] for ci, ch in enumerate(C.CHANNELS)},
                      "baseline": tab["baseline"], "hold": tk.hold, "age": tk.age,
                      "hold_n": lim["hold_n"]}
                e = X.explain(ev)
                e["t"] = tk.t
                alerts.append(e)
                last_expl = tk.t
            prev_c = rc
        crew.append({"id": C.CREW[k], "subject": "PPG-DaLiA S%d" % k, "t0": rec["t"][0],
                     "series": series, "score": score, "range": a, "range_hold": b, "crewwatch": c,
                     "label": label, "faults": marks, "alerts": alerts,
                     "activity": rec["activity"], "baseline": tab["baseline"]})
        print("%s: %d ticks, %d CrewWatch alert cards, faults %s" % (
            C.CREW[k], len(score), len(alerts), [(x["type"], x["onset"]) for x in marks]))

    with open(os.path.join(ROOT, "data", "nasa", "donki_sep.json")) as f:
        sep = json.load(f)
    out = {
        "generated_by": "web/export_demo.py -- scores from flight C code (tinyinfer) via ctypes",
        "channels": [{"key": ch[0], "unit": ch[5], "name": ch[6], "scale": ch[4]} for ch in C.CHANNELS],
        "threshold": 1.0, "limits": lim["limits"], "hold_n": lim["hold_n"], "baseline_s": C.BASELINE_S,
        "crew": crew, "donki_sep": sep,
        "results": {"by_type": res["by_type"], "fa": res["fa"], "model": res["model"],
                    "chance": res.get("chance_by_type", {})},
        "fault_types": {str(t): {"key": v[0], "name": v[1], "duration": v[2]} for t, v in FT.TYPES.items()},
    }
    with open(os.path.join(HERE, "data.js"), "w") as f:
        f.write("window.CREWWATCH = ")
        json.dump(out, f, separators=(",", ":"))
        f.write(";\n")
    print("wrote web/data.js (%.1f MB)" % (os.path.getsize(os.path.join(HERE, "data.js")) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
