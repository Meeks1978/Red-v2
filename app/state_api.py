from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.world_state import WorldState, get_state, set_state, arm, disarm, freeze

router = APIRouter(prefix="/v1", tags=["state"])


class StateResponse(BaseModel):
    state: str
    reason: str
    updated_at: str
    updated_by: str


class StateSetRequest(BaseModel):
    state: WorldState = Field(...)
    reason: str = Field(..., min_length=1, max_length=500)
    actor: str = Field(default="user", min_length=1, max_length=64)
    trace_id: str | None = Field(default=None, max_length=128)


@router.get("/state", response_model=StateResponse)
def api_get_state() -> StateResponse:
    snap = get_state()
    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )


@router.post("/state", response_model=StateResponse)
def api_set_state(req: StateSetRequest) -> StateResponse:
    snap = set_state(req.state, reason=req.reason, actor=req.actor, trace_id=req.trace_id)
    # If denied, set_state returns a snapshot with DENIED… reason but unchanged state.
    if snap.reason.startswith("DENIED transition"):
        raise HTTPException(status_code=403, detail=snap.reason)
    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )


@router.post("/state/arm", response_model=StateResponse)
def api_arm(reason: str = "manual arm", actor: str = "user") -> StateResponse:
    snap = arm(reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)


@router.post("/state/disarm", response_model=StateResponse)
def api_disarm(reason: str = "manual disarm", actor: str = "user") -> StateResponse:
    snap = disarm(reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)


@router.post("/state/freeze", response_model=StateResponse)
def api_freeze(reason: str = "manual freeze", actor: str = "user") -> StateResponse:
    snap = freeze(reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)
