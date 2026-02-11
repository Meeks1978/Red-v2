from __future__ import annotations
import time
from typing import Any, Dict, List

class ObserverEngine:
    def tick(self, ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        # bounded, read-only observation
        return [{
            "ts_ms": int(time.time()*1000),
            "kind": "observer_tick",
            "note": "scaffold"
        }]
