from __future__ import annotations

from fastapi import APIRouter

from app.world_probes import run_probes

router = APIRouter(prefix="/v1/world", tags=["world-probes"])


@router.post("/probes/run")
def probes_run(enforce_freeze: bool = True):
    return run_probes(enforce_freeze=enforce_freeze)
