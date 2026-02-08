from __future__ import annotations

import os
from fastapi import APIRouter

from app.pillars_engine import compute_pillars
from app.world_state import get_state, freeze, WorldState

router = APIRouter(tags=["pillars"])


def _env_int(name: str, default: str) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return int(default)


def _env_bool(name: str, default: str = "0") -> bool:
    v = os.getenv(name, default).strip().lower()
    return v in ("1", "true", "yes", "on")


@router.get("/health/pillars")
def health_pillars():
    """
    Returns pillar scores and can optionally auto-freeze when armed and critical dependencies fail.
    """
    report = compute_pillars()

    auto_freeze = _env_bool("PILLARS_AUTO_FREEZE", "1")
    agency_min = _env_int("PILLARS_AGENCY_MIN", "40")     # if Agency < 40 while armed -> freeze
    trust_min = _env_int("PILLARS_TRUST_MIN", "30")       # if Trust < 30 while armed -> freeze

    state = get_state()
    if auto_freeze and state.state in (WorldState.ARMED_IDLE, WorldState.ARMED_ACTIVE):
        agency = report["pillars"].get("Agency", 0)
        trust = report["pillars"].get("Trust", 0)

        if agency < agency_min:
            fr = freeze(reason=f"AUTO-FREEZE: Agency {agency} < {agency_min}", actor="pillars")
            report["auto_freeze"] = {"ok": True, "state": fr.state.value, "reason": fr.reason}
        elif trust < trust_min:
            fr = freeze(reason=f"AUTO-FREEZE: Trust {trust} < {trust_min}", actor="pillars")
            report["auto_freeze"] = {"ok": True, "state": fr.state.value, "reason": fr.reason}
        else:
            report["auto_freeze"] = {"ok": True, "action": "noop"}

    return report
