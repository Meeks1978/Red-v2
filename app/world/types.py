from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
import time

def now_ms() -> int:
    return int(time.time() * 1000)



class WorldEntity(BaseModel):
    entity_id: str
    kind: str = "generic"
    attrs: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    created_at_ms: int
    updated_at_ms: int
    last_seen_ms: int


class WorldEvent(BaseModel):
    ts_ms: int
    kind: str
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    source: str = "world"
    confidence: float = 0.5


class Snapshot(BaseModel):
    ok: bool = True
    store_path: str
    entity_count: int
    event_count: int
    last_event_ts: Optional[int] = None
    stale_entity_count: int = 0


class UpsertEntityRequest(BaseModel):
    entity_id: str
    kind: str = "generic"
    attrs: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    seen: bool = True
    ts_ms: Optional[int] = None


class EmitEventRequest(BaseModel):
    kind: str
    entity_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None
    confidence: float = 0.5
    ts_ms: Optional[int] = None
    source: str = "world"



# --- WorldRelation (added for BU-4 store compatibility) ---

class WorldRelation(BaseModel):
    """
    Minimal relationship edge between two entities.
    Keep stable: JSON-serializable, schema-light, no side effects.
    """
    src_id: str
    dst_id: str
    rel: str = "related_to"
    attrs: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    ts_ms: Optional[int] = None

class UpsertRelationRequest(BaseModel):
    src_id: str
    dst_id: str
    rel: str = "related_to"
    attrs: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.5
    ts_ms: Optional[int] = None

class ListRelationsResponse(BaseModel):
    ok: bool = True
    since_ms: Optional[int] = None
    limit: int = 100
    relations: List[WorldRelation] = Field(default_factory=list)

class ListEventsResponse(BaseModel):
    ok: bool = True
    since_ms: Optional[int] = None
    limit: int = 100
    events: List[WorldEvent] = Field(default_factory=list)


class ListEntitiesResponse(BaseModel):
    ok: bool = True
    entities: List[WorldEntity] = Field(default_factory=list)


class ProbeRequest(BaseModel):
    kind: Literal["snapshot", "staleness", "drift"] = "snapshot"
    limit: int = 50
    stale_after_ms: int = 6 * 60 * 60 * 1000  # 6h default


class ProbeResponse(BaseModel):
    ok: bool = True
    kind: str
    data: Dict[str, Any] = Field(default_factory=dict)
