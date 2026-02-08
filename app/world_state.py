from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Set, Tuple

from app.db import connect, tx, DEFAULT_DB_PATH

STATE_ROW_ID = 1


class WorldState(str, Enum):
    DISARMED = "DISARMED"
    ARMED_IDLE = "ARMED_IDLE"
    ARMED_ACTIVE = "ARMED_ACTIVE"
    FROZEN = "FROZEN"
    ENDED = "ENDED"


TERMINAL: Set[WorldState] = {WorldState.ENDED}

# Allowed transitions (World Engine 1)
ALLOWED_TRANSITIONS: Dict[WorldState, Set[WorldState]] = {
    WorldState.DISARMED: {WorldState.ARMED_IDLE, WorldState.FROZEN, WorldState.ENDED},
    WorldState.ARMED_IDLE: {WorldState.ARMED_ACTIVE, WorldState.DISARMED, WorldState.FROZEN, WorldState.ENDED},
    WorldState.ARMED_ACTIVE: {WorldState.ARMED_IDLE, WorldState.DISARMED, WorldState.FROZEN, WorldState.ENDED},
    # FROZEN is a hard stop. You must explicitly DISARM (or END) to exit.
    WorldState.FROZEN: {WorldState.DISARMED, WorldState.ENDED},
    WorldState.ENDED: set(),
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class WorldStateSnapshot:
    state: WorldState
    reason: str
    updated_at: str
    updated_by: str


class WorldStateStore:
    """
    World Engine v1:
      - persistent state with a strict transition table
      - append-only transition events (if schema has events table)
      - DISARMED-by-default
      - FROZEN is a hard stop
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)
        self._conn: sqlite3.Connection = connect(self.db_path)
        self._lock = threading.RLock()
        self._ensure_schema()
        self._ensure_initialized()

    def _ensure_schema(self) -> None:
        schema_path = os.getenv("RED_SCHEMA_PATH", os.path.join(os.path.dirname(__file__), "schema.sql"))
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
                        "INSERT INTO world_state_current (id, state, reason, updated_at, updated_by) VALUES (?,?,?,?,?)",
                        (STATE_ROW_ID, WorldState.DISARMED.value, "boot default", now, "system"),
                    )
                    # event log is optional; ignore if table doesn't exist
                    try:
                        c.execute(
                            "INSERT INTO world_state_events (from_state, to_state, reason, actor, created_at, trace_id) "
                            "VALUES (?,?,?,?,?,?)",
                            (WorldState.DISARMED.value, WorldState.DISARMED.value, "boot default", "system", now, None),
                        )
                    except Exception:
                        pass

    def get(self) -> WorldStateSnapshot:
        with self._lock:
            row = self._conn.execute(
                "SELECT state, reason, updated_at, updated_by FROM world_state_current WHERE id=?",
                (STATE_ROW_ID,),
            ).fetchone()
            if row is None:
                # should not happen
                return WorldStateSnapshot(WorldState.DISARMED, "uninitialized", utc_now_iso(), "system")
            return WorldStateSnapshot(
                state=WorldState(row["state"]),
                reason=row["reason"] or "",
                updated_at=row["updated_at"],
                updated_by=row["updated_by"] or "system",
            )

    def can_execute(self) -> Tuple[bool, str]:
        """
        Hard gate used by /v1/execute.
        Only ARMED_IDLE and ARMED_ACTIVE allow execution.
        """
        snap = self.get()
        if snap.state in {WorldState.ARMED_IDLE, WorldState.ARMED_ACTIVE}:
            return True, f"execution allowed: state={snap.state.value}"
        return False, f"execution blocked: state={snap.state.value} reason={snap.reason}"

    def set_state(
        self,
        new_state: WorldState,
        *,
        reason: str,
        actor: str = "system",
        trace_id: Optional[str] = None,
        allow_terminal_override: bool = False,
        allow_illegal_transition: bool = False,
    ) -> WorldStateSnapshot:
        """
        Transition with strict enforcement.
        - ENDED is terminal unless allow_terminal_override=True
        - transitions must be allowed by ALLOWED_TRANSITIONS unless allow_illegal_transition=True
        """
        if not isinstance(new_state, WorldState):
            new_state = WorldState(str(new_state))

        reason = (reason or "").strip() or "no reason provided"

        with self._lock:
            cur = self.get()

            if cur.state in TERMINAL and not allow_terminal_override:
                return cur

            if not allow_illegal_transition:
                allowed = ALLOWED_TRANSITIONS.get(cur.state, set())
                if new_state not in allowed and new_state != cur.state:
                    return WorldStateSnapshot(
                        state=cur.state,
                        reason=f"DENIED transition {cur.state.value} -> {new_state.value}: {reason}",
                        updated_at=cur.updated_at,
                        updated_by=cur.updated_by,
                    )

            now = utc_now_iso()

            with tx(self._conn) as c:
                c.execute(
                    "UPDATE world_state_current SET state=?, reason=?, updated_at=?, updated_by=? WHERE id=?",
                    (new_state.value, reason, now, actor, STATE_ROW_ID),
                )
                try:
                    c.execute(
                        "INSERT INTO world_state_events (from_state, to_state, reason, actor, created_at, trace_id) "
                        "VALUES (?,?,?,?,?,?)",
                        (cur.state.value, new_state.value, reason, actor, now, trace_id),
                    )
                except Exception:
                    pass

            return self.get()


# ---- Convenience wrappers (used across the app) ----
_STATE_STORE = WorldStateStore()


def can_execute():
    return _STATE_STORE.can_execute()


def get_state():
    return _STATE_STORE.get()


def set_state(new_state: WorldState, reason: str, actor: str = "user", trace_id: Optional[str] = None):
    return _STATE_STORE.set_state(new_state, reason=reason, actor=actor, trace_id=trace_id)


def arm(reason: str = "manual arm", actor: str = "user"):
    return set_state(WorldState.ARMED_IDLE, reason=reason, actor=actor)


def disarm(reason: str = "manual disarm", actor: str = "user"):
    return set_state(WorldState.DISARMED, reason=reason, actor=actor)


def freeze(reason: str = "manual freeze", actor: str = "user"):
    return set_state(WorldState.FROZEN, reason=reason, actor=actor)
