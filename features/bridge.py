"""
CrewWatch feature engine -- host bridge to the FLIGHT C code.

No arithmetic here. Every feature value comes from C:
  RAW / DIFF / AGE : vendor/cfs-m2s150/apps/tlm_watch/fsw/src/tlm_watch_feature.c (unchanged)
  HOLD             : features/crewwatch_hold.c (new, 48 h), scaled via the AGE path above

Tick order mirrors vendor features_ctypes.FeatureEngine (= tlm_watch_latch.c /
tlm_watch_sample.c): packets are latched as they arrive, then on each fixed tick
ages advance, the vector is built, DIFF/HOLD states advance.

Build the .so first:  bash features/build_host.sh   (WSL, gcc)
"""

import ctypes
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUND = os.path.join(ROOT, "vendor", "cfs-m2s150", "apps", "tlm_watch", "ground")
if GROUND not in sys.path:
    sys.path.insert(0, GROUND)

import features_ctypes as FC  # noqa: E402  (vendor: struct layouts + constants only)
import tinyinfer_ctypes as TI  # noqa: E402,F401  (re-exported for callers)

SO = os.path.join(ROOT, "features", "libcrewwatch_feat.so")

TYPE_U16_LE = FC.TYPE_U16_LE
TYPE_I16_LE = FC.TYPE_I16_LE
XFORM_RAW = FC.XFORM_RAW
XFORM_DIFF = FC.XFORM_DIFF
XFORM_AGE = FC.XFORM_AGE
XFORM_HOLD = 4  # CrewWatch-local code; in C it is routed through the AGE scaling

XFORM_NAMES = {XFORM_RAW: "RAW", XFORM_DIFF: "DIFF", XFORM_AGE: "AGE", XFORM_HOLD: "HOLD"}


class CHoldState(ctypes.Structure):
    """CREWWATCH_HoldState_t -- uint32, uint16, bool (+pad) = 8 bytes"""
    _fields_ = [("PrevRaw", ctypes.c_uint32),
                ("HoldTicks", ctypes.c_uint16),
                ("HasPrev", ctypes.c_bool)]


FeatureDef = FC.FeatureDef


class Engine(object):
    def __init__(self, defs, n_sources):
        if not os.path.exists(SO):
            raise RuntimeError("missing %s -- run: bash features/build_host.sh" % SO)
        lib = ctypes.CDLL(SO)
        lib.TLM_WATCH_ExtractRaw.restype = ctypes.c_bool
        lib.TLM_WATCH_ExtractRaw.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_uint32,
            ctypes.c_uint16, ctypes.c_uint8, ctypes.POINTER(ctypes.c_uint32)]
        lib.TLM_WATCH_ApplyTransform.restype = ctypes.c_bool
        lib.TLM_WATCH_ApplyTransform.argtypes = [
            ctypes.POINTER(FC.CFeatureDef), ctypes.c_uint32, ctypes.c_uint16,
            ctypes.POINTER(FC.CFeatState), ctypes.POINTER(ctypes.c_int16)]
        lib.TLM_WATCH_AdvanceState.restype = None
        lib.TLM_WATCH_AdvanceState.argtypes = [ctypes.POINTER(FC.CFeatState), ctypes.c_uint32]
        lib.CREWWATCH_HoldInit.restype = None
        lib.CREWWATCH_HoldInit.argtypes = [ctypes.POINTER(CHoldState)]
        lib.CREWWATCH_HoldAdvance.restype = None
        lib.CREWWATCH_HoldAdvance.argtypes = [ctypes.POINTER(CHoldState), ctypes.c_uint32]
        lib.CREWWATCH_ApplyHold.restype = ctypes.c_bool
        lib.CREWWATCH_ApplyHold.argtypes = [
            ctypes.POINTER(FC.CFeatureDef), ctypes.POINTER(CHoldState), ctypes.POINTER(ctypes.c_int16)]
        if ctypes.sizeof(FC.CFeatureDef) != 20:
            raise RuntimeError("CFeatureDef layout drifted from C")
        if ctypes.sizeof(CHoldState) != 8:
            raise RuntimeError("CHoldState layout drifted from C")
        self.lib = lib

        self.defs = defs
        self.n_sources = n_sources
        self.cdefs = []
        for d in defs:
            c = d.to_c()
            if d.xform == XFORM_HOLD:
                c.Transform = XFORM_AGE  # never read by ApplyHold, keeps table valid
            self.cdefs.append(c)
        self.reset()

    def reset(self):
        n = len(self.defs)
        self.dstate = [FC.CFeatState() for _ in range(n)]
        self.hstate = [CHoldState() for _ in range(n)]
        for h in self.hstate:
            self.lib.CREWWATCH_HoldInit(ctypes.byref(h))
        self.raw = [0] * n
        self.raw_valid = [False] * n
        self.age = [0xFFFF] * self.n_sources  # flight latch starts at max, not 0
        self.updated = [False] * self.n_sources
        self._out = ctypes.c_int16()
        self._rawout = ctypes.c_uint32()

    def latch(self, src, packet):
        buf = (ctypes.c_uint8 * len(packet)).from_buffer_copy(bytes(packet))
        for i, d in enumerate(self.defs):
            if d.src != src or d.xform == XFORM_AGE:
                continue
            if self.lib.TLM_WATCH_ExtractRaw(buf, len(packet), d.offset, d.type, ctypes.byref(self._rawout)):
                self.raw[i] = self._rawout.value
                self.raw_valid[i] = True
        self.updated[src] = True

    def tick(self):
        for s in range(self.n_sources):
            if self.updated[s]:
                self.age[s] = 0
                self.updated[s] = False
            elif self.age[s] < 0xFFFF:
                self.age[s] += 1

        vec = [0] * len(self.defs)
        ok_all = True
        out = self._out
        for i, d in enumerate(self.defs):
            age = self.age[d.src]
            if d.xform == XFORM_AGE:
                ok = self.lib.TLM_WATCH_ApplyTransform(
                    ctypes.byref(self.cdefs[i]), 0, age, ctypes.byref(self.dstate[i]), ctypes.byref(out))
            elif not self.raw_valid[i]:
                ok_all = False
                continue
            elif d.xform == XFORM_HOLD:
                self.lib.CREWWATCH_HoldAdvance(ctypes.byref(self.hstate[i]), self.raw[i])
                ok = self.lib.CREWWATCH_ApplyHold(
                    ctypes.byref(self.cdefs[i]), ctypes.byref(self.hstate[i]), ctypes.byref(out))
            else:
                ok = self.lib.TLM_WATCH_ApplyTransform(
                    ctypes.byref(self.cdefs[i]), self.raw[i], age, ctypes.byref(self.dstate[i]), ctypes.byref(out))
                if d.xform == XFORM_DIFF:
                    self.lib.TLM_WATCH_AdvanceState(ctypes.byref(self.dstate[i]), self.raw[i])
            if ok:
                vec[i] = out.value
            else:
                ok_all = False
        return vec if ok_all else None

    def hold_ticks(self):
        """Unscaled HOLD counters (for the baseline rule and explanations)."""
        return [h.HoldTicks for h in self.hstate]


def selftest():
    """Cross-check the bridge against hand-derived values."""
    import struct
    defs = [FeatureDef(0, 2, TYPE_U16_LE, XFORM_RAW, bias=100, scale=2, shift=0, name="raw"),
            FeatureDef(0, 2, TYPE_U16_LE, XFORM_DIFF, name="diff"),
            FeatureDef(0, 2, TYPE_U16_LE, XFORM_HOLD, name="hold"),
            FeatureDef(0, 0, TYPE_U16_LE, XFORM_AGE, name="age")]
    e = Engine(defs, 1)
    vals = [150, 150, 150, 160, None, None, 170]
    got = []
    for v in vals:
        if v is not None:
            e.latch(0, struct.pack("<HH", 0, v))
        got.append(e.tick())
    exp = [None,               # DIFF warm-up
           [100, 0, 1, 0],
           [100, 0, 2, 0],
           [120, 10, 0, 0],
           [120, 0, 1, 1],     # silent: latched value repeats, AGE grows
           [120, 0, 2, 2],
           [140, 10, 0, 0]]
    fails = [(i, g, x) for i, (g, x) in enumerate(zip(got, exp)) if g != x]
    for f in fails:
        print("  FAIL tick %d: got %s expected %s" % f)
    print("bridge selftest: %d/%d ticks match" % (len(exp) - len(fails), len(exp)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(selftest())
