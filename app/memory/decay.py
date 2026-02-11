from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from app.memory.types import MemoryItem, now_ms


@dataclass(frozen=True)
class DecayPolicy:
    # Staleness windows
    working_stale_ms: int = 3 * 24 * 60 * 60 * 1000      # 3 days
    canonical_stale_ms: int = 7 * 24 * 60 * 60 * 1000    # 7 days

    # Per-sweep deltas (called manually or via future scheduler)
    working_decay_step: float = 0.03
    canonical_decay_step: float = 0.02

    # Demotion thresholds
    working_floor: float = 0.60
    canonical_floor: float = 0.85

    # Hard clamps
    min_conf: float = 0.05
    max_conf: float = 0.98


class MemoryDecay:
    def __init__(self, policy: DecayPolicy) -> None:
        self.policy = policy

    def apply(self, item: MemoryItem) -> Tuple[MemoryItem, bool, str]:
        """
        Returns: (item, changed?, note)
        """
        if item.tier in ("quarantine",):
            return item, False, "skip:quarantine"

        age = now_ms() - item.updated_at_ms
        changed = False
        note = "noop"

        # Working tier decay
        if item.tier == "working" and age > self.policy.working_stale_ms:
            item.confidence = max(self.policy.min_conf, item.confidence - self.policy.working_decay_step)
            changed = True
            note = "decayed:working"
            if item.confidence < self.policy.working_floor:
                item.tier = "ephemeral"
                changed = True
                note = "demoted:working->ephemeral"

        # Canonical tier decay (demote to working if it drops below canonical floor)
        if item.tier == "canonical" and age > self.policy.canonical_stale_ms:
            item.confidence = max(self.policy.min_conf, item.confidence - self.policy.canonical_decay_step)
            changed = True
            note = "decayed:canonical"
            if item.confidence < self.policy.canonical_floor:
                item.tier = "working"
                changed = True
                note = "demoted:canonical->working"

        # Clamp
        if item.confidence > self.policy.max_conf:
            item.confidence = self.policy.max_conf
            changed = True
            note = "clamped:max"

        return item, changed, note
