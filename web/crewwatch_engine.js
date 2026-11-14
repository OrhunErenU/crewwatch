/* CrewWatch in the browser: thin JS driver around crewwatch.wasm.
 *
 * No arithmetic here (project rule: no second implementation). The wasm module is the flight C code:
 * tlm_watch_feature.c, tlm_watch_window.c, crewwatch_hold.c, tinyinfer.
 * JS only packs packets (little-endian, same layout as sim/crew.py) and
 * copies numbers in and out of wasm memory.
 *
 * Works in the browser (window.CrewWatchEngine) and in node (module.exports).
 * Written with AI assistance (Claude Code), see AI_USE.md.
 */
(function (root) {
  "use strict";

  function b64ToBytes(b64) {
    if (typeof atob === "function") {
      const s = atob(b64), out = new Uint8Array(s.length);
      for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
      return out;
    }
    return new Uint8Array(Buffer.from(b64, "base64"));
  }

  function Engine(wasmBytes) {
    const inst = new WebAssembly.Instance(new WebAssembly.Module(wasmBytes), {});
    this.x = inst.exports;
    if (this.x._initialize) this.x._initialize();
    if (this.x.CW_DefSize() !== 20) throw new Error("TLM_WATCH_FeatureDef_t layout drifted (wasm says " + this.x.CW_DefSize() + ")");
  }

  Engine.fromBase64 = function (b64) { return new Engine(b64ToBytes(b64)); };

  Engine.prototype.mem = function () { return this.x.memory.buffer; };

  /* model = data.js wasm_model; table = crew.table {bias, scale, shift} */
  Engine.prototype.configure = function (model, table) {
    const x = this.x, F = model.features.length;
    this.F = F;
    this.model = model;
    let dv = new DataView(this.mem(), x.CW_Defs(), 20 * F);
    const xf = new Uint8Array(this.mem(), x.CW_Xforms(), F);
    model.features.forEach((f, i) => {
      const o = 20 * i;
      for (let k = 0; k < 20; k++) dv.setUint8(o + k, 0);
      dv.setUint16(o + 0, f.src, true);
      dv.setUint16(o + 2, f.offset, true);
      dv.setUint8(o + 4, f.type);
      dv.setUint8(o + 5, f.xform === 4 ? 3 : f.xform);
      dv.setInt32(o + 8, table.bias[i], true);
      dv.setInt32(o + 12, table.scale[i], true);
      dv.setInt8(o + 16, table.shift[i]);
      xf[i] = f.xform;
    });
    model.models.forEach((m, k) => {
      new Int8Array(this.mem(), x.CW_WEnc(k), m.w_enc.length).set(m.w_enc);
      new Int8Array(this.mem(), x.CW_WDec(k), m.w_dec.length).set(m.w_dec);
      x.CW_SetModel(k, m.mult_enc, m.shift_enc, m.mult_dec, m.shift_dec);
    });
    if (!x.CW_Init(F, model.n_sources)) throw new Error("CW_Init rejected the feature table");
    this.seq = new Array(model.n_sources).fill(0);
  };

  function pack(dv, fmt, values) {
    // supports "<" + H (u16) / h (i16) only -- all CrewWatch packets
    let o = 0;
    for (let i = 1; i < fmt.length; i++) {
      const v = values[i - 1];
      if (fmt[i] === "H") dv.setUint16(o, v, true);
      else if (fmt[i] === "h") dv.setInt16(o, v, true);
      else throw new Error("unsupported packet field " + fmt[i]);
      o += 2;
    }
    return o;
  }

  /* One tick. arrived = bitmask of sources whose packet arrived; get(ch) -> raw channel value.
   * Returns {valid, fast, slow, vec, wmean} with integer scores straight from tinyinfer. */
  Engine.prototype.tick = function (arrived, get) {
    const x = this.x, F = this.F;
    for (let s = 0; s < this.model.n_sources; s++) {
      if (!(arrived & (1 << s))) continue;
      const p = this.model.packets[s];
      this.seq[s] = (this.seq[s] + 1) & 0xFFFF;
      const vals = [this.seq[s]].concat(p.channels.map(get));
      const n = pack(new DataView(this.mem(), x.CW_PktBuf(), 64), p.fmt, vals);
      x.CW_Latch(s, n);
    }
    const valid = x.CW_Tick() === 1;
    const out = { valid: valid, fast: null, slow: null };
    if (valid) {
      out.fast = x.CW_Score(0, x.CW_Vec());
      if (x.CW_WMeanValid()) out.slow = x.CW_Score(1, x.CW_WMean());
    }
    return out;
  };

  /* Replay one crew member from data.js and compare with the host scores. */
  Engine.prototype.replayCrew = function (model, crew) {
    this.configure(model, crew.table);
    const n = crew.arrive.length;
    const fast = new Array(n), slow = new Array(n);
    let same = 0, diff = 0, firstDiff = -1;
    for (let i = 0; i < n; i++) {
      const r = this.tick(crew.arrive[i], ch => crew.series[ch][i]);
      fast[i] = r.fast; slow[i] = r.slow;
      for (const [a, b] of [[r.fast, crew.score_fast[i]], [r.slow, crew.score_slow[i]]]) {
        if (a === b) same++; else { diff++; if (firstDiff < 0) firstDiff = i; }
      }
    }
    return { fast: fast, slow: slow, same: same, diff: diff, firstDiff: firstDiff };
  };

  if (typeof module !== "undefined" && module.exports) module.exports = Engine;
  else root.CrewWatchEngine = Engine;
})(typeof window !== "undefined" ? window : globalThis);
