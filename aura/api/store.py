"""Minimal SQLite document store for the demo build (data/aura.db).

One table of JSON documents keyed by (kind, id), plus insertion order. The relational
schema of A7.2 replaces this in Milestone M2; the API contract does not change.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.RLock()
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=NORMAL")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS docs (kind TEXT NOT NULL, id TEXT NOT NULL, seq INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY (kind, id))"
            )
            self._db.execute("CREATE INDEX IF NOT EXISTS docs_kind_seq ON docs(kind, seq)")
            self._db.commit()

    def put(self, kind: str, id: str, data: dict[str, Any]) -> dict[str, Any]:
        text = json.dumps(data, ensure_ascii=False)
        with self._lock:
            row = self._db.execute("SELECT seq FROM docs WHERE kind=? AND id=?", (kind, id)).fetchone()
            if row:
                self._db.execute("UPDATE docs SET data=? WHERE kind=? AND id=?", (text, kind, id))
            else:
                seq = self._db.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM docs").fetchone()[0]
                self._db.execute("INSERT INTO docs (kind, id, seq, data) VALUES (?, ?, ?, ?)", (kind, id, seq, text))
            self._db.commit()
        return data

    def get(self, kind: str, id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT data FROM docs WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, kind: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute("SELECT data FROM docs WHERE kind=? ORDER BY seq", (kind,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def count(self, kind: str) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM docs WHERE kind=?", (kind,)).fetchone()[0]
