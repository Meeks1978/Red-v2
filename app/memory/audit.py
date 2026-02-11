from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from app.memory.types import MemoryItem


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class AuditEvent:
    ts_ms: int
    event: str                # sweep | resolve_accept | resolve_reject | resolve_promote_canonical | other
    memory_id: Optional[str]
    namespace: Optional[str]
    key: Optional[str]
    before: Optional[Dict[str, Any]]
    after: Optional[Dict[str, Any]]
    note: Optional[str] = None
    actor: str = "system"     # later: user identity
    trace_id: Optional[str] = None


class MemoryAuditLog:
    """
    Phase-0 audit log:
    - in-memory list
    - optional JSONL append file for persistence inside container
    """

    def __init__(self, jsonl_path: Optional[str] = "/tmp/red_memory_audit.jsonl") -> None:
        self._events: List[AuditEvent] = []
        self._jsonl_path = jsonl_path

    def _item_snapshot(self, item: Optional[MemoryItem]) -> Optional[Dict[str, Any]]:
        if item is None:
            return None
        return {
            "tier": item.tier,
            "confidence": item.confidence,
            "version": item.version,
            "updated_at_ms": item.updated_at_ms,
            "ttl_ms": item.ttl_ms,
            "conflicts_with": list(item.conflicts_with),
            "source": {"kind": item.source.kind, "ref": item.source.ref},
        }

    def log(
        self,
        *,
        event: str,
        before_item: Optional[MemoryItem],
        after_item: Optional[MemoryItem],
        note: Optional[str] = None,
        actor: str = "system",
        trace_id: Optional[str] = None,
    ) -> None:
        ev = AuditEvent(
            ts_ms=now_ms(),
            event=event,
            memory_id=(after_item.memory_id if after_item else (before_item.memory_id if before_item else None)),
            namespace=(after_item.namespace if after_item else (before_item.namespace if before_item else None)),
            key=(after_item.key if after_item else (before_item.key if before_item else None)),
            before=self._item_snapshot(before_item),
            after=self._item_snapshot(after_item),
            note=note,
            actor=actor,
            trace_id=trace_id,
        )
        self._events.append(ev)

        # Best-effort JSONL append
        if self._jsonl_path:
            try:
                with open(self._jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(ev)) + "\n")
            except Exception:
                pass

    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        limit = max(1, min(limit, 500))
        return [asdict(e) for e in self._events[-limit:]]
