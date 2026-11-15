"""Loopback-only web application. Receipts live in memory for the current server session."""
import argparse
import copy
import hashlib
import json
import logging
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import pandas as pd


from needstate.workspace import analyse_lines, config, workbook, to_canonical
from needstate.workspace import combine
from needstate.uploads import stage, review, prepare_commit, build_report, describe, possible_duplicates, save_review

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
        self.collection = self.collection_report = self.batch = None
        self.sources = {}
        self.ocr_cache = {}
        self.collection_config = None
        self.scope = 'example'

    def task(self, action):
        with self.lock:
            if self.state['phase'] == 'working':
                return False
            self.state = dict(phase='working', stage='Preparing your upload')
        def work():
            try:
                action()
                with self.lock:
                    self.state = dict(phase='ready')
            except Exception as exc:
                logging.exception('Upload failed')
                with self.lock:
                    self.state = dict(phase='error', error=str(exc) if isinstance(exc, ValueError)
                                      else 'Could not process this upload. Your collection is unchanged.',
                                      previous=self.report is not None)
        threading.Thread(target=work, daemon=True).start()
        return True

    def upload(self, data, filename, kind, consumer=None):
        if kind == 'photo' and hashlib.sha256(data).hexdigest() in self.sources:
            raise ValueError('This photo has already been added to your data.')
        with self.lock:
            self.state = dict(phase='working', stage='Reading receipt locally; the first image may take a minute' if kind == 'photo' else 'Checking workbook rows')
        batch = stage(data, filename, kind, config(), ocr_cache=self.ocr_cache)
        if kind == 'photo' and consumer:
            batch['consumer'] = consumer.strip()
        with self.lock:
            self.batch = batch

    def commit(self, payload):
        batch = self.batch
        if not batch or payload.get('batch_id') != batch['id']:
            raise ValueError('This review has expired. Open the current upload again.')
        mode = payload.get('mode')
        if mode not in ('append', 'focus'):
            raise ValueError('Choose Add to my data or Focus on this upload.')
        if batch['accepted'] and mode == 'append':
            return
        cfg = config()
        lines = prepare_commit(batch, payload, cfg)
        currency = batch['receipt'].currency if batch['kind'] == 'photo' else payload.get('currency')
        currency = str(currency or '').strip().upper()
        if currency and (len(currency) != 3 or not currency.isalpha()):
            raise ValueError('Use a three-letter currency code such as GBP, or leave currency unknown.')
        batch['currency'] = currency or None
        duplicates = 0
        if mode == 'append':
            similar = possible_duplicates(self.collection, lines)
            if similar and not payload.get('keep_similar'):
                raise ValueError('Possible duplicate: matching products and amounts on the same date already exist. Review the receipt, then confirm Keep matching receipts as separate purchases if these are different trips.')
            lines, duplicates = combine(self.collection, lines)
        def progress(message):
            with self.lock:
                self.state = dict(phase='working', stage=message)
        config_key = hashlib.sha256(repr(cfg).encode()).hexdigest()
        cache_key = (batch['revision'], config_key)
        cached = batch.get('analysis_cache')
        if mode == 'append' and self.collection is not None and len(lines) == len(self.collection) and self.collection_config == config_key:
            # combine() already verified every overlapping receipt is identical.
            report = dict(self.collection_report)
        elif (mode == 'focus' or self.collection is None) and cached and cached[0] == cache_key:
            report = dict(cached[1])
        else:
            report = build_report(lines, cfg, progress)
            if mode == 'focus' or self.collection is None:
                batch['analysis_cache'] = (cache_key, report)
            report = dict(report)
        report.pop('spending_unavailable', None)
        report.pop('currency', None)
        currencies = {batch['currency']}
        if mode == 'append':
            currencies.update(source.get('currency') for source in self.sources.values())
        if None in currencies or len(currencies) > 1:
            report['spending_unavailable'] = 'Spending comparisons are unavailable because the selected data has unknown or different currencies. Purchase patterns and shopper histories remain available.'
        else:
            report['currency'] = next(iter(currencies))
        report['version'] = secrets.token_hex(8)
        with self.lock:
            self.lines, self.report, self.sample = lines, report, False
            self.scope = 'collection' if mode == 'append' else batch['filename']
            if mode == 'append':
                self.collection, self.collection_report = lines, report
                self.collection_config = config_key
                batch['accepted'] = True
                # Retain source evidence, not another copy of the entire analysis
                # or workbook frame for every imported file.
                self.sources[batch['digest']] = copy.deepcopy({k:v for k,v in batch.items() if k not in ('analysis_cache', 'lines')})
            report['import_duplicates'] = duplicates

    def start(self, data):
        with self.lock:
            if self.state["phase"] == "working":
                return False
            self.state = {"phase":"working"}
        threading.Thread(target=self.run, args=(data,), daemon=True).start()
        return True

    def run(self, data):
        try:
            def progress(message):
                with self.lock:
                    self.state = dict(phase='working', stage=message)
            progress('Reading workbook')
            cfg = config()
            if data is None:
                new, skipped, duplicates = demo(cfg), 0, 0
            else:
                new, skipped = workbook(data, cfg.mapping)
                duplicates = 0
            report = analyse_lines(new, cfg, progress=progress)
            report['version'] = secrets.token_hex(8)
            with self.lock:
                self.report, self.lines, self.sample = report, new, data is None
                self.scope = 'example' if data is None else 'Legacy workbook'
                self.state = dict(phase="ready", skipped=skipped, duplicates=duplicates, sample=self.sample)
        except Exception as exc:
            if not isinstance(exc, ValueError):
                logging.exception("Import failed")
            with self.lock:
                self.state = dict(phase="error", error=str(exc) if isinstance(exc, ValueError) else "Could not read this workbook. Check the file and try again.", previous=self.report is not None)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

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
        for offset in range(0, len(body), 16384):
            self.wfile.write(body[offset:offset + 16384])
        self.wfile.flush()

    def local(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def do_GET(self):
        if not self.local(): return self.send(403, {})
        url = urlsplit(self.path)
        if url.path == '/imports.js':
            return self.send(200, (ASSETS/'imports.js').read_bytes(), 'text/javascript')
        assets = {"/":("index.html","text/html; charset=utf-8"),"/business.js":("business.js","text/javascript"),"/goals.js":("goals.js","text/javascript"),"/app.js":("app.js","text/javascript"),"/style.css":("style.css","text/css")}
        if url.path in assets:
            name,mime = assets[url.path]
            return self.send(200,(ASSETS/name).read_bytes(),mime)
        store = self.server.store
        with store.lock:
            r = store.report
            if url.path == "/api/state":
                return self.send(200,dict(store.state, token=store.token, available=r is not None, sample=store.sample, version=r.get('version') if r else None, scope=store.scope, collection=describe(store.collection) if store.collection is not None else None))
            if url.path == '/api/batch':
                result = review(store.batch) if store.batch else None
                if result is not None:
                    result['shoppers'] = sorted(store.collection.customer_id.dropna().astype(str).unique().tolist()) if store.collection is not None else []
                return self.send(200, result)
            if url.path == '/api/export':
                batch = store.batch
                if not batch or batch['kind'] != 'photo' or 'lines' not in batch or parse_qs(url.query).get('batch', [''])[0] != batch['id']:
                    return self.send(400, {'error':'First review and analyse this receipt.'})
                from needstate_receipt_ingestion.export import excel_bytes
                return self.send(200, excel_bytes(batch['receipt'], batch['consumer'], batch['receipt_id'], batch['filename']),
                                 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            if url.path == '/api/preview' and store.batch and store.batch['kind'] == 'photo':
                import base64
                requested = parse_qs(url.query).get('batch', [store.batch['id']])[0]
                if requested != store.batch['id']:
                    return self.send(404, {})
                try:
                    page = int(parse_qs(url.query).get('page', ['0'])[0])
                    if page < 0: raise ValueError()
                    data = store.batch['pages'][page]
                except (ValueError, IndexError): return self.send(404, {})
                return self.send(200, base64.b64decode(data.split(',', 1)[1]), 'image/jpeg')
            if r and url.path == "/api/spending":
                return self.send(200,r["spending"])
            if r and url.path == "/api/findings":
                return self.send(200,dict({k:v for k,v in r.items() if k not in ("receipts","findings","spending")},findings=[
                    {k:v for k,v in f.items() if k!="customers"} for f in r["findings"]]))
            if r and url.path == "/api/evidence":
                q = parse_qs(url.query)
                if q.get('version', [r['version']])[0] != r['version']:
                    return self.send(409, {'error':'The selected data changed. Reopen the finding to view its evidence.'})
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
        if self.path == '/api/customer-id':
            try:
                from needstate_receipt_ingestion.export import new_id
            except ImportError:
                return self.send(503, {'error':'Install the OCR extra to use receipt-photo import.'})
            return self.send(200, {'id':new_id('C')})
        if self.path not in ("/api/import","/api/sample", '/api/stage', '/api/commit', '/api/collection', '/api/review'): return self.send(404,{})
        try: size = int(self.headers.get("Content-Length","0"))
        except ValueError: return self.send(400,{})
        if not 0 <= size <= LIMIT: return self.send(413,{"error":"Choose a workbook smaller than 16 MB."})
        if self.path == '/api/collection':
            with store.lock:
                if store.state['phase'] == 'working': return self.send(409, {'error':'Wait for the current import to finish.'})
                if store.collection is None: return self.send(400, {'error':'No collection yet.'})
                store.lines, store.report = store.collection, store.collection_report
                store.scope, store.sample = 'collection', False
            return self.send(200, {})
        if self.path in ('/api/stage', '/api/commit', '/api/review'):
            data = self.rfile.read(size)
            if self.path == '/api/stage':
                from urllib.parse import unquote
                filename = unquote(self.headers.get('X-Filename', 'upload'))
                kind = self.headers.get('X-Upload-Type', 'spreadsheet')
                consumer = unquote(self.headers.get('X-Customer-Id', ''))
                action = lambda: store.upload(data, filename, kind, consumer)
            else:
                try: payload = json.loads(data)
                except ValueError: return self.send(400, {'error':'Invalid review data.'})
                if not isinstance(payload, dict): return self.send(400, {'error':'Invalid review data.'})
                if self.path == '/api/review':
                    def action():
                        if not store.batch or payload.get('batch_id') != store.batch['id']:
                            raise ValueError('This review has expired.')
                        with store.lock:
                            save_review(store.batch, payload)
                else:
                    action = lambda: store.commit(payload)
            if not store.task(action): return self.send(409, {'error':'An import is already running.'})
            return self.send(202, {})
        if self.path == "/api/import" and not size: return self.send(400,{"error":"Choose a workbook first."})
        if self.path == "/api/import" and self.headers.get("X-Data-Scope") != "synthetic":
            return self.send(400,{"error":"Confirm that this workbook contains synthetic receipts, not real personal data."})
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
