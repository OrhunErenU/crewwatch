#!/usr/bin/env python3
"""
Fetch NASA DONKI Solar Energetic Particle (SEP) events, 60-day windows
(the API refuses longer ranges), and store them unmodified plus a compact list.

Source: NASA CCMC DONKI, https://ccmc.gsfc.nasa.gov/DONKI-API/get/SEP (no key).

    python3 sim/fetch_donki.py --start 2024-01-01 --end 2026-11-14
Written with AI assistance (Claude Code), see AI_USE.md.
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

API = "https://ccmc.gsfc.nasa.gov/DONKI-API/get/SEP?startDate=%s&endDate=%s"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=dt.date.today().isoformat())
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "nasa"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    s = dt.date.fromisoformat(a.start)
    e = dt.date.fromisoformat(a.end)
    events = {}
    while s <= e:
        w_end = min(s + dt.timedelta(days=59), e)
        url = API % (s.isoformat(), w_end.isoformat())
        with urllib.request.urlopen(url, timeout=60) as r:
            body = r.read().decode("utf-8").strip()
        chunk = json.loads(body) if body else []
        for ev in chunk:
            events[ev["sepID"]] = ev
        print("%s .. %s : %d events" % (s, w_end, len(chunk)), file=sys.stderr)
        s = w_end + dt.timedelta(days=1)

    raw = sorted(events.values(), key=lambda v: v["eventTime"])
    with open(os.path.join(a.out, "donki_sep_raw.json"), "w") as f:
        json.dump({"source": "NASA CCMC DONKI SEP API", "url": API % (a.start, a.end),
                   "fetched": dt.datetime.now(dt.timezone.utc).isoformat(), "events": raw}, f, indent=1)
    compact = [{"id": v["sepID"], "time": v["eventTime"],
                "instruments": [i.get("displayName", "") for i in v.get("instruments", [])],
                "link": v.get("link", "")} for v in raw]
    with open(os.path.join(a.out, "donki_sep.json"), "w") as f:
        json.dump(compact, f, indent=1)
    print("%d unique SEP events -> data/nasa/donki_sep.json" % len(compact))
    return 0


if __name__ == "__main__":
    sys.exit(main())
