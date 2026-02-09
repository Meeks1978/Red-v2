from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

Scope = Literal["canonical", "ops", "semantic"]
Kind = Literal["fact", "event", "receipt", "doc_ref", "note"]
Source = Literal["user", "system", "runner", "doc", "import"]

class MemoryPut(BaseModel):
    scope: Scope
    kind: Kind
    text: str = Field(min_length=1, max_length=20000)
    key: Optional[str] = Field(default=None, max_length=512)
    data: Optional[dict[str, Any]] = None
    source: Source
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    ttl_seconds: Optional[int] = Field(default=None, ge=1)
    trace_id: str = Field(min_length=1, max_length=128)
    approval_ref: Optional[str] = Field(default=None, max_length=256)
    tags: list[str] = Field(default_factory=list)
    refs: list[str] = Field(default_factory=list)

class MemoryItem(MemoryPut):
    id: str
    created_at: datetime

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

class MemoryQuery(BaseModel):
    scope: Optional[Scope] = None
    kind: Optional[Kind] = None
    key: Optional[str] = None
    text_contains: Optional[str] = None
    tag: Optional[str] = None
    limit: int = Field(default=25, ge=1, le=200)

class WorldStatePut(BaseModel):
    state: dict[str, Any]
    trace_id: str = Field(min_length=1, max_length=128)

class WorldStateGet(BaseModel):
    state: dict[str, Any]
    updated_at: datetime
    trace_id: str
