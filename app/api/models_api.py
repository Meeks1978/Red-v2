from __future__ import annotations
from fastapi import APIRouter
from app.models.gateway import GATEWAY

router = APIRouter(prefix="/v1", tags=["models"])

@router.get("/models/status")
def status():
    return {"ok": True, "status": GATEWAY.status()}
