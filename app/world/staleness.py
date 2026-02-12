from __future__ import annotations

from typing import Any, Dict, List
from app.world.store import WorldStore, now_ms


class StalenessMonitor:
    """
    Computes staleness signals without raising.
    """

    def __init__(self, store: WorldStore) -> None:
        self.store = store

    def report(self, stale_after_ms: int) -> Dict[str, Any]:
        try:
            stale_ids = self.store.staleness(stale_after_ms=stale_after_ms)
            return {
                "ok": True,
                "now_ms": now_ms(),
                "stale_after_ms": int(stale_after_ms),
                "stale_count": len(stale_ids),
                "stale_ids": stale_ids[:200],  # cap payload
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "stale_count": 0, "stale_ids": []}
