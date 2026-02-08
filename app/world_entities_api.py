from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.world_entities import EntityRegistry

router = APIRouter(prefix="/v1/world", tags=["world-entities"])
_registry = EntityRegistry()


class EntityUpsert(BaseModel):
    entity_id: str = Field(..., min_length=1)
    kind: str = Field(default="service")
    display_name: str = Field(default="")
    tags: List[str] = Field(default_factory=list)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    last_seen: Optional[str] = None
    status: str = Field(default="UNKNOWN")
    meta: Dict[str, Any] = Field(default_factory=dict)


@router.get("/entities")
def list_entities():
    return {"ok": True, "entities": _registry.list_entities()}


@router.get("/entities/{entity_id}")
def get_entity(entity_id: str):
    ent = _registry.get_entity(entity_id)
    if not ent:
        raise HTTPException(status_code=404, detail="entity not found")
    return {"ok": True, "entity": ent}


@router.put("/entities/{entity_id}")
def upsert_entity(entity_id: str, payload: EntityUpsert):
    d = payload.model_dump()
    d["entity_id"] = entity_id
    if not d.get("display_name"):
        d["display_name"] = entity_id
    ent = _registry.upsert(d)
    return {"ok": True, "entity": ent}
