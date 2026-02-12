from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.world.store import WorldStore
from app.world.types import now_ms


class DriftEvent(BaseModel):
    kind: str = "world_drift_fingerprint_changed"
    ts_ms: int = Field(default_factory=now_ms)
    prev_fingerprint: Optional[str] = None
    fingerprint: str
    detail: Dict[str, Any] = Field(default_factory=dict)


def _as_entity_dict(e: Any) -> Dict[str, Any]:
    """
    Best-effort object→dict. Supports:
    - dict
    - Pydantic v2 (model_dump)
    - Pydantic v1 (dict)
    - plain objects with __dict__
    Never raises.
    """
    if e is None:
        return {}
    if isinstance(e, dict):
        return e
    md = getattr(e, "model_dump", None)
    if callable(md):
        try:
            return md()
        except Exception:
            return {}
    dct = getattr(e, "dict", None)
    if callable(dct):
        try:
            return dct()
        except Exception:
            return {}
    try:
        return dict(getattr(e, "__dict__", {}) or {})
    except Exception:
        return {}


def _fingerprint_entities(ents: List[Any]) -> str:
    """
    Deterministic fingerprint of entity identity + update timestamp.
    Uses only stable fields; never raises.
    """
    rows: List[Dict[str, Any]] = []
    for e in ents or []:
        d = _as_entity_dict(e)
        # tolerate multiple possible field names
        entity_id = d.get("entity_id") or d.get("id") or d.get("uid") or "unknown"
        updated = (
            d.get("updated_at_ms")
            or d.get("updated_at")
            or d.get("ts_ms")
            or d.get("created_at_ms")
            or 0
        )
        try:
            updated = int(updated)
        except Exception:
            updated = 0
        rows.append({"id": str(entity_id), "u": updated})

    rows.sort(key=lambda r: (r["id"], r["u"]))
    blob = json.dumps(rows, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


class DriftDetector:
    """
    Phase-7 safe drift scaffold:
    - fingerprint over entities
    - emits a DriftEvent when fingerprint changes
    - never raises
    """

    def __init__(self, store: WorldStore) -> None:
        self.store = store
        self._last_fingerprint: Optional[str] = None
        self._last_ts: Optional[int] = None

    def compute(self, limit_entities: int = 50) -> Dict[str, Any]:
        try:
            ents = self.store.list_entities(limit=int(limit_entities))
        except Exception:
            ents = []

        try:
            fp = _fingerprint_entities(ents)
        except Exception:
            fp = "error00000000"

        events: List[Dict[str, Any]] = []
        if self._last_fingerprint is None:
            # First run: establish baseline, do not emit
            self._last_fingerprint = fp
            self._last_ts = now_ms()
            return {"ok": True, "fingerprint": fp, "drift_events": [], "count": 0}

        if fp != self._last_fingerprint:
            ev = DriftEvent(
                prev_fingerprint=self._last_fingerprint,
                fingerprint=fp,
                detail={"from": self._last_fingerprint, "to": fp},
            )
            try:
                events.append(ev.model_dump())
            except Exception:
                events.append({"kind": ev.kind, "fingerprint": fp, "prev_fingerprint": self._last_fingerprint})

            self._last_fingerprint = fp
            self._last_ts = now_ms()

        return {"ok": True, "fingerprint": fp, "drift_events": events, "count": len(events)}
