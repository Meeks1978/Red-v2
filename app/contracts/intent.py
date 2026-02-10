from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from red.app.types.core import Confidence


@dataclass(frozen=True)
class Intent:
    intent_id: str
    user_text: str
    created_at_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SuccessCriteria:
    """
    Explicit definition of 'done' for an intent.
    """
    description: str
    required_signals: List[str] = field(default_factory=list)  # e.g. ["calendar_event_created", "email_drafted"]
    must_not_happen: List[str] = field(default_factory=list)    # e.g. ["sent_email", "created_event"]


@dataclass(frozen=True)
class Plan:
    plan_id: str
    intent_id: str
    summary: str
    steps: List[Dict[str, Any]] = field(default_factory=list)   # deliberately generic here
    assumptions: List[str] = field(default_factory=list)
    success: Optional[SuccessCriteria] = None
    confidence: Confidence = Confidence(0.5, "default")
