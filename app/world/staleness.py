from __future__ import annotations

from typing import List

from app.world.types import WorldFact


class StalenessMonitor:
    def find_stale(self, facts: List[WorldFact]) -> List[WorldFact]:
        return [f for f in facts if f.is_stale()]
