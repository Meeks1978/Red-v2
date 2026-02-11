from __future__ import annotations
from fastapi import APIRouter
from app.services.engine_container import ENGINES

router = APIRouter(prefix="/v1", tags=["world-engine"])

@router.get("/world/snapshot")
def snapshot():
    snap = ENGINES.world.snapshot()
    return {"ok": True, "snapshot": snap}
