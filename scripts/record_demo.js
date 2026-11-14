#!/usr/bin/env node
/* Records docs/crewwatch-demo.mp4 (≤ 30 s) without ffmpeg:
 *   1. starts scripts/record_server.py (serves web/, accepts the upload)
 *   2. opens Chrome full-screen with a THROWAWAY profile and remote debugging
 *   3. clicks "Start recording" through the DevTools protocol (a real user gesture)
 *   4. the page captures its own tab with MediaRecorder, runs the 30-s demo, uploads
 *   5. closes Chrome, deletes the throwaway profile
 *
 *   node --experimental-websocket scripts/record_demo.js "TEDU team"
 *
 * Written with AI assistance (Claude Code), see AI_USE.md.
 */
"use strict";
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 8766, DBG = 9333;
const team = process.argv[2] || "TEDU team";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function json(url) { const r = await fetch(url); return r.json(); }

(async () => {
  for (const ext of ["mp4", "webm"]) {
    const f = path.join(ROOT, "docs", "crewwatch-demo." + ext);
    if (fs.existsSync(f)) fs.unlinkSync(f);
  }
  const server = spawn("python", [path.join(ROOT, "scripts", "record_server.py"), String(PORT)], { stdio: ["ignore", "pipe", "inherit"] });
  let saved = null;
  server.stdout.on("data", d => { process.stdout.write(d); if (/saved/.test(String(d))) saved = String(d); });
  await sleep(800);

  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "cw-rec-"));
  const url = `http://127.0.0.1:${PORT}/index.html?record&team=${encodeURIComponent(team)}`;
  const chrome = spawn(CHROME, [
    `--user-data-dir=${profile}`, `--remote-debugging-port=${DBG}`, "--no-first-run",
    "--no-default-browser-check", "--force-device-scale-factor=1", "--kiosk",
    "--auto-accept-this-tab-capture", "--disable-extensions", url], { stdio: "ignore" });

  let target = null;
  for (let i = 0; i < 50 && !target; i++) {
    await sleep(300);
    try { target = (await json(`http://127.0.0.1:${DBG}/json`)).find(t => t.type === "page" && t.url.includes("index.html")); } catch (e) { /* not up yet */ }
  }
  if (!target) throw new Error("Chrome DevTools target not found");
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener("open", r));
  let id = 0; const pending = new Map();
  ws.addEventListener("message", ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

  await sleep(2500);   // page + data.js + wasm check
  const geo = await send("Runtime.evaluate", { expression:
    "(()=>{const b=document.getElementById('recBtn').getBoundingClientRect();return JSON.stringify({x:b.x+b.width/2,y:b.y+b.height/2,w:innerWidth,h:innerHeight,dpr:devicePixelRatio})})()", returnByValue: true });
  const g = JSON.parse(geo.result.result.value);
  console.log("viewport", g.w + "x" + g.h, "dpr", g.dpr);
  for (const type of ["mousePressed", "mouseReleased"])
    await send("Input.dispatchMouseEvent", { type, x: g.x, y: g.y, button: "left", clickCount: 1 });

  for (let i = 0; i < 90 && !saved; i++) await sleep(500);   // 30 s demo + upload
  try { await send("Browser.close"); } catch (e) { /* closing */ }
  await sleep(1500);
  server.kill();
  try { chrome.kill(); } catch (e) { /* gone */ }
  try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) { /* Chrome may still hold files */ }
  if (!saved) { console.error("FAIL: no recording received"); process.exit(1); }
  console.log("done");
  process.exit(0);
})().catch(e => { console.error(e); process.exit(1); });
