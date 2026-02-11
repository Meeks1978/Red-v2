from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.memory.types import MemoryItem, now_ms


@dataclass(frozen=True)
class Conflict:
    namespace: str
    key: str
    existing_id: str
    incoming_id: str
    reason: str


class MemoryConflictResolver:
    """
    Detect conflicts for same (namespace,key) when values disagree materially.
    Strategy (Phase-0):
      - If same value -> merge/update version
      - If different -> move incoming to quarantine and link conflicts
    """

    def _equivalent(self, a: object, b: object) -> bool:
        return a == b

    def detect_and_resolve(self, existing: List[MemoryItem], incoming: MemoryItem) -> Tuple[MemoryItem, List[Conflict]]:
        conflicts: List[Conflict] = []

        # no prior -> accept as-is
        if not existing:
            return incoming, conflicts

        # if any canonical/working matches value -> treat as update
        for ex in existing:
            if self._equivalent(ex.value, incoming.value):
                incoming.tier = ex.tier  # keep tier
                incoming.version = ex.version + 1
                incoming.updated_at_ms = now_ms()
                return incoming, conflicts

        # otherwise conflict: quarantine incoming
        for ex in existing:
            conflicts.append(Conflict(
                namespace=incoming.namespace,
                key=incoming.key,
                existing_id=ex.memory_id,
                incoming_id=incoming.memory_id,
                reason="value mismatch",
            ))
            incoming.conflicts_with.append(ex.memory_id)

        incoming.tier = "quarantine"
        incoming.updated_at_ms = now_ms()
        return incoming, conflicts
