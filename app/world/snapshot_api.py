from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter

from app.world.store import WorldStore

router = APIRouter(prefix="/v1/world", tags=["world"])

# Durable store path (volume-mounted /red/data is already in your run flags)
WORLD_DB_PATH = os.getenv("WORLD_DB_PATH", "/red/data/world.db")

STORE = WorldStore(WORLD_DB_PATH)


@router.get("/snapshot")
def world_snapshot(limit_entities: int = 50, limit_events: int = 25) -> Dict[str, Any]:
    """
    BU-4 Step A: World snapshot.
    Returns a compact view of:
      - counts
      - recent entities
      - recent events
    """
    entities = STORE.list_entities(limit=limit_entities)
    events = STORE.list_events(limit=limit_events)

    return {
        "ok": True,
        "store": {"db_path": WORLD_DB_PATH},
        "counts": {
            "entities": STORE.count_entities(),
            "events": STORE.count_events(),
        },
        "entities": entities,
        "events": events,
    }


@router.post("/_debug/seed")
def debug_seed() -> Dict[str, Any]:
    """
    Optional helper: seeds one entity + one event so you can prove persistence quickly.
    Safe: only touches world.db.
    """
    e = STORE.upsert_entity(
        entity_id="node:ai-control",
        kind="node",
        external_id="ai-control",
        name="AI-Control",
        attrs={"role": "red-core", "note": "seed"},
    )
    ev = STORE.append_event(kind="seed", entity_id=e["entity_id"], payload={"note": "seed event"})
    return {"ok": True, "entity": e, "event": ev}

# --- BU-4 Drift endpoint (minimal, safe) ---
# Adds: GET /v1/world/drift?limit=10
# Uses the same STORE as /snapshot, and caches a DriftDetector instance so
# fingerprint state persists across calls.
try:
    from typing import Optional
    from app.world.drift import DriftDetector
except Exception:
    DriftDetector = None  # type: ignore
    Optional = None  # type: ignore

_DETECTOR = None

@router.get("/drift")
def world_drift(limit: int = 10):
    """
    Minimal drift probe. Must never crash the service.
    Returns fingerprint + drift_events.
    """
    try:
        global _DETECTOR
        if DriftDetector is None:
            return {"ok": False, "error": "DriftDetector import failed"}
        if _DETECTOR is None:
            # STORE should exist in this module because /snapshot already uses it.
            _DETECTOR = DriftDetector(STORE)
        out = _DETECTOR.compute(limit_entities=int(limit))
        # DriftDetector.compute already returns a dict with drift_events + fingerprint.
        if isinstance(out, dict):
            out.setdefault("ok", True)
            return out
        return {"ok": True, "result": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---- BU-4 write path (emit) ----
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from app.services.container import ServiceContainer

class EmitReq(BaseModel):
    kind: str = "note"
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    source: str = "world"

@router.post("/emit")
def world_emit(req: EmitReq):
    """
    Minimal stable world write path.
    Must NEVER crash the server.
    """
    try:
        eng = ServiceContainer.world_engine
        out = eng.emit(
            kind=req.kind,
            entity_id=req.entity_id,
            payload=req.payload,
            trace_id=req.trace_id,
            source=req.source,
        )
        return {"ok": True, "result": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}

