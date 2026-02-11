from __future__ import annotations

from fastapi import APIRouter
from typing import Optional

from app.services.container import ServiceContainer

router = APIRouter(prefix="/v1/semantic", tags=["semantic-memory"])


@router.get("/status")
def status():
    return {
        "enabled": ServiceContainer.semantic_memory is not None,
        "qdrant_url": bool(getattr(ServiceContainer, "semantic_memory", None)),
    }


@router.get("/search")
def search(q: str, limit: int = 5):
    sem = ServiceContainer.semantic_memory
    if sem is None:
        return {"ok": False, "error": "semantic memory disabled (set ENABLE_SEMANTIC_MEMORY=true and QDRANT_URL)"}
    hits = sem.search(query=q, limit=limit)
    return {"ok": True, "hits": hits}
