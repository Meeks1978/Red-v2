from __future__ import annotations

from typing import Dict, Iterable, Optional

from app.world.types import WorldFact, WorldSnapshot, new_id, now_ms


class WorldStore:
    """
    In-memory world model.
    """
    def __init__(self) -> None:
        self._facts: Dict[str, WorldFact] = {}

    def upsert_fact(self, fact: WorldFact) -> None:
        self._facts[fact.key] = fact

    def get_fact(self, key: str) -> Optional[WorldFact]:
        return self._facts.get(key)

    def all_facts(self) -> Iterable[WorldFact]:
        return self._facts.values()

    def snapshot(self) -> WorldSnapshot:
        return WorldSnapshot(
            snapshot_id=new_id("snapshot"),
            created_at_ms=now_ms(),
            facts=dict(self._facts),
        )
