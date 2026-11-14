"""
Evidence packet -> short alert an astronaut can act on.

Same rule as vendor ground/tlm_explain.py: nothing is invented. Every sentence
is built from a number in the evidence packet, and selftest() checks that each
sentence carries at least one of those numbers. Language is "check / early
warning", never a diagnosis (ROADMAP rule 4).

Evidence packet (dict):
  score, threshold          int, from the flight C code
  contrib                   per-row SqErr contributions (flight C code)
  features                  names, same order as contrib
  latched                   {channel: raw value last received}
  baseline                  {channel: personal baseline, raw units}
  hold                      {channel: ticks unchanged}
  age                       [ticks since packet, per source]
  hold_n                    {channel: HOLD rule limit}

Note on attribution: with M = L^T (upper-triangular), row i of the residual
mixes feature i with later features. The ranking is the flight evidence packet
as produced on board; we label it "contribution", not "cause".
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import crew as C  # noqa: E402

AGE_ALERT = 5     # s without packets before we call a source silent (assumption)


def phys(ch, raw):
    c = C.CHANNELS[C.CH[ch]]
    return raw * c[4], c[5]


def fmt(ch, raw):
    v, u = phys(ch, raw)
    if ch == "temp_x100":
        return "%.2f %s" % (v, u)
    if ch == "eda_x1000":
        return "%.2f %s" % (v, u)
    if ch == "act_mg":
        return "%d %s" % (round(v), u)
    return "%.1f %s" % (v, u)


def explain(ev):
    """-> {"level", "headline", "lines": [...], "actions": [...]}"""
    lines, actions = [], []
    over = ev["score"] / float(ev["threshold"]) if ev["threshold"] else 0.0

    for s, a in enumerate(ev["age"]):
        if a >= AGE_ALERT and a != 0xFFFF:
            lines.append("%s has sent no data for %d s." % (C.SOURCES[s].capitalize(), a))
            actions.append("Check the %s: battery, fit, Bluetooth link." % C.SOURCES[s])
    silent = {C.CHANNELS[i][1] for i in range(len(C.CHANNELS))
              if ev["age"][C.CHANNELS[i][1]] >= AGE_ALERT}

    for ch, n in sorted(ev["hold"].items()):
        lim = ev["hold_n"].get(ch)
        if lim and n >= lim and C.CHANNELS[C.CH[ch]][1] not in silent:
            name = C.CHANNELS[C.CH[ch]][6]
            lines.append("%s has read exactly %s for %d s while data keeps arriving "
                         "(longest seen in normal data: %d s)." % (
                             name.capitalize(), fmt(ch, ev["latched"][ch]), n, lim - 1))
            actions.append("Sensor may be frozen: re-seat or restart the %s." %
                           C.SOURCES[C.CHANNELS[C.CH[ch]][1]])

    hr, act = ev["latched"].get("hr_x10"), ev["latched"].get("act_mg")
    bhr, bact = ev["baseline"].get("hr_x10"), ev["baseline"].get("act_mg")
    if None not in (hr, act, bhr, bact) and not silent:
        d_act = act - bact
        d_hr = (hr - bhr) / 10.0
        if d_act >= 100 and d_hr < 5:
            lines.append("Activity is %d mg above your baseline but heart rate is only %+.1f bpm "
                         "from your baseline." % (d_act, d_hr))
            actions.append("Check chest-strap electrode contact (skin moist, strap snug).")

    tot = float(sum(max(0, c) for c in ev["contrib"])) or 1.0
    order = sorted(range(len(ev["contrib"])), key=lambda i: -ev["contrib"][i])[:3]
    top = []
    for i in order:
        share = 100.0 * max(0, ev["contrib"][i]) / tot
        if share < 5:
            continue
        nm = ev["features"][i]
        ch = C.FEATURES[i][0]
        if C.FEATURES[i][1] == C.B.XFORM_RAW and ch in ev["latched"] and ch in ev["baseline"]:
            top.append("%s %.0f %% (now %s, your baseline %s)" % (
                nm, share, fmt(ch, ev["latched"][ch]), fmt(ch, ev["baseline"][ch])))
        else:
            top.append("%s %.0f %%" % (nm, share))
    if top:
        lines.append("Largest contributions to the score: " + "; ".join(top) + ".")

    if not actions:
        actions.append("Unusual combination of readings. Check sensor fit first; "
                       "if sensors are fine, note how you feel and log it for the crew medical officer.")
    level = "ALERT" if over >= 1.0 else "OK"
    headline = "Score %d is %.1fx the alert threshold %d." % (ev["score"], over, ev["threshold"])
    return {"level": level, "headline": headline, "lines": lines, "actions": actions}


def selftest():
    import re
    ev = {"score": 900000, "threshold": 30000, "contrib": [500, 100, 300, 0, 0, 0, 0, 80000, 0, 0, 0, 0, 0, 0],
          "features": [C.feature_name(i) for i in range(C.F)],
          "latched": {"hr_x10": 712, "rmssd_x10": 400, "act_mg": 320, "temp_x100": 3310, "eda_x1000": 2100},
          "baseline": {"hr_x10": 690.0, "rmssd_x10": 420.0, "act_mg": 40.0, "temp_x100": 3290.0, "eda_x1000": 1800.0},
          "hold": {"hr_x10": 120, "rmssd_x10": 0, "act_mg": 0, "temp_x100": 8, "eda_x1000": 3},
          "age": [0, 0], "hold_n": {"hr_x10": 9, "rmssd_x10": 30, "act_mg": 30, "temp_x100": 200, "eda_x1000": 200}}
    out = explain(ev)
    ok = True
    for ln in out["lines"]:
        if not re.search(r"\d", ln):
            print("  FAIL sentence without a number: %s" % ln)
            ok = False
    checks = [
        ("frozen HR reported", any("120 s" in l and "Heart rate" in l for l in out["lines"])),
        ("decoupling reported", any("280 mg above" in l for l in out["lines"])),
        ("no diagnosis words", not any(w in " ".join(out["lines"] + out["actions"]).lower()
                                       for w in ("diagnos", "infection", "disease", "you have"))),
        ("level ALERT", out["level"] == "ALERT"),
    ]
    ev2 = dict(ev, age=[40, 0], hold={k: 0 for k in ev["hold"]})
    out2 = explain(ev2)
    checks.append(("silence reported, no HR advice", any("no data for 40 s" in l for l in out2["lines"])
                   and not any("electrode" in a for a in out2["actions"])))
    for name, c in checks:
        print("  %s  %s" % ("ok  " if c else "FAIL", name))
        ok = ok and c
    for ln in out["lines"] + out["actions"]:
        print("     | " + ln)
    print("explain selftest: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest())
