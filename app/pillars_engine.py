from __future__ import annotations

import os
import sqlite3
from typing import Any, Dict, Tuple

from app.db import connect, DEFAULT_DB_PATH
from app.world_state import get_state, WorldState
from app.world_entities import EntityRegistry


def _env_bool(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default).strip().lower()
    return v in ("1", "true", "yes", "on")


def _score(ok: bool, good: int = 100, bad: int = 0) -> int:
    return good if ok else bad


def _db_writable(db_path: str) -> bool:
    try:
        conn = connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS _pillars_probe (k TEXT PRIMARY KEY, v TEXT)")
        conn.execute("INSERT OR REPLACE INTO _pillars_probe (k, v) VALUES ('last', 'ok')")
        if conn.in_transaction:
            conn.commit()
        return True
    except Exception:
        return False


def compute_pillars() -> Dict[str, Any]:
    """
    World Engine 4: Pillars v1 (objective signals).

    Returns:
      - per-pillar score 0..100
      - overall existence score
      - gating failures (actionable)
    """
    db_path = os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)
    reg = EntityRegistry()
    state = get_state()

    # Signals
    approvals_secret_ok = len(os.getenv("APPROVAL_SIGNING_SECRET", "")) >= 16
    db_ok = _db_writable(db_path)

    # Control plane status from entity registry (world probes update this)
    cp = reg.get_entity("meeks-control-plane")
    cp_ok = bool(cp and cp.get("status") == "OK")

    # “Scheduler running” is optional but boosts Awareness/Continuity
    scheduler_enabled = _env_bool("WORLD_SCHEDULER_ENABLED", "0")

    # Pillar scores (v1)
    pillars: Dict[str, int] = {
        "Identity": _score(approvals_secret_ok),         # secret present = identity anchor for authority minting
        "Continuity": _score(db_ok, good=90, bad=20),    # DB writable indicates state persistence viable
        "Agency": _score(cp_ok, good=90, bad=10),        # CP reachable = can act (through governance)
        "Governance": 100,                               # governance mechanisms exist; gating handled elsewhere
        "Awareness": _score(scheduler_enabled, good=70, bad=30),
        "Presence": 20,                                  # not implemented yet (watch/phone/AR)
        "Intentionality": 70,                             # approvals+scopes exist, planning layer minimal
        "Adaptation": 20,                                 # Phase-6 switch OFF
        "Embodiment": 80,                                 # runners proven (ai-laptop system)
        "Trust": _score(approvals_secret_ok and db_ok, good=85, bad=30),
    }

    # Governance gating failures (actionable)
    failures = []
    if not approvals_secret_ok:
        failures.append("APPROVAL_SIGNING_SECRET missing/too short (authority minting unsafe)")
    if not db_ok:
        failures.append("RED_DB_PATH not writable (continuity degraded)")
    if state.state in (WorldState.FROZEN, WorldState.DISARMED):
        failures.append(f"World state blocks execution: {state.state.value}")

    # Overall existence score (simple average)
    overall = int(sum(pillars.values()) / max(1, len(pillars)))

    return {
        "ok": True,
        "world_state": {"state": state.state.value, "reason": state.reason},
        "pillars": pillars,
        "overall": overall,
        "failures": failures,
    }
