from __future__ import annotations

import json
import os
import threading
from typing import Dict, Iterable, List, Optional

from app.memory.types import MemoryItem, MemorySource


class MemoryStore:
    def upsert(self, item: MemoryItem) -> None:
        raise NotImplementedError

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        raise NotImplementedError

    def get_by_key(self, namespace: str, key: str) -> List[MemoryItem]:
        raise NotImplementedError

    def all(self) -> Iterable[MemoryItem]:
        raise NotImplementedError

    def delete(self, memory_id: str) -> None:
        raise NotImplementedError


class JsonFileStore(MemoryStore):
    """
    Durable MemoryStore backed by a single JSON file.

    Format:
    {
      "items": {
        "<memory_id>": { ...MemoryItem fields... },
        ...
      }
    }
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        # ensure file exists
        if not os.path.exists(self.path):
            self._write({"items": {}})

    def _read(self) -> Dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f) or {"items": {}}
        except FileNotFoundError:
            return {"items": {}}

    def _write(self, data: Dict) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def _to_dict(self, item: MemoryItem) -> Dict:
        return {
            "memory_id": item.memory_id,
            "namespace": item.namespace,
            "key": item.key,
            "value": item.value,
            "created_at_ms": item.created_at_ms,
            "updated_at_ms": item.updated_at_ms,
            "source": {"kind": item.source.kind, "ref": item.source.ref},
            "ttl_ms": item.ttl_ms,
            "confidence": item.confidence,
            "tags": item.tags,
            "tier": item.tier,
            "version": item.version,
            "conflicts_with": item.conflicts_with,
            "notes": item.notes,
        }

    def _from_dict(self, d: Dict) -> MemoryItem:
        src = d.get("source") or {}
        return MemoryItem(
            memory_id=d["memory_id"],
            namespace=d["namespace"],
            key=d["key"],
            value=d.get("value"),
            created_at_ms=d.get("created_at_ms", 0),
            updated_at_ms=d.get("updated_at_ms", 0),
            source=MemorySource(kind=src.get("kind", "unknown"), ref=src.get("ref", "unknown")),
            ttl_ms=d.get("ttl_ms"),
            confidence=float(d.get("confidence", 0.5)),
            tags=list(d.get("tags") or []),
            tier=d.get("tier", "ephemeral"),
            version=int(d.get("version", 1)),
            conflicts_with=list(d.get("conflicts_with") or []),
            notes=dict(d.get("notes") or {}),
        )

    def upsert(self, item: MemoryItem) -> None:
        with self._lock:
            data = self._read()
            items = data.setdefault("items", {})
            items[item.memory_id] = self._to_dict(item)
            self._write(data)

    def get(self, memory_id: str) -> Optional[MemoryItem]:
        with self._lock:
            data = self._read()
            items = data.get("items", {})
            d = items.get(memory_id)
            return self._from_dict(d) if d else None

    def get_by_key(self, namespace: str, key: str) -> List[MemoryItem]:
        with self._lock:
            data = self._read()
            out: List[MemoryItem] = []
            for d in (data.get("items", {}) or {}).values():
                if d.get("namespace") == namespace and d.get("key") == key:
                    out.append(self._from_dict(d))
            return out

    def all(self) -> Iterable[MemoryItem]:
        with self._lock:
            data = self._read()
            return [self._from_dict(d) for d in (data.get("items", {}) or {}).values()]

    def delete(self, memory_id: str) -> None:
        with self._lock:
            data = self._read()
            items = data.get("items", {})
            if memory_id in items:
                del items[memory_id]
                self._write(data)
