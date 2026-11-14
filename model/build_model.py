#!/usr/bin/env python3
"""
CrewWatch model: Mahalanobis on the flight chain, int8, threshold from INTEGER scores.

Adapted from vendor ground/build_maha.py (same algebra, same vendor quantizer):
    d^2 = x^T Sigma^-1 x,  Sigma^-1 = L L^T,  M = L^T,  W_enc = I - sM,  W_dec = I
    flight score = || x - W_dec W_enc x ||^2 = s^2 d^2

Feature table = per astronaut (Bias = personal baseline), model table = shared.

    python3 model/build_model.py            (WSL; needs data/dalia_1hz + features .so)

Outputs
    model/model.json                       everything eval/ and web/ need
    board/tlm_watch_model_tbl.c            same weights as a cFS table source (P2)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "sim"))
import crew as C  # noqa: E402
import bridge as B  # noqa: E402  (path set by crew)
sys.path.insert(0, B.GROUND)
import evaluate as E  # noqa: E402  vendor
import quantize as Q  # noqa: E402  vendor
import tinyinfer_ctypes as TI  # noqa: E402  vendor

FA_BUDGET = 0.001          # matched false-alarm budget: 0.1 % of validation ticks (D-12)
TARGET = 4000              # p99.9 of |centred feature| maps here (int16 headroom x8)
SHIFT = 8
RIDGE = 1e-3


def vectors(rec, defs, start=0, stop=None, seed=0):
    return [tk.vec for tk in C.replay(rec, defs, start=start, stop=stop, seed=seed) if tk.vec is not None]


def mean(col):
    return sum(col) / float(len(col))


def cholesky(A):
    n = len(A)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                L[i][j] = math.sqrt(max(A[i][i] - s, 1e-12))
            else:
                L[i][j] = (A[i][j] - s) / L[j][j]
    return L


def pctl(vals, q):
    v = sorted(vals)
    return v[min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))]


def main():
    subjects = C.SPLIT["train"] + C.SPLIT["val"] + C.SPLIT["test"]
    recs = {k: C.load(k) for k in subjects}
    raw_idx = [i for i, (_, xf) in enumerate(C.FEATURES) if xf == B.XFORM_RAW]

    # -- pass 1: unscaled features (Bias 0, Scale 1). EDA x1000 may clip int16
    #    at 32.767 uS here; only the baseline MEAN is taken from this pass.
    d0 = C.feature_defs()
    base = {}
    unscaled = {}
    for k in subjects:
        v = vectors(recs[k], d0)
        unscaled[k] = v
        nb = min(len(v), C.BASELINE_S)
        base[k] = [mean([x[i] for x in v[:nb]]) for i in range(C.F)]

    # population offset: mean over TRAIN of (x - personal baseline) for RAW;
    # plain train mean for DIFF/HOLD/AGE (no personal component).
    offset = []
    for i in range(C.F):
        vals = []
        for k in C.SPLIT["train"]:
            b = base[k][i] if i in raw_idx else 0.0
            vals.extend(x[i] - b for x in unscaled[k])
        offset.append(mean(vals))

    def bias_for(k):
        return [int(round((base[k][i] if i in raw_idx else 0.0) + offset[i])) for i in range(C.F)]

    # scale: p99.9 |x - bias| over train -> TARGET
    dev = [[] for _ in range(C.F)]
    for k in C.SPLIT["train"]:
        b = bias_for(k)
        for x in unscaled[k]:
            for i in range(C.F):
                dev[i].append(abs(x[i] - b[i]))
    scale = []
    for i in range(C.F):
        p = max(1.0, pctl(dev[i], 0.999))
        scale.append(max(1, int(round(TARGET * (1 << SHIFT) / p))))
    shift = [SHIFT] * C.F

    # personal baseline per channel (raw units) -- used by explain/ to say "your usual"
    tables = {k: {"bias": bias_for(k), "scale": scale, "shift": shift,
                  "baseline": {C.FEATURES[i][0]: base[k][i] for i in raw_idx}} for k in subjects}

    # -- pass 2: final integer features
    X = {}
    for k in subjects:
        t = tables[k]
        X[k] = vectors(recs[k], C.feature_defs(t["bias"], t["scale"], t["shift"]))
    Xtr = [x for k in C.SPLIT["train"] for x in X[k]]
    sat = sum(1 for x in Xtr for v in x if v in (32767, -32768)) / float(len(Xtr) * C.F)

    m = E.Mahalanobis(Xtr, ridge_frac=RIDGE)
    L = cholesky(m.inv)
    M = [[L[j][i] for j in range(C.F)] for i in range(C.F)]
    mx = max(abs(M[i][j]) for i in range(C.F) for j in range(C.F))
    s = 1.0 / mx
    Ms = [[M[i][j] * s for j in range(C.F)] for i in range(C.F)]
    w_enc = [(1.0 if i == j else 0.0) - Ms[i][j] for i in range(C.F) for j in range(C.F)]
    w_dec = [1.0 if i == j else 0.0 for i in range(C.F) for j in range(C.F)]

    ti = TI.TinyInfer()
    q = Q.quantize_model(w_enc, C.F, C.F, w_dec, C.F, C.F,
                         scale_hidden=1.0, act_enc=TI.ACT_NONE, act_dec=TI.ACT_NONE)
    qm = Q.model_to_tinyinfer(q, ti=ti)

    def fscore(x):
        return sum(sum(Ms[i][j] * x[j] for j in range(C.F)) ** 2 for i in range(C.F))

    # thresholds on VALIDATION, evaluation part only (after personal baseline)
    val = [x for k in C.SPLIT["val"] for x in X[k][C.BASELINE_S:]]
    iv = [qm.score(x)[0] for x in val]
    fv = [fscore(x) for x in val]
    thr_i = pctl(iv, 1 - FA_BUDGET)
    thr_f = pctl(fv, 1 - FA_BUDGET)
    agree = sum(1 for a, b in zip(iv, fv) if (a > thr_i) == (b > thr_f)) / float(len(iv))
    mu_max = max(abs(v) for v in m.mu)

    print("=" * 70)
    print(" CrewWatch model -- Mahalanobis on the flight chain")
    print("=" * 70)
    print("  F = %d features, weights %d bytes (2 x F x F int8)" % (C.F, 2 * C.F * C.F))
    print("  train vectors %d (subjects %s), val %d" % (len(Xtr), C.SPLIT["train"], len(val)))
    print("  int16 saturation on train features: %.4f %%" % (100 * sat))
    print("  train mean after centring, max |mu| = %.1f LSB (target ~0 of %d)" % (mu_max, TARGET))
    print("  scale s = %.4g" % s)
    print("  threshold  int = %d   float = %.1f   (val FA budget %.2f %%)" % (thr_i, thr_f, 100 * FA_BUDGET))
    print("  int vs float decision agreement on val: %.3f %%" % (100 * agree))

    out = {
        "features": [{"name": C.feature_name(i), "channel": C.FEATURES[i][0],
                      "xform": B.XFORM_NAMES[C.FEATURES[i][1]]} for i in range(C.F)],
        "tables": {str(k): v for k, v in tables.items()},
        "quant": {k: v for k, v in q.items()},
        "Ms": Ms, "s": s, "threshold_int": thr_i, "threshold_float": thr_f,
        "fa_budget": FA_BUDGET, "val_int_float_agreement": agree,
        "train_saturation": sat, "split": C.SPLIT, "baseline_s": C.BASELINE_S,
        "packet_loss": C.PACKET_LOSS, "weight_bytes": 2 * C.F * C.F,
    }
    with open(os.path.join(HERE, "model.json"), "w") as f:
        json.dump(out, f)
    os.makedirs(os.path.join(ROOT, "board"), exist_ok=True)
    Q.emit_c_table(q, thr_i, os.path.join(ROOT, "board", "tlm_watch_model_tbl.c"),
                   stamp="CrewWatch Mahalanobis F=%d, threshold from INTEGER model on validation subjects" % C.F)
    print("  wrote model/model.json, board/tlm_watch_model_tbl.c")
    return 0


if __name__ == "__main__":
    sys.exit(main())
