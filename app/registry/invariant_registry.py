from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Dict, List

@dataclass(frozen=True)
class Invariant:
    name: str
    check: Callable[[], bool]
    description: str = ""

class InvariantRegistry:
    def __init__(self) -> None:
        self._inv: Dict[str, Invariant] = {}

    def register(self, inv: Invariant) -> None:
        self._inv[inv.name] = inv

    def list(self) -> List[Invariant]:
        return list(self._inv.values())
