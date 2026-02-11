from __future__ import annotations
from typing import Any, Dict

class MemoryCuratorEngine:
    """
    Adapter scaffold: you already have MemoryCurator in ServiceContainer.
    """
    def __init__(self, container) -> None:
        self.container = container

    def ingest_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return {"ok": True, "note": "scaffold", "event_keys": sorted(event.keys())}
