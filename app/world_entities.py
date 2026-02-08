from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List

DEFAULT_PATH = os.getenv("WORLD_ENTITIES_PATH", "/red/data/entities.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_parent(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Entity:
    entity_id: str
    kind: str  # node|service|device|person|runner etc.
    display_name: str
    tags: List[str]
    capabilities: Dict[str, Any]
    last_seen: Optional[str] = None
    status: str = "UNKNOWN"  # OK|DEGRADED|DOWN|UNKNOWN
    meta: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "kind": self.kind,
            "display_name": self.display_name,
            "tags": self.tags,
            "capabilities": self.capabilities,
            "last_seen": self.last_seen,
            "status": self.status,
            "meta": self.meta or {},
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Entity":
        return Entity(
            entity_id=d["entity_id"],
            kind=d.get("kind", "unknown"),
            display_name=d.get("display_name", d["entity_id"]),
            tags=list(d.get("tags", [])),
            capabilities=dict(d.get("capabilities", {})),
            last_seen=d.get("last_seen"),
            status=d.get("status", "UNKNOWN"),
            meta=dict(d.get("meta", {})),
        )


class EntityRegistry:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        _ensure_parent(self.path)
        if not Path(self.path).exists():
            self._write({"entities": {}})

    def _read(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: Dict[str, Any]) -> None:
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    def list_entities(self) -> List[Dict[str, Any]]:
        data = self._read()
        ents = data.get("entities", {})
        return [Entity.from_dict(v).to_dict() for v in ents.values()]

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        data = self._read()
        ent = data.get("entities", {}).get(entity_id)
        return Entity.from_dict(ent).to_dict() if ent else None

    def upsert(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        data = self._read()
        ents = data.setdefault("entities", {})
        e = Entity.from_dict(entity)
        ents[e.entity_id] = e.to_dict()
        self._write(data)
        return e.to_dict()

    def touch(self, entity_id: str, status: str, meta_patch: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = self._read()
        ents = data.setdefault("entities", {})
        cur = ents.get(entity_id)
        if not cur:
            # auto-create minimal entity if missing
            cur = Entity(
                entity_id=entity_id,
                kind="service",
                display_name=entity_id,
                tags=[],
                capabilities={},
            ).to_dict()

        cur["last_seen"] = _now_iso()
        cur["status"] = status
        if meta_patch:
            cur.setdefault("meta", {})
            cur["meta"].update(meta_patch)
        ents[entity_id] = cur
        self._write(data)
        return cur
