from __future__ import annotations

import threading
from typing import Dict, Optional

from .models import IntentRecord


class IntentStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_id: Dict[str, IntentRecord] = {}

    def put(self, rec: IntentRecord) -> None:
        with self._lock:
            self._by_id[rec.intent_id] = rec

    def get(self, intent_id: str) -> Optional[IntentRecord]:
        with self._lock:
            return self._by_id.get(intent_id)

    def update(self, intent_id: str, rec: IntentRecord) -> None:
        with self._lock:
            if intent_id not in self._by_id:
                raise KeyError(f"intent_id not found: {intent_id}")
            self._by_id[intent_id] = rec
