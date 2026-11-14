"""Local SQLite review decisions with transactional deduplication and an audit history.

Approval records a research decision. It never automatically edits the taxonomy.
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from needstate.config import ROOT

DEFAULT = ROOT / "data/review/queue.sqlite3"

@contextmanager
def _connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, kind TEXT, payload TEXT, status TEXT, note TEXT, dedupe_key TEXT UNIQUE, created_at TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS decisions (id TEXT, status TEXT, note TEXT, decided_at TEXT)")
    try:
        with con:
            yield con
    finally:
        con.close()

def add_item(kind, payload, path=DEFAULT, dedupe_key=None):
    with _connect(path) as con:
        uid = uuid.uuid4().hex[:12]
        con.execute("INSERT OR IGNORE INTO items VALUES (?,?,?,?,?,?,?)", (uid, kind, json.dumps(payload, default=str), "pending", "", dedupe_key, datetime.now(timezone.utc).isoformat()))
        if dedupe_key is not None:
            uid = con.execute("SELECT id FROM items WHERE dedupe_key=?", (dedupe_key,)).fetchone()[0]
        return uid

def list_items(path=DEFAULT, status=None):
    with _connect(path) as con:
        df = pd.read_sql_query("SELECT * FROM items" + (" WHERE status=?" if status else ""), con, params=(status,) if status else ())
    df["payload"] = df["payload"].map(json.loads)
    return df

def decide(item_id, status, note="", path=DEFAULT):
    if status not in {"approved", "rejected", "deferred"}:
        raise ValueError("Invalid decision")
    with _connect(path) as con:
        cursor = con.execute("UPDATE items SET status=?, note=? WHERE id=?", (status, note, item_id))
        if not cursor.rowcount:
            raise ValueError("Review item not found")
        con.execute("INSERT INTO decisions VALUES (?,?,?,?)", (item_id, status, note, datetime.now(timezone.utc).isoformat()))
