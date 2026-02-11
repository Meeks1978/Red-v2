from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Literal, Dict, Any, List

from app.services.container import ServiceContainer
from app.memory.promotion import PromotionPolicy
from app.memory.decay import DecayPolicy
from app.memory.types import now_ms

router = APIRouter(prefix="/v1/memory", tags=["memory"])


@router.get("/stats")
def stats():
    items = list(ServiceContainer.memory_store.all())
    by_tier = {}
    for m in items:
        by_tier[m.tier] = by_tier.get(m.tier, 0) + 1
    return {"count": len(items), "by_tier": by_tier}


@router.get("/items")
def list_items(limit: int = 50):
    items = list(ServiceContainer.memory_store.all())[: max(0, min(limit, 500))]
    return [
        {
            "memory_id": m.memory_id,
            "namespace": m.namespace,
            "key": m.key,
            "tier": m.tier,
            "version": m.version,
            "confidence": m.confidence,
            "source": {"kind": m.source.kind, "ref": m.source.ref},
            "ttl_ms": m.ttl_ms,
            "updated_at_ms": m.updated_at_ms,
            "conflicts_with": m.conflicts_with,
        }
        for m in items
    ]


# --- Audit log ---

@router.get("/audit")
def audit(limit: int = 50):
    return ServiceContainer.memory_audit.list(limit=limit)


# --- Quarantine Review ---

@router.get("/quarantine")
def list_quarantine(limit: int = 50):
    items = [m for m in ServiceContainer.memory_store.all() if m.tier == "quarantine"]
    items = items[: max(0, min(limit, 500))]
    return [
        {
            "memory_id": m.memory_id,
            "namespace": m.namespace,
            "key": m.key,
            "tier": m.tier,
            "version": m.version,
            "confidence": m.confidence,
            "source": {"kind": m.source.kind, "ref": m.source.ref},
            "updated_at_ms": m.updated_at_ms,
            "conflicts_with": m.conflicts_with,
        }
        for m in items
    ]


class ResolveRequest(BaseModel):
    memory_id: str
    action: Literal["accept", "reject", "promote_canonical"] = "accept"
    note: Optional[str] = None


@router.post("/resolve")
def resolve(req: ResolveRequest):
    store = ServiceContainer.memory_store
    audit = ServiceContainer.memory_audit

    before = store.get(req.memory_id)
    if not before:
        return {"ok": False, "error": "memory_id not found"}

    if req.action == "reject":
        audit.log(event="resolve_reject", before_item=before, after_item=None, note=req.note, actor="user")
        store.delete(req.memory_id)
        return {"ok": True, "action": "reject", "deleted": req.memory_id}

    if req.action == "accept":
        after = before
        after.tier = "working"
        after.conflicts_with = []
        if req.note:
            after.notes["resolve_note"] = req.note
        store.upsert(after)
        audit.log(event="resolve_accept", before_item=before, after_item=after, note=req.note, actor="user")
        return {"ok": True, "action": "accept", "memory_id": after.memory_id, "tier": after.tier}

    if req.action == "promote_canonical":
        after = before
        after.tier = "canonical"
        if after.confidence < 0.85:
            after.confidence = 0.85
        after.conflicts_with = []
        if req.note:
            after.notes["resolve_note"] = req.note
        store.upsert(after)
        audit.log(event="resolve_promote_canonical", before_item=before, after_item=after, note=req.note, actor="user")
        return {"ok": True, "action": "promote_canonical", "memory_id": after.memory_id, "tier": after.tier}

    return {"ok": False, "error": "unknown action"}


# --- Decay Sweep ---

@router.post("/sweep")
def sweep(note: Optional[str] = None):
    """
    Manual sweep trigger. Logs summary into audit.
    """
    audit = ServiceContainer.memory_audit
    before_count = len(list(ServiceContainer.memory_store.all()))
    res = ServiceContainer.memory_curator.sweep_decay()  # type: ignore[attr-defined]
    after_count = len(list(ServiceContainer.memory_store.all()))

    audit.log(
        event="sweep",
        before_item=None,
        after_item=None,
        note=f"{note or ''} result={res} before_count={before_count} after_count={after_count}".strip(),
        actor="system",
    )
    return {"ok": True, "result": res}


# --- Explain ---

@router.get("/explain")
def explain(memory_id: Optional[str] = None, namespace: Optional[str] = None, key: Optional[str] = None):
    """
    Explain why a memory item is in its current tier/confidence.
    """
    store = ServiceContainer.memory_store
    item = None

    if memory_id:
        item = store.get(memory_id)
    elif namespace and key:
        items = store.get_by_key(namespace, key)
        item = items[0] if items else None

    if not item:
        return {"ok": False, "error": "not found (provide memory_id or namespace+key)"}

    promo = PromotionPolicy()
    decay = DecayPolicy()

    age_ms = now_ms() - item.updated_at_ms
    stale_ms = decay.canonical_stale_ms if item.tier == "canonical" else decay.working_stale_ms

    # Determine which promotion rule applies
    execute_semantic_rule = (
        item.namespace == "execute"
        and isinstance(item.key, str)
        and item.key.startswith("action:")
        and item.version >= promo.min_observations_for_canonical
        and isinstance(item.value, dict)
        and item.value.get("status_code") == 200
        and item.value.get("ok") is True
    )

    general_canonical_rule = (
        item.confidence >= promo.promote_to_canonical_min_confidence
        and item.version >= promo.min_observations_for_canonical
    )

    return {
        "ok": True,
        "item": {
            "memory_id": item.memory_id,
            "namespace": item.namespace,
            "key": item.key,
            "tier": item.tier,
            "version": item.version,
            "confidence": item.confidence,
            "updated_at_ms": item.updated_at_ms,
            "ttl_ms": item.ttl_ms,
            "conflicts_with": item.conflicts_with,
            "source": {"kind": item.source.kind, "ref": item.source.ref},
            "value": item.value,
        },
        "why": {
            "execute_semantic_rule_met": execute_semantic_rule,
            "general_canonical_rule_met": general_canonical_rule,
            "promotion_thresholds": {
                "working_confidence": promo.promote_to_working_min_confidence,
                "canonical_confidence": promo.promote_to_canonical_min_confidence,
                "canonical_min_observations": promo.min_observations_for_canonical,
            },
            "staleness": {
                "age_ms": age_ms,
                "stale_after_ms": stale_ms,
                "is_stale": age_ms > stale_ms,
            },
        },
    }
