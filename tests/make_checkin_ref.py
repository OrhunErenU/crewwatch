#!/usr/bin/env python3
"""Host reference for the check-in bit-exact test: runs crewwatch_checkin.c
(gcc build, features/libcrewwatch_feat.so) over a deterministic grid of inputs
and writes tests/checkin_ref.json. tests/test_wasm_bitexact.js replays the same
grid through the wasm build and requires identical results.
Written with AI assistance (Claude Code), see AI_USE.md."""
import ctypes, json, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lib = ctypes.CDLL(os.path.join(ROOT, "features", "libcrewwatch_feat.so"))

class CI(ctypes.Structure):
    _fields_ = [("Present", ctypes.c_uint16), ("SysMmHg", ctypes.c_uint16), ("DiaMmHg", ctypes.c_uint16),
                ("PulseBpm", ctypes.c_uint16), ("TempX10", ctypes.c_int16), ("GlucoseMgDl", ctypes.c_uint16),
                ("SleepMin", ctypes.c_uint16), ("Mood", ctypes.c_uint8), ("Pad", ctypes.c_uint8)]

class RES(ctypes.Structure):
    _fields_ = [("Bp", ctypes.c_uint8), ("Temp", ctypes.c_uint8), ("Glucose", ctypes.c_uint8), ("Sleep", ctypes.c_uint8),
                ("Mood", ctypes.c_uint8), ("Pulse", ctypes.c_uint8), ("PulseDiffX10", ctypes.c_int16),
                ("Overall", ctypes.c_uint8), ("Pad", ctypes.c_uint8 * 3)]

assert ctypes.sizeof(CI) == 16 and ctypes.sizeof(RES) == 12
lib.CREWWATCH_EvaluateCheckIn.restype = ctypes.c_bool
lib.CREWWATCH_EvaluateCheckIn.argtypes = [ctypes.POINTER(CI), ctypes.c_uint16, ctypes.c_uint16, ctypes.POINTER(RES)]

rnd = random.Random(2026)
cases = []
for i in range(5000):
    c = CI()
    c.Present = rnd.randint(0, 63)
    c.SysMmHg = rnd.randint(40, 320); c.DiaMmHg = rnd.randint(10, 210)
    c.PulseBpm = rnd.randint(10, 260); c.TempX10 = rnd.randint(290, 460)
    c.GlucoseMgDl = rnd.randint(5, 820); c.SleepMin = rnd.randint(0, 1500); c.Mood = rnd.randint(0, 6)
    hr = rnd.choice([0, rnd.randint(300, 2200)]); age = rnd.randint(0, 8)
    r = RES()
    ok = bool(lib.CREWWATCH_EvaluateCheckIn(ctypes.byref(c), hr, age, ctypes.byref(r)))
    cases.append({"in": [c.Present, c.SysMmHg, c.DiaMmHg, c.PulseBpm, c.TempX10, c.GlucoseMgDl, c.SleepMin, c.Mood],
                  "hr": hr, "age": age, "ok": ok,
                  "out": [r.Bp, r.Temp, r.Glucose, r.Sleep, r.Mood, r.Pulse, r.PulseDiffX10, r.Overall] if ok else None})
with open(os.path.join(ROOT, "tests", "checkin_ref.json"), "w") as f:
    json.dump(cases, f, separators=(",", ":"))
print("checkin_ref.json: %d cases, %d accepted" % (len(cases), sum(c["ok"] for c in cases)))
