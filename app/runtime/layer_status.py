# red/app/runtime/layer_status.py
from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Dict, Optional, Literal

LayerStatus = Literal["not_started", "scaffolded", "wired", "tested", "shipped"]

@dataclass
class LayerState:
    status: LayerStatus
    last_check: Optional[str] = None
    detail: Optional[dict] = None

class LayerStatusStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._layers: Dict[int, LayerState] = {}

    def set(self, layer_id: int, status: LayerStatus, last_check: Optional[str] = None, detail: Optional[dict] = None) -> None:
        with self._lock:
            self._layers[layer_id] = LayerState(status=status, last_check=last_check, detail=detail)

    def get(self, layer_id: int) -> Optional[LayerState]:
        with self._lock:
            return self._layers.get(layer_id)

    def snapshot(self) -> Dict[int, dict]:
        with self._lock:
            return {
                lid: {
                    "status": st.status,
                    "last_check": st.last_check,
                    "detail": st.detail,
                }
                for lid, st in self._layers.items()
            }

layer_status_store = LayerStatusStore()
