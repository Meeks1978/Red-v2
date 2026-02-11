from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from app.memory.types import MemoryItem, now_ms


@dataclass(frozen=True)
class PromotionPolicy:
    """
    Promotion policy with an execute-specific canonical rule.

    Default thresholds:
    - working: confidence >= 0.60
    - canonical: confidence >= 0.85 AND version >= 3 (general rule)

    Execute semantic rule (Option B):
    - if namespace=="execute" AND key startswith "action:" AND version>=3
      AND value.status_code==200 AND value.ok==True -> canonical
      (and confidence lifted to >= 0.85)
    """
    promote_to_working_min_confidence: float = 0.6
    promote_to_canonical_min_confidence: float = 0.85
    min_observations_for_canonical: int = 3


class MemoryPromotion:
    def __init__(self, policy: PromotionPolicy) -> None:
        self.policy = policy

    def _execute_success(self, item: MemoryItem) -> bool:
        if item.namespace != "execute":
            return False
        if not isinstance(item.key, str) or not item.key.startswith("action:"):
            return False
        if item.version < self.policy.min_observations_for_canonical:
            return False

        v = item.value
        if not isinstance(v, dict):
            return False

        status_code = v.get("status_code")
        ok = v.get("ok")

        return status_code == 200 and ok is True

    def promote(self, item: MemoryItem) -> MemoryItem:
        if item.tier == "quarantine":
            return item

        # Option B: execute semantic canonical rule
        if self._execute_success(item):
            if item.confidence < self.policy.promote_to_canonical_min_confidence:
                item.confidence = self.policy.promote_to_canonical_min_confidence
            if item.tier != "canonical":
                item.tier = "canonical"
                item.updated_at_ms = now_ms()
            return item

        # General canonical promotion (non-execute or non-success)
        if (
            item.confidence >= self.policy.promote_to_canonical_min_confidence
            and item.version >= self.policy.min_observations_for_canonical
        ):
            if item.tier != "canonical":
                item.tier = "canonical"
                item.updated_at_ms = now_ms()
            return item

        # Working promotion
        if item.confidence >= self.policy.promote_to_working_min_confidence:
            if item.tier == "ephemeral":
                item.tier = "working"
                item.updated_at_ms = now_ms()
            return item

        return item
