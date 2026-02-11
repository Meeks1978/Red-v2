from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class VerificationViolation:
    code: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class VerificationReport:
    ok: bool
    violations: List[VerificationViolation] = field(default_factory=list)
    required_rechecks: List[str] = field(default_factory=list)
    debug: Dict[str, Any] = field(default_factory=dict)
