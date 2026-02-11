from __future__ import annotations
from fastapi import APIRouter
from app.services.engine_container import ENGINES

router = APIRouter(prefix="/v1", tags=["observer-engine"])

@router.get("/observer/status")
def status():
    obs = ENGINES.observer.tick({"note":"scaffold"})
    return {"ok": True, "observations": obs}
