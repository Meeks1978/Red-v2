from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class IntentStatus(str, Enum):
    OPEN = "open"
    PARTIAL = "partial"
    DONE = "done"
    BLOCKED = "blocked"


@dataclass
class Assumption:
    statement: str
    verified: bool = False
    confidence: float = 0.5


@dataclass
class SuccessCriteria:
    conditions: List[str] = field(default_factory=list)


@dataclass
class ReasonSurface:
    signals_used: List[str] = field(default_factory=list)
    key_factors: List[str] = field(default_factory=list)
    what_would_change_my_mind: List[str] = field(default_factory=list)


@dataclass
class IntentRecord:
    intent_id: str
    created_at: str
    updated_at: str

    user_input: str
    goal: str
    constraints: List[str] = field(default_factory=list)

    status: IntentStatus = IntentStatus.OPEN
    success: SuccessCriteria = field(default_factory=SuccessCriteria)
    assumptions: List[Assumption] = field(default_factory=list)

    confidence: float = 0.6
    reasons: ReasonSurface = field(default_factory=ReasonSurface)

    memory_candidates: List[Dict[str, Any]] = field(default_factory=list)
    reflection: Dict[str, Any] = field(default_factory=dict)

    trace_id: Optional[str] = None


def new_intent_id() -> str:
    return f"INT-{uuid4().hex[:12]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
