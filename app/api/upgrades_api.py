from __future__ import annotations
from fastapi import APIRouter
from app.services.engine_container import ENGINES

router = APIRouter(prefix="/v1", tags=["upgrade-advisor"])

@router.get("/upgrades/proposals")
def proposals():
    props = ENGINES.upgrades.propose({"note":"scaffold"})
    return {"ok": True, "proposals": props}
