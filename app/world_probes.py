from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import requests

from app.world_entities import EntityRegistry
from app.world_state import get_state, freeze, WorldState

_registry = EntityRegistry()


def _probe_http(name: str, url: str, timeout_s: float = 2.5) -> Tuple[bool, str, Dict[str, Any]]:
    try:
        r = requests.get(url, timeout=timeout_s)
        return True, f"{name} reachable ({r.status_code})", {"status_code": r.status_code}
    except Exception as e:
        return False, f"{name} unreachable: {e}", {}


def run_probes(enforce_freeze: bool = True) -> Dict[str, Any]:
    """
    World Engine 3 probes. Can be called manually or later scheduled.
    Updates entity registry and optionally auto-freezes if armed and critical deps are down.
    """
    cp_base = (os.getenv("CONTROL_PLANE_URL") or "").strip().rstrip("/")
    if not cp_base:
        cp_base = "http://meeks-control-plane:8088"

    ok_cp, msg_cp, meta_cp = _probe_http("control-plane", f"{cp_base}/health")
    _registry.touch("meeks-control-plane", "OK" if ok_cp else "DOWN", {"probe": msg_cp, **meta_cp})

    snap = get_state()
    froze = None
    if enforce_freeze and (not ok_cp) and snap.state in (WorldState.ARMED_IDLE, WorldState.ARMED_ACTIVE):
        fr = freeze(reason=f"AUTO-FREEZE: {msg_cp}", actor="world-engine")
        froze = {"state": fr.state.value, "reason": fr.reason}

    return {
        "ok": True,
        "control_plane": {"ok": ok_cp, "msg": msg_cp},
        "world_state": {"state": snap.state.value, "reason": snap.reason},
        "freeze": froze,
    }
