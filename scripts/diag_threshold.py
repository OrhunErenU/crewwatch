"""Which features drive the top validation scores (that set the threshold)?
And which channels make the range check fire on clean TEST data?"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "eval")); sys.path.insert(0, os.path.join(ROOT, "sim"))
import evaluate as EV, crew as C
m, qm = EV.load_model()
rows = []
for k in C.SPLIT["val"]:
    for tk in C.replay(C.load(k), EV.defs_for(m, k)):
        if tk.t >= C.BASELINE_S and tk.vec:
            s, contrib, _ = qm.score(tk.vec); rows.append((s, contrib))
rows.sort(key=lambda r: -r[0]); top = rows[:max(1, len(rows)//1000)]
cnt = {}
for s, c in top:
    f = m["features"][max(range(len(c)), key=lambda i: c[i])]["name"]; cnt[f] = cnt.get(f, 0) + 1
print("top-0.1%% val ticks (%d), leading contributor:" % len(top), cnt)
res = json.load(open(os.path.join(ROOT, "eval", "results.json")))
L = res["limits"]["limits"]; per = {}
for k in C.SPLIT["test"]:
    for tk in C.replay(C.load(k), EV.defs_for(m, k)):
        if tk.t < C.BASELINE_S: continue
        for ci, v in enumerate(tk.latched):
            if v is not None and not (L[ci][0] <= v <= L[ci][1]):
                per[(k, C.CHANNELS[ci][0])] = per.get((k, C.CHANNELS[ci][0]), 0) + 1
print("range violations on clean test:", per)
print("limits:", [(C.CHANNELS[i][0], round(L[i][0]), round(L[i][1])) for i in range(len(L))])
