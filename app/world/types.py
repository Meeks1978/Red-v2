from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import uuid


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class Source:
    """
    Where a fact came from.
    """
    source_id: str
    kind: str            # sensor | human | inference | memory
    trust: float         # 0.0 - 1.0 baseline trust


@dataclass
class WorldFact:
    fact_id: str
    key: str
    value: Any
    observed_at_ms: int
    source: Source
    ttl_ms: Optional[int] = None

    def age_ms(self) -> int:
        return now_ms() - self.observed_at_ms

    def is_stale(self) -> bool:
        return self.ttl_ms is not None and self.age_ms() > self.ttl_ms


@dataclass
class WorldSnapshot:
    """
    Point-in-time view of the world.
    """
    snapshot_id: str
    created_at_ms: int
    facts: Dict[str, WorldFact] = field(default_factory=dict)
