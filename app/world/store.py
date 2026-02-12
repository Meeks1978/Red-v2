from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def now_ms() -> int:
    return int(time.time() * 1000)


def _default_world_path() -> str:
    return os.getenv("WORLD_STORE_PATH", "/red/data/world.db")


class WorldStore:
    """
    Minimal JSON-file backed world store.

    Phase-7 safe rules:
    - Never raise from basic read/write operations
    - Always tolerate schema drift + call-site drift (kwargs vs dict vs positional)
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or _default_world_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            self._write(
                {
                    "entities": {},      # entity_id -> dict
                    "relations": [],     # list[dict]
                    "events": [],        # list[dict]
                    "meta": {
                        "next_event_id": 1,
                        "fingerprint": None,
                        "last_event_ts": None,
                    },
                }
            )

    # -----------------
    # Low-level I/O
    # -----------------
    def _read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.db_path.read_text(encoding="utf-8"))
        except Exception:
            # hard-safe fallback
            return {
                "entities": {},
                "relations": [],
                "events": [],
                "meta": {"next_event_id": 1, "fingerprint": None, "last_event_ts": None},
            }

    def _write(self, data: Dict[str, Any]) -> None:
        try:
            tmp = self.db_path.with_suffix(self.db_path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.db_path)
        except Exception:
            # never raise
            pass

    # -----------------
    # Counts / stats
    # -----------------
    def count_entities(self) -> int:
        d = self._read()
        return int(len(d.get("entities", {}) or {}))

    def count_events(self) -> int:
        d = self._read()
        return int(len(d.get("events", []) or []))

    def count_relations(self) -> int:
        d = self._read()
        return int(len(d.get("relations", []) or []))

    def last_event_ts(self) -> Optional[int]:
        d = self._read()
        return d.get("meta", {}).get("last_event_ts")

    # -----------------
    # Entities
    # -----------------
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        d = self._read()
        return (d.get("entities", {}) or {}).get(entity_id)

    def list_entities(self, limit: int = 50) -> List[Dict[str, Any]]:
        d = self._read()
        ents = list((d.get("entities", {}) or {}).values())
        # newest-ish first if updated_at_ms exists
        ents.sort(key=lambda e: int(e.get("updated_at_ms", 0) or 0), reverse=True)
        return ents[: max(1, int(limit))]

    def upsert_entity(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Accepts any of:
        - upsert_entity(entity_id="x1", kind="generic", attrs={...}, ts_ms=..., confidence=..., seen=...)
        - upsert_entity("x1", {...attrs...})
        - upsert_entity({"entity_id":"x1","kind":"...","attrs":{...}, ...})
        """

        entity: Dict[str, Any] = {}

        # form 1: dict as first arg
        if args and isinstance(args[0], dict):
            entity = dict(args[0])
        # form 2: positional entity_id (+ optional attrs dict)
        elif args and isinstance(args[0], str):
            entity_id = args[0]
            attrs = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            entity = {"entity_id": entity_id, "attrs": attrs}
        else:
            # form 3: kwargs
            entity = {}

        # merge kwargs on top (lets call-sites override)
        entity.update(kwargs)

        # normalize keys (call-site drift tolerant)
        entity_id = entity.get("entity_id") or entity.get("id") or entity.get("entityId")
        if not entity_id:
            # last resort: never raise; create a stable-ish id
            entity_id = f"entity_{now_ms()}"
        kind = entity.get("kind") or "generic"
        attrs = entity.get("attrs") or entity.get("payload") or {}
        if not isinstance(attrs, dict):
            attrs = {"value": attrs}

        ts = entity.get("ts_ms")
        if ts is None:
            ts = now_ms()

        conf = entity.get("confidence", 0.5)
        try:
            conf = float(conf)
        except Exception:
            conf = 0.5

        seen = bool(entity.get("seen", True))

        # write
        d = self._read()
        ents = d.get("entities", {}) or {}
        existing = ents.get(entity_id, {})
        merged = dict(existing)
        merged.update(
            {
                "entity_id": str(entity_id),
                "kind": str(kind),
                "attrs": dict(attrs),
                "confidence": conf,
                "seen": seen,
                "updated_at_ms": int(ts),
            }
        )
        ents[str(entity_id)] = merged
        d["entities"] = ents
        self._write(d)
        return merged

    # -----------------
    # Relations (minimal)
    # -----------------
    def list_relations(self, limit: int = 50) -> List[Dict[str, Any]]:
        d = self._read()
        rels = list(d.get("relations", []) or [])
        rels = rels[-max(1, int(limit)) :]
        return rels

    def upsert_relation(self, src_id: str, dst_id: str, rel: str = "related_to", attrs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        d = self._read()
        rels = d.get("relations", []) or []
        rec = {
            "src_id": str(src_id),
            "dst_id": str(dst_id),
            "rel": str(rel),
            "attrs": dict(attrs or {}),
            "ts_ms": now_ms(),
        }
        rels.append(rec)
        d["relations"] = rels[-5000:]
        self._write(d)
        return rec

    # -----------------
    # Events
    # -----------------
    def append_event(
        self,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
        entity_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        source: str = "world",
        ts_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        d = self._read()
        meta = d.get("meta", {}) or {}
        eid = int(meta.get("next_event_id", 1) or 1)

        ts = int(ts_ms or now_ms())
        ev = {
            "event_id": eid,
            "kind": str(kind),
            "entity_id": entity_id,
            "payload": dict(payload or {}),
            "trace_id": trace_id,
            "source": str(source),
            "created_at_ms": ts,
        }

        events = d.get("events", []) or []
        events.append(ev)
        d["events"] = events[-10000:]

        meta["next_event_id"] = eid + 1
        meta["last_event_ts"] = ts
        d["meta"] = meta
        self._write(d)
        return ev

    def list_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        d = self._read()
        events = list(d.get("events", []) or [])
        return events[-max(1, int(limit)) :]

    # -----------------
    # Drift (deterministic)
    # -----------------
    def fingerprint(self) -> str:
        d = self._read()
        ents = d.get("entities", {}) or {}
        # stable string based on ids + updated_at
        items: List[Tuple[str, int]] = []
        for k, v in ents.items():
            try:
                items.append((str(k), int(v.get("updated_at_ms", 0) or 0)))
            except Exception:
                items.append((str(k), 0))
        items.sort()
        s = "|".join([f"{k}:{t}" for k, t in items])
        # simple hash (no deps)
        h = 2166136261
        for ch in s.encode("utf-8"):
            h ^= ch
            h = (h * 16777619) & 0xFFFFFFFF
        return f"{h:08x}"

    def drift_check(self) -> Dict[str, Any]:
        d = self._read()
        meta = d.get("meta", {}) or {}
        fp = self.fingerprint()
        prev = meta.get("fingerprint")

        drift_events: List[Dict[str, Any]] = []
        if prev is not None and prev != fp:
            drift_events.append(
                {
                    "kind": "world_drift_fingerprint_changed",
                    "prev": prev,
                    "curr": fp,
                    "ts_ms": now_ms(),
                }
            )
        meta["fingerprint"] = fp
        d["meta"] = meta
        self._write(d)
        return {"ok": True, "fingerprint": fp, "drift_events": drift_events, "count": len(drift_events)}
