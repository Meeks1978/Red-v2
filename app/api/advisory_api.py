from __future__ import annotations
import time, uuid
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.services.engine_container import ENGINES
from app.contracts.intent import IntentEnvelope

router = APIRouter(prefix="/v1", tags=["advisory"])

class AdvisoryRequest(BaseModel):
    text: str
    intent_id: Optional[str] = None
    trace_id: Optional[str] = None
    constraints: Dict[str, Any] = {}
    user_context: Dict[str, Any] = {}

@router.post("/advisory")
def advisory(req: AdvisoryRequest):
    intent = IntentEnvelope(
        intent_id=req.intent_id or f"intent_{uuid.uuid4().hex[:10]}",
        text=req.text,
        created_at_ms=int(time.time()*1000),
        user_context=req.user_context,
        constraints=req.constraints,
        trace_id=req.trace_id,
    )
    ctx = {
        "memory_stats": getattr(ENGINES.core, "runtime", None),
        "world": ENGINES.world.snapshot().ts_ms,
        "semantic_enabled": bool(getattr(ENGINES.core, "semantic_memory", None)),
    }
    out = ENGINES.advisory.advise(intent, ctx)
    return {"ok": True, "advisory": out}
