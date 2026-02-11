from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass(frozen=True)
class ModelProfile:
    name: str
    kind: str  # reasoning | coder | vision | embed
    trust: float = 0.5

class ModelRegistry:
    def __init__(self) -> None:
        self._models: Dict[str, ModelProfile] = {}

    def register(self, profile: ModelProfile) -> None:
        self._models[profile.name] = profile

    def get(self, name: str) -> Optional[ModelProfile]:
        return self._models.get(name)
