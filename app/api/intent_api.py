from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.services.container import ServiceContainer

router = APIRouter(prefix="/v1/intent", tags=["intent"])


class IntentStartReq(BaseModel):
    text: str
    required_signals: List[str] = []
    must_not_happen: List[str] = []
    trace_id: Optional[str] = None


class IntentCloseReq(BaseModel):
    intent_id: str
    final_state: Dict[str, Any] = {}
    receipts: List[Dict[str, Any]] = []
    ok: Optional[bool] = None
    summary: Optional[str] = None
    confidence: Optional[float] = None
    assumptions: List[str] = []
    what_would_change_my_mind: List[str] = []


@router.post("/start")
def start(req: IntentStartReq) -> Dict[str, Any]:
    rec = ServiceContainer.intent_tracker.start(
        text=req.text,
        required_signals=req.required_signals,
        must_not_happen=req.must_not_happen,
        trace_id=req.trace_id,
    )
    return {"ok": True, "intent_id": rec.intent_id, "trace_id": rec.trace_id, "created_at_ms": rec.created_at_ms}


@router.post("/close")
def close(req: IntentCloseReq) -> Dict[str, Any]:
    rec = ServiceContainer.intent_tracker.close(
        intent_id=req.intent_id,
        final_state=req.final_state or {},
        receipts=req.receipts or [],
        ok=req.ok,
        summary=req.summary,
        confidence=req.confidence,
        assumptions=req.assumptions or [],
        what_would_change_my_mind=req.what_would_change_my_mind or [],
    )
    if not rec:
        return {"ok": False, "error": "intent_id not found"}
    return {"ok": True, "intent_id": rec.intent_id, "closed_at_ms": rec.closed_at_ms}


@router.get("/get")
def get(intent_id: str) -> Dict[str, Any]:
    d = ServiceContainer.intent_tracker.get(intent_id)
    if not d:
        return {"ok": False, "error": "intent_id not found"}
    return {"ok": True, "intent": d}


@router.get("/open")
def open_(limit: int = 25) -> Dict[str, Any]:
    return {"ok": True, "items": ServiceContainer.intent_tracker.list_open(limit=limit)}


@router.get("/stats")
def stats() -> Dict[str, Any]:
    return {"ok": True, "stats": ServiceContainer.intent_tracker.stats()}
