from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
import sqlite3
import os

from app.db import connect, DEFAULT_DB_PATH

router = APIRouter(prefix="/v1/world", tags=["world-events"])

DB_PATH = os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


@router.get("/events")
def list_events(limit: int = 200, since_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Returns append-only world-state transition events.
    """
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be 1..1000")

    conn = connect(DB_PATH)
    if not _table_exists(conn, "world_state_events"):
        raise HTTPException(status_code=500, detail="world_state_events table not found (schema not applied)")

    q = (
        "SELECT event_id, from_state, to_state, reason, actor, created_at, trace_id "
        "FROM world_state_events "
    )
    params: List[Any] = []
    if since_id is not None:
        q += "WHERE event_id > ? "
        params.append(since_id)
    q += "ORDER BY event_id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(q, params).fetchall()
    events = []
    for r in rows:
        events.append(
            {
                "event_id": r["event_id"],
                "from_state": r["from_state"],
                "to_state": r["to_state"],
                "reason": r["reason"],
                "actor": r["actor"],
                "created_at": r["created_at"],
                "trace_id": r["trace_id"],
            }
        )

    return {"ok": True, "count": len(events), "events": events}
