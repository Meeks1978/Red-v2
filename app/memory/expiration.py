from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.memory.types import MemoryItem


@dataclass(frozen=True)
class ExpirationPolicy:
    """
    Rule: what should expire, and when.
    Keep it simple at first; tune later.
    """
    default_ttl_ms: Optional[int] = 7 * 24 * 60 * 60 * 1000  # 7 days


class MemoryExpiration:
    def __init__(self, policy: ExpirationPolicy) -> None:
        self.policy = policy

    def apply_default_ttl(self, item: MemoryItem) -> MemoryItem:
        if item.ttl_ms is not None:
            return item
        if self.policy.default_ttl_ms is None:
            return item
        item.ttl_ms = self.policy.default_ttl_ms
        return item

    def should_expire(self, item: MemoryItem) -> bool:
        return item.is_expired()
