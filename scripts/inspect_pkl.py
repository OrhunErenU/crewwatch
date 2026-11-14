import sys, zipfile, pickle, numpy as np
z = zipfile.ZipFile(sys.argv[1]); d = pickle.load(z.open("PPG_FieldStudy/S1/S1.pkl"), encoding="latin1")
print(d.keys()); print(d["signal"]["wrist"].keys(), d["signal"]["chest"].keys())
a = np.asarray(d["signal"]["wrist"]["ACC"], float); print("wrist ACC shape", a.shape, "mean", a.mean(0), "norm median", np.median(np.linalg.norm(a, axis=1)))
print("TEMP", np.asarray(d["signal"]["wrist"]["TEMP"]).ravel()[:8]); print("EDA", np.asarray(d["signal"]["wrist"]["EDA"]).ravel()[:8])
print("label", len(d["label"]), d["label"][:5], "rpeaks", len(d["rpeaks"]), "activity", np.asarray(d["activity"]).shape, np.unique(np.asarray(d["activity"])))
