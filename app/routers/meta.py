# red/app/routers/meta.py
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter

from app.runtime.layer_status import layer_status_store

router = APIRouter(tags=["meta"])

def _git(cmd: list[str]) -> Optional[str]:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        return out or None
    except Exception:
        return None

def _build_meta() -> Dict[str, Any]:
    # prefer env if you inject at build time; else fallback to git (works in dev)
    commit = os.getenv("RED_GIT_COMMIT") or _git(["git", "rev-parse", "--short", "HEAD"]) or "unknown"
    branch = os.getenv("RED_GIT_BRANCH") or _git(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    dirty = os.getenv("RED_GIT_DIRTY")
    if dirty is None:
        dirty = "true" if (_git(["git", "status", "--porcelain"]) not in (None, "")) else "false"

    return {
        "commit": commit,
        "branch": branch,
        "dirty": (str(dirty).lower() == "true"),
        "built_at": os.getenv("RED_BUILT_AT") or None,
        "service": os.getenv("RED_SERVICE_NAME", "red"),
    }

@router.get("/meta/build")
def meta_build() -> Dict[str, Any]:
    return _build_meta()

@router.get("/health/layers")
def health_layers() -> Dict[str, Any]:
    # Dashboard expects { layers: { "1": {status:..}, ... } }
    snap = layer_status_store.snapshot()
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "layers": {str(k): v for k, v in snap.items()},
    }

@router.get("/meta/phase7")
def meta_phase7() -> Dict[str, Any]:
    # Required layer list for Phase-7 minimum set
    required_ids = [4, 6, 9, 22, 23, 24, 27, 32, 33, 35, 36, 37, 38, 39]

    required_layers: Dict[str, Any] = {}
    for lid in required_ids:
        st = layer_status_store.get(lid)
        required_layers[str(lid)] = (st.status if st else "not_started")

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        # you’ll wire these for real once you add the governance state machine & observer loop
        "governance_state": os.getenv("RED_GOV_STATE", "DISARMED"),
        "observer_loop": os.getenv("RED_OBSERVER_STATE", "stopped"),
        "required_layers": required_layers,
    }
