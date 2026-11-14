"""Loopback-only web application. Receipts live in memory for the current server session."""
import argparse
import json
import logging
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import pandas as pd

from needstate.workspace import analyse_lines, combine, config, workbook, to_canonical

ASSETS = Path(__file__).with_name("web")
LIMIT = 16 * 1024**2


def demo(cfg):
    products = ["ARIEL WASHING LIQUID", "LENOR FAB COND", "HOVIS BREAD", "QUAKER OATS", "COLGATE TOOTHPASTE"]
    rows = []
    for buyer in range(8):
        for trip in range(8):
            items = [2, 3] + ([0, 1] if (buyer + trip) % 3 == 0 or buyer % 2 and trip >= 4 else []) + ([4] if trip < 4 else [])
            for i, p in enumerate(items):
                rows.append({"Receipt ID": f"D{buyer}-{trip}", "Consumer ID": f"Demo {buyer+1:02}",
                             "Product Name": products[p], "Date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=trip*7),
                             "Quantity": 1, "Unit Price": 2, "Line Total": 2, "Line Number": i+1})
    return to_canonical(pd.DataFrame(rows), cfg.mapping)


class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.lines = self.report = None
        self.sample = False
        self.state = {"phase": "empty"}
        self.token = secrets.token_urlsafe(32)

    def start(self, data):
        with self.lock:
            if self.state["phase"] == "working":
                return False
            self.state = {"phase":"working"}
        threading.Thread(target=self.run, args=(data,), daemon=True).start()
        return True

    def run(self, data):
        try:
            cfg = config()
            if data is None:
                if self.lines is not None and not self.sample:
                    raise ValueError("Your imports are open. Restart the workspace to explore the example separately.")
                new, skipped, duplicates = demo(cfg), 0, 0
            else:
                incoming, skipped = workbook(data, cfg.mapping)
                new, duplicates = combine(None if self.sample else self.lines, incoming)
            report = analyse_lines(new, cfg)
            with self.lock:
                self.report, self.lines, self.sample = report, new, data is None
                self.state = dict(phase="ready", skipped=skipped, duplicates=duplicates, sample=self.sample)
        except Exception as exc:
            if not isinstance(exc, ValueError):
                logging.exception("Import failed")
            with self.lock:
                self.state = dict(phase="error", error=str(exc) if isinstance(exc, ValueError) else "Could not read this workbook. Check the file and try again.", previous=self.report is not None)


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, mime="application/json"):
        if mime == "application/json":
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; object-src 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.local(): return self.send(403, {})
        url = urlsplit(self.path)
        assets = {"/":("index.html","text/html; charset=utf-8"),"/app.js":("app.js","text/javascript"),"/style.css":("style.css","text/css")}
        if url.path in assets:
            name,mime = assets[url.path]
            return self.send(200,(ASSETS/name).read_bytes(),mime)
        store = self.server.store
        with store.lock:
            r = store.report
            if url.path == "/api/state":
                return self.send(200,dict(store.state, token=store.token, available=r is not None, sample=store.sample))
            if r and url.path == "/api/findings":
                return self.send(200,dict({k:v for k,v in r.items() if k not in ("receipts","findings")},findings=[
                    {k:v for k,v in f.items() if k!="customers"} for f in r["findings"]]))
            if r and url.path == "/api/evidence":
                q = parse_qs(url.query)
                try:
                    i = int(q["finding"][0])
                    if i < 0: raise ValueError
                    customers = r["findings"][i]["customers"]
                    if "buyer" not in q: return self.send(200,[c["id"] for c in customers])
                    j = int(q["buyer"][0])
                    if j < 0: raise ValueError
                    c = customers[j]
                    return self.send(200,dict(c, receipts=[r["receipts"][tid] for tid in c["receipts"]]))
                except (IndexError, ValueError, KeyError):
                    return self.send(400,{"error":"Unknown finding or buyer."})
        self.send(404,{})

    def do_POST(self):
        store = self.server.store
        if not self.local() or self.headers.get("X-Workspace") != store.token: return self.send(403,{})
        if self.path not in ("/api/import","/api/sample"): return self.send(404,{})
        try: size = int(self.headers.get("Content-Length","0"))
        except ValueError: return self.send(400,{})
        if not 0 <= size <= LIMIT: return self.send(413,{"error":"Choose a workbook smaller than 16 MB."})
        if self.path == "/api/import" and not size: return self.send(400,{"error":"Choose a workbook first."})
        if not store.start(self.rfile.read(size) if self.path == "/api/import" else None):
            return self.send(409,{"error":"An import is already running."})
        self.send(202,{"phase":"working"})


def server(port):
    http = ThreadingHTTPServer(("127.0.0.1",port),Handler)
    http.store = Store()
    return http


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--open",action="store_true")
    args = parser.parse_args()
    http = server(args.port)
    url = f"http://127.0.0.1:{http.server_port}"
    print(url, flush=True)
    if args.open: webbrowser.open(url)
    http.serve_forever()
