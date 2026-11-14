import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import crew as C
m = json.load(open(os.path.join(ROOT, "model", "model.json")))
for split in ("train", "val"):
    X = []
    for k in C.SPLIT[split]:
        t = m["tables"][str(k)]
        X += [tk.vec for tk in C.replay(C.load(k), C.feature_defs(t["bias"], t["scale"], t["shift"])) if tk.vec]
    n = len(X)
    print(split, n)
    for i in range(C.F):
        col = [x[i] for x in X]; mu = sum(col)/n; sd = (sum((v-mu)**2 for v in col)/n)**.5
        print("  %-34s mu %8.1f sd %8.1f min %6d max %6d  scale %d bias(S%d) %d" % (C.feature_name(i), mu, sd, min(col), max(col), t["scale"][i], k, t["bias"][i]))
