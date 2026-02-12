from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .intake import intake
from .store import IntentStore
from .success import close_intent
from .reflection import attach_reflection

router = APIRouter(prefix="/v1/intent", tags=["copilot-intent"])
_store = IntentStore()


class IntakeReq(BaseModel):
    user_input: str
    trace_id: str | None = None


class CloseReq(BaseModel):
    intent_id: str
    assistant_output: str


@router.post("/intake")
def intent_intake(req: IntakeReq):
    rec = intake(req.user_input, trace_id=req.trace_id)
    _store.put(rec)
    return rec


@router.post("/close")
def intent_close(req: CloseReq):
    rec = _store.get(req.intent_id)
    if not rec:
        raise HTTPException(status_code=404, detail="intent_id not found")

    rec = close_intent(rec, req.assistant_output)
    rec = attach_reflection(rec)
    _store.update(rec.intent_id, rec)
    return rec


@router.get("/{intent_id}")
def intent_get(intent_id: str):
    rec = _store.get(intent_id)
    if not rec:
        raise HTTPException(status_code=404, detail="intent_id not found")
    return rec
