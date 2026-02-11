from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass(frozen=True)
class ReasonSurface:
    reason: str
    confidence: float
    violated_assumptions: List[str] = field(default_factory=list)
    drift_keys: List[str] = field(default_factory=list)
    what_would_change_my_mind: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class AdvisoryResponse:
    recommendation: str
    reason_surface: ReasonSurface
    debug: Dict[str, Any] = field(default_factory=dict)
