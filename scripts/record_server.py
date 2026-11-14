#!/usr/bin/env python3
"""Serves web/ on 127.0.0.1 and saves one POSTed recording to docs/.
Used only to capture the demo video (web/index.html?demo&record).
Written with AI assistance (Claude Code), see AI_USE.md."""
import http.server, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB, OUT = os.path.join(ROOT, "web"), os.path.join(ROOT, "docs")

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)
    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404); return
        n = int(self.headers.get("Content-Length", 0))
        ctype = self.headers.get("Content-Type", "")
        ext = "mp4" if "mp4" in ctype else "webm"
        path = os.path.join(OUT, "crewwatch-demo." + ext)
        with open(path, "wb") as f:
            f.write(self.rfile.read(n))
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        print("saved %s (%d bytes, %s)" % (path, n, ctype), flush=True)
    def log_message(self, *a):
        pass

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
