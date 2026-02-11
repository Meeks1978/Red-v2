from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import uuid


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class MemorySource:
    kind: str  # receipt | world | human | system | inference
    ref: str   # trace_id / receipt_id / url / etc.


@dataclass
class MemoryItem:
    """
    A single memory record. Start simple and keep it auditable.
    """
    memory_id: str
    namespace: str            # e.g. "world", "ops", "approvals"
    key: str                  # stable lookup key (entity_id:attr or intent_id, etc.)
    value: Any                # stored payload
    created_at_ms: int
    updated_at_ms: int
    source: MemorySource
    ttl_ms: Optional[int] = None

    # hygiene / governance
    confidence: float = 0.5   # 0..1
    tags: List[str] = field(default_factory=list)

    # lifecycle
    tier: str = "ephemeral"   # ephemeral | working | canonical | quarantine
    version: int = 1

    # conflict tracking
    conflicts_with: List[str] = field(default_factory=list)
    notes: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.ttl_ms is None:
            return False
        return (now_ms() - self.updated_at_ms) > self.ttl_ms
