from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.memory.types import MemoryItem, MemorySource, new_id, now_ms
from app.memory.store import MemoryStore
from app.memory.expiration import MemoryExpiration, ExpirationPolicy
from app.memory.conflict import MemoryConflictResolver, Conflict
from app.memory.promotion import MemoryPromotion, PromotionPolicy


@dataclass
class IngestResult:
    item: MemoryItem
    conflicts: List[Conflict]
    updated_existing: bool = False


class MemoryCurator:
    """
    BU-3: Memory hygiene and lifecycle manager with confidence accumulation.

    Key behaviors:
    - TTL defaults applied
    - If same (namespace,key) with equivalent value: update existing item (version++)
      and adjust confidence (accumulation) instead of creating a new memory_id.
    - If value differs: quarantine incoming + conflict links.
    - Promotion runs after confidence adjustment.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.expiration = MemoryExpiration(ExpirationPolicy())
        self.conflicts = MemoryConflictResolver()
        self.promotion = MemoryPromotion(PromotionPolicy())

    # --- Confidence accumulation policy (Phase-0) ---
    def _accumulate_confidence(self, prior: float, incoming: float) -> float:
        """
        Deterministic heuristic:
        - Treat incoming >= 0.75 as reinforcing evidence
        - Treat incoming <= 0.45 as negative evidence
        - Otherwise blend gently toward incoming

        Keeps confidence within [0.05, 0.98] to avoid false certainty.
        """
        p = float(prior)
        inc = float(incoming)

        if inc >= 0.75:
            # reinforce: +0.05, but diminishing as we approach 0.95
            bump = 0.05 if p < 0.90 else 0.02
            return min(0.98, max(p, inc) + bump)

        if inc <= 0.45:
            # penalize
            return max(0.05, min(p, inc) - 0.10)

        # mild blend toward incoming
        blended = (0.85 * p) + (0.15 * inc)
        return min(0.98, max(0.05, blended))

    def _equivalent(self, a: object, b: object) -> bool:
        # Semantic equivalence: ignore dynamic fields (latency, trace_id, timestamps)
        if not isinstance(a, dict) or not isinstance(b, dict):
            return a == b
        return (
            a.get('status_code') == b.get('status_code') and
            a.get('ok') == b.get('ok') and
            a.get('action_key') == b.get('action_key')
        )
        # Ignore latency and dynamic fields.
        if not isinstance(a, dict) or not isinstance(b, dict):
            return a == b

        return (
            a.get("status_code") == b.get("status_code") and
            a.get("ok") == b.get("ok") and
            a.get("trace_id") == b.get("trace_id")
        )

    def ingest(
        self,
        *,
        namespace: str,
        key: str,
        value: Any,
        source_kind: str,
        source_ref: str,
        confidence: float = 0.5,
        tags: Optional[List[str]] = None,
        ttl_ms: Optional[int] = None,
        tier: str = "ephemeral",
    ) -> IngestResult:

        existing = self.store.get_by_key(namespace, key)

        # If we already have an equivalent value, update the best candidate in place
        for ex in existing:
            if ex.tier == "quarantine":
                continue
            if self._equivalent(ex.value, value):
                # in-place update (same memory_id)
                ex.version += 1
                ex.updated_at_ms = now_ms()
                ex.source = MemorySource(kind=source_kind, ref=source_ref)
                ex.tags = sorted(set(ex.tags + (tags or [])))

                # TTL: keep existing TTL if present, else apply defaults/incoming
                if ex.ttl_ms is None:
                    ex.ttl_ms = ttl_ms
                    ex = self.expiration.apply_default_ttl(ex)

                # Confidence accumulation
                ex.confidence = self._accumulate_confidence(ex.confidence, confidence)

                # Tier: preserve highest tier unless policy promotes further
                # (If someone passed tier="working" and ex was ephemeral, allow that)
                if ex.tier == "ephemeral" and tier in ("working", "canonical"):
                    ex.tier = tier

                ex = self.promotion.promote(ex)

                self.store.upsert(ex)
                return IngestResult(item=ex, conflicts=[], updated_existing=True)

        # No equivalent found -> create new item
        item = MemoryItem(
            memory_id=new_id("mem"),
            namespace=namespace,
            key=key,
            value=value,
            created_at_ms=now_ms(),
            updated_at_ms=now_ms(),
            source=MemorySource(kind=source_kind, ref=source_ref),
            ttl_ms=ttl_ms,
            confidence=float(confidence),
            tags=tags or [],
            tier=tier,
        )

        item = self.expiration.apply_default_ttl(item)

        # Conflict path if same key exists but values differ
        item, conflicts = self.conflicts.detect_and_resolve(existing, item)

        item = self.promotion.promote(item)

        self.store.upsert(item)
        return IngestResult(item=item, conflicts=conflicts, updated_existing=False)

    def sweep_expired(self) -> int:
        expired_ids: List[str] = []
        for m in list(self.store.all()):
            if self.expiration.should_expire(m):
                expired_ids.append(m.memory_id)

        for mid in expired_ids:
            self.store.delete(mid)

        return len(expired_ids)

# --- BU-3 Decay Sweep ---
from app.memory.decay import MemoryDecay, DecayPolicy

def _curator_decay_init(self):
    if not hasattr(self, "decay"):
        self.decay = MemoryDecay(DecayPolicy())

# Attach dynamically (keeps this EOF-safe without rewriting whole file)
MemoryCurator._decay_init = _curator_decay_init  # type: ignore[attr-defined]

def sweep_decay(self) -> dict:
    """
    Applies decay/demotion to stale items and deletes expired items.
    Phase-0: deterministic, manual trigger.
    """
    self._decay_init()  # type: ignore[attr-defined]

    expired_deleted = 0
    changed = 0
    demoted = 0

    # delete expired
    expired_deleted = self.sweep_expired()

    # decay + demotion
    for m in list(self.store.all()):
        before_tier = m.tier
        before_conf = m.confidence

        m2, did_change, note = self.decay.apply(m)  # type: ignore[attr-defined]
        if did_change:
            changed += 1
            if before_tier != m2.tier:
                demoted += 1
            m2.updated_at_ms = now_ms()
            self.store.upsert(m2)

    return {
        "expired_deleted": expired_deleted,
        "changed": changed,
        "demoted": demoted,
    }

MemoryCurator.sweep_decay = sweep_decay  # type: ignore[attr-defined]
