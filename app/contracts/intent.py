from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class IntentEnvelope:
    intent_id: str
    text: str
    created_at_ms: int
    user_context: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
