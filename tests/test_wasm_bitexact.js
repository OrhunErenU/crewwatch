#!/usr/bin/env node
/* Bit-exact test: browser path (flight C -> wasm32, driven by web/crewwatch_engine.js)
 * versus host path (same C via gcc + ctypes, scores stored in web/data.js by
 * web/export_demo.py). Every fast and slow integer score of all 4 crew members
 * must be identical, including warm-up ticks (both null).
 *
 *   node tests/test_wasm_bitexact.js
 *
 * Also checks the embedded base64 copy matches web/wasm/crewwatch.wasm.
 * Written with AI assistance (Claude Code), see AI_USE.md.
 */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const crypto = require("crypto");

const ROOT = path.join(__dirname, "..");
const ctx = { window: {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(ROOT, "web", "data.js"), "utf8"), ctx);
vm.runInContext(fs.readFileSync(path.join(ROOT, "web", "crewwatch_wasm.js"), "utf8"), ctx);
const D = ctx.window.CREWWATCH;
const b64 = ctx.window.CREWWATCH_WASM_B64;
const Engine = require(path.join(ROOT, "web", "crewwatch_engine.js"));

let fails = 0;
const file = fs.readFileSync(path.join(ROOT, "web", "wasm", "crewwatch.wasm"));
const emb = Buffer.from(b64, "base64");
const sameBin = Buffer.compare(file, emb) === 0;
console.log("embedded wasm == web/wasm/crewwatch.wasm : " + (sameBin ? "ok" : "FAIL") +
  "  (" + file.length + " B, sha256 " + crypto.createHash("sha256").update(file).digest("hex").slice(0, 16) + ")");
if (!sameBin) fails++;

if (!D.wasm_model || !D.crew[0].score_fast) {
  console.log("FAIL web/data.js has no wasm_model / host scores -- re-run web/export_demo.py");
  process.exit(1);
}

const eng = Engine.fromBase64(b64);
let total = 0, alarmsHost = 0, alarmsWasm = 0;
for (const c of D.crew) {
  const r = eng.replayCrew(D.wasm_model, c);
  total += r.same + r.diff;
  const thr = D.wasm_model.thresholds;
  for (let i = 0; i < r.fast.length; i++) {
    const h = (c.score_fast[i] !== null && c.score_fast[i] > thr[0]) || (c.score_slow[i] !== null && c.score_slow[i] > thr[1]);
    const w = (r.fast[i] !== null && r.fast[i] > thr[0]) || (r.slow[i] !== null && r.slow[i] > thr[1]);
    alarmsHost += h; alarmsWasm += w;
  }
  const ok = r.diff === 0;
  if (!ok) fails++;
  console.log((ok ? "  ok   " : "  FAIL ") + c.id + ": " + r.same + "/" + (r.same + r.diff) +
    " scores identical" + (ok ? "" : " (first difference at tick " + r.firstDiff + ")"));
}
console.log("alarm ticks host " + alarmsHost + " / wasm " + alarmsWasm);

// non-trivial? count slots where both sides produced a real integer score
let nonNull = 0;
for (const c of D.crew) for (let i = 0; i < c.score_fast.length; i++)
  nonNull += (c.score_fast[i] !== null) + (c.score_slow[i] !== null);
console.log("non-null integer scores compared: " + nonNull);
if (nonNull < 0.9 * total) { console.log("FAIL too many null slots -- test would be trivial"); fails++; }

// negative control: the comparison must notice a 1-LSB change in one feature-table Bias
const c0 = D.crew[0];
const tampered = Object.assign({}, c0, { table: Object.assign({}, c0.table, { bias: c0.table.bias.slice() }) });
tampered.table.bias[0] += 1;
const neg = eng.replayCrew(D.wasm_model, tampered);
const negOk = neg.diff > 0;
console.log((negOk ? "  ok   " : "  FAIL ") + "negative control: Bias[0] + 1 LSB -> " + neg.diff + " scores differ (must be > 0)");
if (!negOk) fails++;
if (alarmsHost !== alarmsWasm) fails++;

// astronaut check-in: same crewwatch_checkin.c, host (gcc) reference vs wasm
const ref = JSON.parse(fs.readFileSync(path.join(ROOT, "tests", "checkin_ref.json"), "utf8"));
let ciSame = 0;
for (const c of ref) {
  const [present, sys, dia, pulse, tempX10, glucose, sleepMin, mood] = c.in;
  const r = eng.checkIn({ present, sys, dia, pulse, tempX10, glucose, sleepMin, mood }, c.hr, c.age);
  const got = r === null ? null : [r.bp, r.temp, r.glucose, r.sleep, r.mood, r.pulse, r.pulseDiffX10, r.overall];
  if (JSON.stringify(got) === JSON.stringify(c.out)) ciSame++;
}
const ciOk = ciSame === ref.length;
console.log((ciOk ? "  ok   " : "  FAIL ") + "check-in: " + ciSame + "/" + ref.length + " results identical (host gcc vs wasm)");
if (!ciOk) fails++;
console.log(fails === 0
  ? "PASS -- browser (wasm32) and host (x86-64 gcc) give bit-identical scores on " + total + " score slots and identical check-in results"
  : "FAIL (" + fails + ")");
process.exit(fails === 0 ? 0 : 1);
