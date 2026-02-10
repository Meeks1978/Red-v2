from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class AssumptionStatus(str, Enum):
    VALID = "valid"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


@dataclass
class Assumption:
    key: str                     # world fact key this depends on
    expected_value: Any          # what the plan assumes
    description: str
    status: AssumptionStatus = AssumptionStatus.UNKNOWN
    last_checked_ms: Optional[int] = None
