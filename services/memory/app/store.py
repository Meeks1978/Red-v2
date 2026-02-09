import json
from datetime import datetime, timezone
from typing import Any
from .db import connect
from .models import MemoryItem, MemoryPut, MemoryQuery, WorldStateGet, WorldStatePut
from .policy import enforce_phase5_policy

def put_memory(item: MemoryPut) -> MemoryItem:
    enforce_phase5_policy(item)

    mem_id = MemoryItem.new_id()
    created_at = datetime.now(timezone.utc)

    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO memory_items
            (id, scope, kind, key, text, data, source, confidence, created_at,
             ttl_seconds, trace_id, approval_ref, tags, refs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mem_id,
                item.scope,
                item.kind,
                item.key,
                item.text,
                json.dumps(item.data) if item.data else None,
                item.source,
                item.confidence,
                created_at.isoformat(),
                item.ttl_seconds,
                item.trace_id,
                item.approval_ref,
                json.dumps(item.tags),
                json.dumps(item.refs),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return MemoryItem(**item.model_dump(), id=mem_id, created_at=created_at)

def query_memory(q: MemoryQuery) -> list[dict[str, Any]]:
    conn = connect()
    try:
        clauses = []
        params: list[Any] = []

        if q.scope:
            clauses.append("scope = ?"); params.append(q.scope)
        if q.kind:
            clauses.append("kind = ?"); params.append(q.kind)
        if q.key:
            clauses.append("key = ?"); params.append(q.key)
        if q.text_contains:
            clauses.append("text LIKE ?"); params.append(f"%{q.text_contains}%")
        if q.tag:
            clauses.append("tags LIKE ?"); params.append(f"%{q.tag}%")

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        sql = f"""
            SELECT * FROM memory_items
            {where}
            ORDER BY datetime(created_at) DESC
            LIMIT ?
        """
        params.append(q.limit)

        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def world_state_set(w: WorldStatePut) -> None:
    conn = connect()
    try:
        conn.execute(
            "UPDATE world_state SET state_json=?, updated_at=?, trace_id=? WHERE id=1",
            (json.dumps(w.state), datetime.now(timezone.utc).isoformat(), w.trace_id),
        )
        conn.commit()
    finally:
        conn.close()

def world_state_get() -> WorldStateGet:
    conn = connect()
    try:
        r = conn.execute("SELECT * FROM world_state WHERE id=1").fetchone()
        return WorldStateGet(
            state=json.loads(r["state_json"]),
            updated_at=datetime.fromisoformat(r["updated_at"]),
            trace_id=r["trace_id"],
        )
    finally:
        conn.close()
