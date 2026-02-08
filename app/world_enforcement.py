from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import requests

from app.world_state import get_state, freeze, WorldState


def _check_control_plane() -> Tuple[bool, str]:
    """
    Minimal critical dependency check.
    If control plane is unreachable, that's a critical degradation.
    """
    url = (os.getenv("CONTROL_PLANE_URL") or "").strip().rstrip("/")
    if not url:
        return False, "CONTROL_PLANE_URL not set"

    # Prefer /health, fall back to base
    for path in ("/health", ""):
        try:
            r = requests.get(f"{url}{path}", timeout=2.5)
            # Any HTTP response means network path exists.
            return True, f"control plane reachable ({r.status_code})"
        except Exception:
            continue

    return False, f"control plane unreachable at {url}"


def evaluate_and_enforce() -> Dict[str, Any]:
    """
    World Engine 2: auto-freeze tripwires.
    Called opportunistically (e.g., on /health/pillars or /health).
    """
    snap = get_state()

    # If ENDED, do nothing.
    if snap.state == WorldState.ENDED:
        return {"ok": True, "state": snap.state.value, "action": "noop", "reason": "ENDED"}

    # If already frozen, do nothing.
    if snap.state == WorldState.FROZEN:
        return {"ok": True, "state": snap.state.value, "action": "noop", "reason": "already frozen"}

    ok_cp, msg_cp = _check_control_plane()

    # You can add more tripwires here later:
    # - runner health check
    # - gateway health
    # - memory store health
    # - pillars score thresholds

    if not ok_cp and snap.state in (WorldState.ARMED_IDLE, WorldState.ARMED_ACTIVE):
        fr = freeze(reason=f"AUTO-FREEZE: {msg_cp}", actor="world-engine")
        return {"ok": True, "action": "freeze", "state": fr.state.value, "reason": fr.reason}

    return {"ok": True, "action": "noop", "state": snap.state.value, "reason": "no tripwires triggered"}
