"""
Shared definitions: channels, packets, crew split, feature table, replay loop.

The replay loop turns 1 Hz channel values into byte packets per source and
feeds them to features/bridge.Engine (flight C code). Nothing here computes a
feature or a score.
Written with AI assistance (Claude Code), see AI_USE.md.
"""
import csv
import os
import random
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "features"))
import bridge as B  # noqa: E402

DATA = os.path.join(ROOT, "data", "dalia_1hz")

# ---------------------------------------------------------------- channels
# name, source, packet offset, C type, unit scale (raw -> physical), unit
CHANNELS = [
    ("hr_x10",    0, 2, B.TYPE_U16_LE, 0.1,   "bpm",   "heart rate"),
    ("rmssd_x10", 0, 4, B.TYPE_U16_LE, 0.1,   "ms",    "HRV (RMSSD)"),
    ("act_mg",    1, 2, B.TYPE_U16_LE, 1.0,   "mg",    "activity"),
    ("temp_x100", 1, 4, B.TYPE_I16_LE, 0.01,  "degC",  "skin temperature"),
    ("eda_x1000", 1, 6, B.TYPE_U16_LE, 0.001, "uS",    "skin conductance"),
]
CH = {c[0]: i for i, c in enumerate(CHANNELS)}
SOURCES = ["chest strap", "wrist band"]
N_SOURCES = 2

# packet layouts: little-endian, u16 sequence counter first
PKT_FMT = ["<HHH", "<HHhH"]

# ---------------------------------------------------------------- split
# Fixed BEFORE any result was looked at (DECISIONS D-09). Person-wise.
SPLIT = {"train": [1, 2, 3, 4, 5, 6, 7, 8], "val": [9, 10, 11], "test": [12, 13, 14, 15]}
CREW = {12: "Crew A", 13: "Crew B", 14: "Crew C", 15: "Crew D"}

BASELINE_S = 1200        # personal baseline window at record start (D-10)
PACKET_LOSS = 0.01       # i.i.d. per packet, assumption (D-11)

# ---------------------------------------------------------------- features
# (channel or source, transform)
FEATURES = [
    ("hr_x10", B.XFORM_RAW), ("rmssd_x10", B.XFORM_RAW), ("act_mg", B.XFORM_RAW),
    ("temp_x100", B.XFORM_RAW), ("eda_x1000", B.XFORM_RAW),
    # No DIFF: vendor DIFF is counter semantics (unsigned, width-masked), so a
    # falling HR gives 65535 instead of -1. See DECISIONS D-13.
    # HOLD only where a healthy signal always moves (D-15)
    ("hr_x10", B.XFORM_HOLD), ("rmssd_x10", B.XFORM_HOLD),
    ("src0", B.XFORM_AGE), ("src1", B.XFORM_AGE),
]
F = len(FEATURES)


def feature_name(i):
    ch, xf = FEATURES[i]
    if ch.startswith("src"):
        return "%s silence (AGE)" % SOURCES[int(ch[3:])]
    return "%s %s" % (CHANNELS[CH[ch]][6], B.XFORM_NAMES[xf])


def feature_defs(bias=None, scale=None, shift=None):
    defs = []
    for i, (ch, xf) in enumerate(FEATURES):
        b = bias[i] if bias else 0
        s = scale[i] if scale else 1
        h = shift[i] if shift else 0
        if ch.startswith("src"):
            defs.append(B.FeatureDef(int(ch[3:]), 0, B.TYPE_U16_LE, xf, b, s, h, name=feature_name(i)))
        else:
            c = CHANNELS[CH[ch]]
            defs.append(B.FeatureDef(c[1], c[2], c[3], xf, b, s, h, name=feature_name(i)))
    return defs


# ---------------------------------------------------------------- data
def load(k):
    path = os.path.join(DATA, "S%d.csv" % k)
    cols = {}
    with open(path) as f:
        r = csv.DictReader(f)
        for name in r.fieldnames:
            cols[name] = []
        for row in r:
            for name in r.fieldnames:
                cols[name].append(int(row[name]))
    cols["subject"] = k
    return cols


def copy_rec(rec):
    out = {k: (list(v) if isinstance(v, list) else v) for k, v in rec.items()}
    return out


# ---------------------------------------------------------------- replay
class Tick(object):
    __slots__ = ("t", "vec", "latched", "hold", "age", "wmean")

    def __init__(self, t, vec, latched, hold, age, wmean=None):
        self.t, self.vec, self.latched, self.hold, self.age = t, vec, latched, hold, age
        self.wmean = wmean   # flight window mean of the last 64 vectors (None until full)


def replay(rec, defs, suppress=None, start=0, stop=None, seed=0, loss=PACKET_LOSS):
    """Feed rec[start:stop] tick by tick into the flight feature code.

    suppress: optional {src: set(tick index)} -- packets withheld (fault 2).
    Yields Tick objects. latched = last RECEIVED value per channel (what a
    limit checker on the downlinked telemetry sees), None until first packet.
    """
    eng = B.Engine(defs, N_SOURCES)
    win = B.Window(len(defs))
    rnd = random.Random(seed * 1000003 + rec["subject"])
    n = len(rec["t"])
    stop = n if stop is None else min(stop, n)
    latched = [None] * len(CHANNELS)
    hold_idx = [i for i, (_, xf) in enumerate(FEATURES) if xf == B.XFORM_HOLD]
    seq = [0, 0]
    for i in range(start, stop):
        for src in range(N_SOURCES):
            if suppress and i in suppress.get(src, ()):
                continue
            if rnd.random() < loss:
                continue
            seq[src] = (seq[src] + 1) & 0xFFFF
            if src == 0:
                pkt = struct.pack(PKT_FMT[0], seq[0], rec["hr_x10"][i], rec["rmssd_x10"][i])
                latched[0], latched[1] = rec["hr_x10"][i], rec["rmssd_x10"][i]
            else:
                pkt = struct.pack(PKT_FMT[1], seq[1], rec["act_mg"][i], rec["temp_x100"][i], rec["eda_x1000"][i])
                latched[2], latched[3], latched[4] = rec["act_mg"][i], rec["temp_x100"][i], rec["eda_x1000"][i]
            eng.latch(src, pkt)
        vec = eng.tick()
        wmean = None
        if vec is not None:
            win.push(vec)
            if win.full():
                wmean = win.mean()
        ht = eng.hold_ticks()
        yield Tick(i, vec, list(latched), {FEATURES[j][0]: ht[j] for j in hold_idx}, list(eng.age), wmean)
