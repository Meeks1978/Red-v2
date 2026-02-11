from __future__ import annotations
import time, uuid
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.services.engine_container import ENGINES
from app.contracts.intent import IntentEnvelope

router = APIRouter(prefix="/v1", tags=["planning"])

class PlanRequest(BaseModel):
    text: str
    intent_id: Optional[str] = None
    trace_id: Optional[str] = None
    constraints: Dict[str, Any] = {}
    user_context: Dict[str, Any] = {}

@router.post("/plan")
def plan(req: PlanRequest):
    intent = IntentEnvelope(
        intent_id=req.intent_id or f"intent_{uuid.uuid4().hex[:10]}",
        text=req.text,
        created_at_ms=int(time.time()*1000),
        user_context=req.user_context,
        constraints=req.constraints,
        trace_id=req.trace_id,
    )
    bundle = ENGINES.planning.plan(intent, {"note":"scaffold"})
    return {"ok": True, "bundle": bundle}
