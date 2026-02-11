from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class WorldFact:
    key: str
    value: Any
    observed_at_ms: int
    source: str = "unknown"
    ttl_ms: Optional[int] = None

@dataclass(frozen=True)
class WorldSnapshot:
    ts_ms: int
    facts: Dict[str, WorldFact] = field(default_factory=dict)

@dataclass(frozen=True)
class DriftEvent:
    key: str
    expected: Any
    observed: Any
    reason: str
