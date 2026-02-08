from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .world_state import WorldStateStore, WorldState

router = APIRouter(prefix="/v1", tags=["state"])
_state_store = WorldStateStore()


class StateResponse(BaseModel):
    state: str
    reason: str
    updated_at: str
    updated_by: str


class StateSetRequest(BaseModel):
    state: WorldState = Field(..., description="Target state")
    reason: str = Field(..., min_length=1, max_length=500, description="Why this state change is happening")
    actor: str = Field(default="user", min_length=1, max_length=64, description="Who initiated the change")
    trace_id: str | None = Field(default=None, max_length=128, description="Optional trace id for audit correlation")


@router.get("/state", response_model=StateResponse)
def get_state() -> StateResponse:
    snap = _state_store.get()
    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )


@router.post("/state", response_model=StateResponse)
def set_state(req: StateSetRequest) -> StateResponse:
    try:
        snap = _state_store.set_state(
            req.state,
            reason=req.reason,
            actor=req.actor,
            trace_id=req.trace_id,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return StateResponse(
        state=snap.state.value,
        reason=snap.reason,
        updated_at=snap.updated_at,
        updated_by=snap.updated_by,
    )


@router.post("/state/disarm", response_model=StateResponse)
def disarm(reason: str = "manual disarm", actor: str = "user") -> StateResponse:
    snap = _state_store.set_state(WorldState.DISARMED, reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)


@router.post("/state/arm", response_model=StateResponse)
def arm(reason: str = "manual arm", actor: str = "user") -> StateResponse:
    snap = _state_store.set_state(WorldState.ARMED_IDLE, reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)


@router.post("/state/freeze", response_model=StateResponse)
def freeze(reason: str = "manual freeze", actor: str = "user") -> StateResponse:
    snap = _state_store.set_state(WorldState.FROZEN, reason=reason, actor=actor)
    return StateResponse(state=snap.state.value, reason=snap.reason, updated_at=snap.updated_at, updated_by=snap.updated_by)
