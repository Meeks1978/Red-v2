from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import uuid


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True)
class Confidence:
    """
    0.0 - 1.0 probability-ish score. Not a truth claim; a decision aid.
    """
    score: float
    rationale: str = ""


@dataclass(frozen=True)
class EvidenceRef:
    """
    Pointer to evidence (log snapshot, screenshot, file, trace segment, etc.)
    """
    kind: str
    uri: str
    note: str = ""


@dataclass(frozen=True)
class Receipt:
    """
    Execution receipt / provability artifact.
    """
    receipt_id: str
    trace_id: str
    step_id: str
    ok: bool
    started_at_ms: int
    finished_at_ms: int
    output: Dict[str, Any] = field(default_factory=dict)
    evidence: List[EvidenceRef] = field(default_factory=list)
    error: Optional[str] = None

    @staticmethod
    def now_ms() -> int:
        return int(time.time() * 1000)
