from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.services.engine_container import ENGINES

router = APIRouter(prefix="/v1", tags=["orchestrator"])

class ReasonReq(BaseModel):
    text: str
    trace_id: Optional[str] = None

@router.post("/reason")
def reason(req: ReasonReq):
    out = ENGINES.orchestrator.reason_only(req.text, trace_id=req.trace_id)
    return {"ok": out.ok, "trace_id": out.trace_id, "out": out}

class ActReq(BaseModel):
    text: str
    execute: bool = False
    trace_id: Optional[str] = None
    approval_token: Optional[Dict[str, Any]] = None

@router.post("/act")
def act(req: ActReq):
    out = ENGINES.orchestrator.act(
        req.text,
        trace_id=req.trace_id,
        execute=req.execute,
        approval_token=req.approval_token,
    )
    return {"ok": out.ok, "trace_id": out.trace_id, "out": out}
