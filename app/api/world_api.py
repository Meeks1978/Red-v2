from __future__ import annotations


def _to_jsonable(x):
    """
    Best-effort JSONable conversion for Pydantic/dict/plain objects.
    Never raises.
    """
    if x is None:
        return None
    if isinstance(x, dict):
        return x
    md = getattr(x, "model_dump", None)
    if callable(md):
        try:
            return md()
        except Exception:
            pass
    dct = getattr(x, "dict", None)
    if callable(dct):
        try:
            return dct()
        except Exception:
            pass
    try:
        return dict(x)
    except Exception:
        pass
    return {"repr": repr(x)}
from fastapi import APIRouter, Query
from typing import Optional

from app.services.container import ServiceContainer
from app.world.types import (
    EmitEventRequest,
    UpsertEntityRequest,
    UpsertRelationRequest,
    ListEventsResponse,
    ListEntitiesResponse,
    ListRelationsResponse,
    ProbeRequest,
)

router = APIRouter(prefix="/v1/world", tags=["world"])


@router.get("/snapshot")
def snapshot():
    return ServiceContainer.world_engine.snapshot()


@router.post("/probes/run")
def probes_run(req: ProbeRequest):
    return ServiceContainer.world_engine.probe(req)


@router.get("/entities")
def list_entities(limit: int = Query(200, ge=0, le=2000)):
    ents = ServiceContainer.world_engine.store.list_entities(limit=limit)
    return ListEntitiesResponse(ok=True, entities=ents).model_dump()


@router.get("/entities/{entity_id}")
def get_entity(entity_id: str):
    ent = ServiceContainer.world_engine.store.get_entity(entity_id)
    return {"ok": bool(ent), "entity": _to_jsonable(ent) if ent else None}


@router.post("/entities")
def upsert_entity(req: UpsertEntityRequest):
    ent = ServiceContainer.world_engine.store.upsert_entity(
        entity_id=req.entity_id,
        kind=req.kind,
        attrs=req.attrs,
        confidence=req.confidence,
        seen=req.seen,
        ts_ms=req.ts_ms,
    )
    return {"ok": True, "entity": _to_jsonable(ent)}


@router.get("/relations")
def list_relations(limit: int = Query(500, ge=0, le=5000)):
    rels = ServiceContainer.world_engine.store.list_relations(limit=limit)
    return ListRelationsResponse(ok=True, relations=rels).model_dump()


@router.post("/relations")
def upsert_relation(req: UpsertRelationRequest):
    rel = ServiceContainer.world_engine.store.upsert_relation(
        src_id=req.src_id,
        rel_type=req.rel_type,
        dst_id=req.dst_id,
        attrs=req.attrs,
        confidence=req.confidence,
        ts_ms=req.ts_ms,
    )
    return {"ok": True, "relation": rel.model_dump()}


@router.get("/events")
def list_events(
    limit: int = Query(100, ge=0, le=1000),
    since_ms: Optional[int] = Query(None),
):
    evs = ServiceContainer.world_engine.store.list_events(since_ms=since_ms, limit=limit)
    return ListEventsResponse(ok=True, since_ms=since_ms, limit=limit, events=evs).model_dump()


@router.post("/events")
def emit_event(req: EmitEventRequest):
    return ServiceContainer.world_engine.modeler.ingest_observation(
        kind=req.kind,
        payload=req.payload,
        entity_id=req.entity_id,
        trace_id=req.trace_id,
        source=req.source,
        confidence=req.confidence,
        ts_ms=req.ts_ms,
    )


@router.post("/ingest/receipt")
def ingest_receipt(payload: dict):
    # expects {"receipt": {...}, "trace_id": "..."} but stays permissive
    receipt = payload.get("receipt") if isinstance(payload, dict) else {}
    trace_id = payload.get("trace_id") if isinstance(payload, dict) else None
    return ServiceContainer.world_engine.modeler.ingest_execute_receipt(receipt=receipt or {}, trace_id=trace_id)


@router.get("/events/stream")
def events_stream(
    limit: int = Query(50, ge=0, le=200),
    since_ms: Optional[int] = Query(None),
):
    evs = ServiceContainer.world_engine.store.list_events(since_ms=since_ms, limit=limit)
    last = evs[-1].ts_ms if evs else since_ms
    return {"ok": True, "since_ms": since_ms, "next_since_ms": last, "events": [e.model_dump() for e in evs]}

# ---- BU-4: World write path (emit) ----
# NOTE: main.py already includes world_engine_router from this module.
# This endpoint must never crash the server.

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.services.container import ServiceContainer


class EmitReq(BaseModel):
    kind: str = "note"
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    source: str = "world"


@router.post("/emit")
def world_emit(req: EmitReq):
    try:
        eng = ServiceContainer.world_engine

        # Preferred: engine implements emit()
        if hasattr(eng, "emit") and callable(getattr(eng, "emit")):
            out = eng.emit(
                kind=req.kind,
                entity_id=req.entity_id,
                payload=req.payload,
                trace_id=req.trace_id,
                source=req.source,
            )
            return {"ok": True, "result": out}

        # Fallback: store implements append_event()
        store = getattr(eng, "store", None)
        if store is not None and hasattr(store, "append_event") and callable(getattr(store, "append_event")):
            out = store.append_event(
                kind=req.kind,
                entity_id=req.entity_id,
                payload=req.payload,
                trace_id=req.trace_id,
                source=req.source,
            )
            return {"ok": True, "result": out}

        return {"ok": False, "error": "World engine has no emit() and store has no append_event()."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

