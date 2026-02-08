from __future__ import annotations

import os
import time
import json
import sqlite3
from typing import Any, Dict, Optional, Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.db import connect, DEFAULT_DB_PATH

router = APIRouter(prefix="/v1/world", tags=["world-events-stream"])

DB_PATH = os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def _sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream(since_id: int, poll_s: float) -> Iterator[str]:
    conn = connect(DB_PATH)
    if not _table_exists(conn, "world_state_events"):
        yield _sse("error", {"ok": False, "error": "world_state_events table not found"})
        return

    last_id = since_id
    yield _sse("hello", {"ok": True, "since_id": since_id})

    while True:
        rows = conn.execute(
            "SELECT event_id, from_state, to_state, reason, actor, created_at, trace_id "
            "FROM world_state_events WHERE event_id > ? ORDER BY event_id ASC LIMIT 200",
            (last_id,),
        ).fetchall()

        for r in rows:
            last_id = int(r["event_id"])
            yield _sse(
                "world_state_event",
                {
                    "event_id": last_id,
                    "from_state": r["from_state"],
                    "to_state": r["to_state"],
                    "reason": r["reason"],
                    "actor": r["actor"],
                    "created_at": r["created_at"],
                    "trace_id": r["trace_id"],
                },
            )

        time.sleep(poll_s)


@router.get("/events/stream")
def events_stream(since_id: int = 0, poll_s: float = 1.0):
    """
    SSE stream of world state transition events.
    """
    return StreamingResponse(_stream(since_id=since_id, poll_s=poll_s), media_type="text/event-stream")
