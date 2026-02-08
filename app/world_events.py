from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from app.db import connect, tx, DEFAULT_DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class WorldEventStore:
    """
    Append-only event log with optional hash chaining for tamper evidence.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)
        self._conn: sqlite3.Connection = connect(self.db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS world_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            type TEXT NOT NULL,
            actor TEXT NOT NULL,
            trace_id TEXT,
            payload_json TEXT NOT NULL,
            prev_hash TEXT,
            hash TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_world_events_ts ON world_events(ts);
        CREATE INDEX IF NOT EXISTS idx_world_events_type ON world_events(type);
        CREATE INDEX IF NOT EXISTS idx_world_events_trace ON world_events(trace_id);
        """
        self._conn.executescript(ddl)
        if self._conn.in_transaction:
            self._conn.commit()

    def _compute_hash(self, ts: str, etype: str, actor: str, trace_id: Optional[str], payload_json: str, prev_hash: Optional[str]) -> str:
        h = hashlib.sha256()
        h.update(ts.encode("utf-8"))
        h.update(b"|")
        h.update(etype.encode("utf-8"))
        h.update(b"|")
        h.update(actor.encode("utf-8"))
        h.update(b"|")
        h.update((trace_id or "").encode("utf-8"))
        h.update(b"|")
        h.update((prev_hash or "").encode("utf-8"))
        h.update(b"|")
        h.update(payload_json.encode("utf-8"))
        return h.hexdigest()

    def append(
        self,
        *,
        etype: str,
        actor: str,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = _now_iso()
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        with tx(self._conn) as c:
            prev = c.execute("SELECT hash FROM world_events ORDER BY event_id DESC LIMIT 1").fetchone()
            prev_hash = prev["hash"] if prev else None
            event_hash = self._compute_hash(ts, etype, actor, trace_id, payload_json, prev_hash)

            cur = c.execute(
                "INSERT INTO world_events (ts, type, actor, trace_id, payload_json, prev_hash, hash) "
                "VALUES (?,?,?,?,?,?,?)",
                (ts, etype, actor, trace_id, payload_json, prev_hash, event_hash),
            )
            event_id = cur.lastrowid

        return {
            "event_id": event_id,
            "ts": ts,
            "type": etype,
            "actor": actor,
            "trace_id": trace_id,
            "payload": payload,
            "prev_hash": prev_hash,
            "hash": event_hash,
        }

    def list(self, *, limit: int = 200, since_id: Optional[int] = None, etype: Optional[str] = None) -> Dict[str, Any]:
        if limit < 1 or limit > 2000:
            limit = 200

        q = "SELECT event_id, ts, type, actor, trace_id, payload_json, prev_hash, hash FROM world_events"
        where = []
        params = []

        if since_id is not None:
            where.append("event_id > ?")
            params.append(since_id)
        if etype is not None:
            where.append("type = ?")
            params.append(etype)

        if where:
            q += " WHERE " + " AND ".join(where)

        q += " ORDER BY event_id ASC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(q, params).fetchall()
        events = []
        for r in rows:
            events.append(
                {
                    "event_id": r["event_id"],
                    "ts": r["ts"],
                    "type": r["type"],
                    "actor": r["actor"],
                    "trace_id": r["trace_id"],
                    "payload": json.loads(r["payload_json"]),
                    "prev_hash": r["prev_hash"],
                    "hash": r["hash"],
                }
            )
        return {"ok": True, "count": len(events), "events": events}


STORE = WorldEventStore()


def emit(etype: str, actor: str, payload: Dict[str, Any], trace_id: Optional[str] = None) -> Dict[str, Any]:
    return STORE.append(etype=etype, actor=actor, payload=payload, trace_id=trace_id)
