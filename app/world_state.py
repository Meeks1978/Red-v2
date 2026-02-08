from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .db import connect, tx, DEFAULT_DB_PATH

STATE_ROW_ID = 1


class WorldState(str, Enum):
    DISARMED = "DISARMED"
    ARMED_IDLE = "ARMED_IDLE"
    ARMED_ACTIVE = "ARMED_ACTIVE"
    FROZEN = "FROZEN"
    ENDED = "ENDED"


TERMINAL = {WorldState.ENDED}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class WorldStateSnapshot:
    state: WorldState
    reason: str
    updated_at: str
    updated_by: str


class WorldStateStore:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)
        self._conn: sqlite3.Connection = connect(self.db_path)
        self._lock = threading.RLock()
        self._ensure_schema()
        self._ensure_initialized()

    def _ensure_schema(self) -> None:
        schema_path = os.getenv(
            "RED_SCHEMA_PATH",
            os.path.join(os.path.dirname(__file__), "schema.sql"),
        )
        with open(schema_path, "r", encoding="utf-8") as f:
            ddl = f.read()

        with self._lock:
            self._conn.executescript(ddl)
            if self._conn.in_transaction:
                self._conn.commit()

    def _ensure_initialized(self) -> None:
        with self._lock:
            row = self._conn.execute(
                "SELECT state, reason, updated_at, updated_by FROM world_state_current WHERE id=?",
                (STATE_ROW_ID,),
            ).fetchone()

            if row is None:
                now = utc_now_iso()
                with tx(self._conn) as c:
                    c.execute(
                        "INSERT INTO world_state_current "
                        "(id, state, reason, updated_at, updated_by) "
                        "VALUES (?,?,?,?,?)",
                        (STATE_ROW_ID, WorldState.DISARMED.value, "boot default", now, "system"),
                    )
                    c.execute(
                        "INSERT INTO world_state_events "
                        "(from_state, to_state, reason, actor, created_at, trace_id) "
                        "VALUES (?,?,?,?,?,?)",
                        (WorldState.DISARMED.value, WorldState.DISARMED.value,
                         "boot default", "system", now, None),
                    )

    def get(self) -> WorldStateSnapshot:
        with self._lock:
            row = self._conn.execute(
                "SELECT state, reason, updated_at, updated_by "
                "FROM world_state_current WHERE id=?",
                (STATE_ROW_ID,),
            ).fetchone()
            return WorldStateSnapshot(
                state=WorldState(row["state"]),
                reason=row["reason"] or "",
                updated_at=row["updated_at"],
                updated_by=row["updated_by"] or "system",
            )

    def can_execute(self) -> tuple[bool, str]:
        snap = self.get()
        if snap.state in {WorldState.DISARMED, WorldState.FROZEN, WorldState.ENDED}:
            return False, f"execution blocked: state={snap.state.value} reason={snap.reason}"
        return True, f"execution allowed: state={snap.state.value}"

    def set_state(
        self,
        new_state: WorldState,
        *,
        reason: str,
        actor: str = "system",
        trace_id: Optional[str] = None,
        allow_terminal_override: bool = False,
    ) -> WorldStateSnapshot:
        if not isinstance(new_state, WorldState):
            new_state = WorldState(str(new_state))

        reason = (reason or "").strip() or "no reason provided"

        with self._lock:
            cur = self.get()

            if cur.state in TERMINAL and not allow_terminal_override:
                return cur

            now = utc_now_iso()

            with tx(self._conn) as c:
                c.execute(
                    "UPDATE world_state_current "
                    "SET state=?, reason=?, updated_at=?, updated_by=? "
                    "WHERE id=?",
                    (new_state.value, reason, now, actor, STATE_ROW_ID),
                )
                c.execute(
                    "INSERT INTO world_state_events "
                    "(from_state, to_state, reason, actor, created_at, trace_id) "
                    "VALUES (?,?,?,?,?,?)",
                    (cur.state.value, new_state.value, reason, actor, now, trace_id),
                )

            return self.get()

# ---- Convenience wrappers expected by execute_api.py ----
# These provide a stable functional API over the WorldStateStore.

try:
    _STATE_STORE  # type: ignore
except NameError:
    _STATE_STORE = WorldStateStore()

def can_execute():
    """
    Returns (ok: bool, reason: str)
    Used by /v1/execute as a hard gate.
    """
    return _STATE_STORE.can_execute()

def get_state():
    """
    Returns WorldStateSnapshot
    """
    return _STATE_STORE.get()
