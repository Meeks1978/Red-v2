from __future__ import annotations
import time
from typing import Any, Dict

from app.contracts.world import WorldSnapshot

class WorldModelerEngine:
    def snapshot(self) -> WorldSnapshot:
        return WorldSnapshot(ts_ms=int(time.time()*1000), facts={})
