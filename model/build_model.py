#!/usr/bin/env python3
"""
CrewWatch models: Mahalanobis on the flight chain, int8, thresholds from INTEGER scores.

Adapted from vendor ground/build_maha.py (same algebra, same vendor quantizer):
    d^2 = x^T Sigma^-1 x,  Sigma^-1 = L L^T,  M = L^T,  W_enc = I - sM,  W_dec = I
    flight score = || x - W_dec W_enc x ||^2 = s^2 d^2

Two instances of the SAME model shape (F x F, two matvecs + SqErr):
    fast  scores the 1 Hz feature vector          -> sensor faults in seconds
    slow  scores the flight window mean (64 s,     -> sustained physiological shifts
          vendor TLM_WATCH_WindowMean)
Alarm = fast OR slow. Each threshold is set on validation at HALF the budget,
so the combined validation false-alarm rate stays within the matched budget.

Feature table = per astronaut (Bias = personal baseline), model tables = shared.
Written with AI assistance (Claude Code), see AI_USE.md.

    python3 model/build_model.py            (WSL; needs data/dalia_1hz + features .so)
Outputs model/model.json, board/tlm_watch_model_tbl.c (fast), board/tlm_watch_model_slow_tbl.c
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
TARGET = 4000              # RAW: p99.9 of |centred feature| maps here (int16 headroom x8)
COUNTER_TARGET = int(os.environ.get("CW_COUNTER_TARGET", 400))  # HOLD/AGE: train max maps here (D-17)
SHIFT = 8
RIDGE = float(os.environ.get("CW_RIDGE", 3e-2))               # D-17


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


def fit(Xtr, Xval, budget, ti, label):
    """Mahalanobis -> flight chain -> int8; threshold from integer val scores."""
    F = len(Xtr[0])
    m = E.Mahalanobis(Xtr, ridge_frac=RIDGE)
    L = cholesky(m.inv)
    M = [[L[j][i] for j in range(F)] for i in range(F)]
    s = 1.0 / max(abs(M[i][j]) for i in range(F) for j in range(F))
    Ms = [[M[i][j] * s for j in range(F)] for i in range(F)]
    w_enc = [(1.0 if i == j else 0.0) - Ms[i][j] for i in range(F) for j in range(F)]
    w_dec = [1.0 if i == j else 0.0 for i in range(F) for j in range(F)]
    q = Q.quantize_model(w_enc, F, F, w_dec, F, F, scale_hidden=1.0,
                         act_enc=TI.ACT_NONE, act_dec=TI.ACT_NONE)
    qm = Q.model_to_tinyinfer(q, ti=ti)

    def fscore(x):
        return sum(sum(Ms[i][j] * x[j] for j in range(F)) ** 2 for i in range(F))

    iv = [qm.score(x)[0] for x in Xval]
    fv = [fscore(x) for x in Xval]
    thr_i = pctl(iv, 1 - budget)
    thr_f = pctl(fv, 1 - budget)
    agree = sum(1 for a, b in zip(iv, fv) if (a > thr_i) == (b > thr_f)) / float(len(iv))
    print("  [%s] train %d  val %d  max|mu| %.1f LSB  s %.4g  thr int %d / float %.1f  int-float agreement %.3f %%" % (
        label, len(Xtr), len(Xval), max(abs(v) for v in m.mu), s, thr_i, thr_f, 100 * agree))
    return {"quant": q, "Ms": Ms, "s": s, "threshold_int": thr_i, "threshold_float": thr_f,
            "val_int_float_agreement": agree}


def main():
    subjects = C.SPLIT["train"] + C.SPLIT["val"] + C.SPLIT["test"]
    recs = {k: C.load(k) for k in subjects}
    raw_idx = [i for i, (_, xf) in enumerate(C.FEATURES) if xf == B.XFORM_RAW]

    # -- pass 1: unscaled features (Bias 0, Scale 1); baseline means only
    d0 = C.feature_defs()
    base, unscaled = {}, {}
    for k in subjects:
        v = [tk.vec for tk in C.replay(recs[k], d0) if tk.vec is not None]
        unscaled[k] = v
        nb = min(len(v), C.BASELINE_S)
        base[k] = [mean([x[i] for x in v[:nb]]) for i in range(C.F)]

    offset = []
    for i in range(C.F):
        vals = []
        for k in C.SPLIT["train"]:
            b = base[k][i] if i in raw_idx else 0.0
            vals.extend(x[i] - b for x in unscaled[k])
        offset.append(mean(vals))

    def bias_for(k):
        return [int(round((base[k][i] if i in raw_idx else 0.0) + offset[i])) for i in range(C.F)]

    dev = [[] for _ in range(C.F)]
    for k in C.SPLIT["train"]:
        b = bias_for(k)
        for x in unscaled[k]:
            for i in range(C.F):
                dev[i].append(abs(x[i] - b[i]))
    scale = []
    for i in range(C.F):
        p = max(1.0, pctl(dev[i], 0.999) if i in raw_idx else max(dev[i]))
        tgt = TARGET if i in raw_idx else COUNTER_TARGET
        scale.append(max(1, int(round(tgt * (1 << SHIFT) / p))))
    shift = [SHIFT] * C.F
    tables = {k: {"bias": bias_for(k), "scale": scale, "shift": shift,
                  "baseline": {C.FEATURES[i][0]: base[k][i] for i in raw_idx}} for k in subjects}

    # -- pass 2: final integer features + flight window means
    X, W = {}, {}
    for k in subjects:
        t = tables[k]
        X[k], W[k] = [], []
        for tk in C.replay(recs[k], C.feature_defs(t["bias"], t["scale"], t["shift"])):
            if tk.vec is None:
                continue
            ev = tk.t >= C.BASELINE_S
            X[k].append((ev, tk.vec))
            if tk.wmean is not None:
                W[k].append((ev, tk.wmean))
    tr = lambda D: [v for k in C.SPLIT["train"] for _, v in D[k]]          # noqa: E731
    va = lambda D: [v for k in C.SPLIT["val"] for ev, v in D[k] if ev]      # noqa: E731
    sat = sum(1 for x in tr(X) for v in x if v in (32767, -32768)) / float(len(tr(X)) * C.F)

    print("=" * 74)
    print(" CrewWatch models -- Mahalanobis on the flight chain (fast + slow)")
    print("=" * 74)
    print("  F = %d features -> %d-byte int8 table per model" % (C.F, 2 * C.F * C.F))
    print("  int16 saturation on train features: %.4f %%" % (100 * sat))
    ti = TI.TinyInfer()
    fast = fit(tr(X), va(X), FA_BUDGET / 2, ti, "fast")
    slow = fit(tr(W), va(W), FA_BUDGET / 2, ti, "slow")

    out = {
        "features": [{"name": C.feature_name(i), "channel": C.FEATURES[i][0],
                      "xform": B.XFORM_NAMES[C.FEATURES[i][1]]} for i in range(C.F)],
        "tables": {str(k): v for k, v in tables.items()},
        "fast": fast, "slow": slow,
        # kept for older readers: the fast model at top level
        "quant": fast["quant"], "Ms": fast["Ms"], "threshold_int": fast["threshold_int"],
        "threshold_float": fast["threshold_float"], "val_int_float_agreement": fast["val_int_float_agreement"],
        "fa_budget": FA_BUDGET, "train_saturation": sat, "split": C.SPLIT, "baseline_s": C.BASELINE_S,
        "packet_loss": C.PACKET_LOSS, "weight_bytes": 2 * C.F * C.F, "window_len": B.WINDOW_LEN,
        "ridge": RIDGE, "counter_target": COUNTER_TARGET,
    }
    with open(os.path.join(HERE, "model.json"), "w") as f:
        json.dump(out, f)
    os.makedirs(os.path.join(ROOT, "board"), exist_ok=True)
    Q.emit_c_table(fast["quant"], fast["threshold_int"], os.path.join(ROOT, "board", "tlm_watch_model_tbl.c"),
                   stamp="CrewWatch FAST Mahalanobis F=%d, threshold from INTEGER model on validation" % C.F)
    Q.emit_c_table(slow["quant"], slow["threshold_int"], os.path.join(ROOT, "board", "tlm_watch_model_slow_tbl.c"),
                   stamp="CrewWatch SLOW (64-tick window mean) Mahalanobis F=%d, INTEGER threshold" % C.F)
    print("  wrote model/model.json, board/tlm_watch_model_tbl.c, board/tlm_watch_model_slow_tbl.c")
    return 0


if __name__ == "__main__":
    sys.exit(main())
