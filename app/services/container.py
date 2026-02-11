from __future__ import annotations
import os

from app.engines.advisory_engine import AdvisoryEngine
from app.services.intent_outcome import IntentOutcomeTracker, SuccessCriteriaEvaluator, PostIntentReflection
from app.trust.surface import TrustSurfaceBuilder


class ServiceContainer:
    """
    Simple DI container. Replace with your existing wiring if you have one.
    """
    def __init__(self) -> None:
        self.intent_outcome_tracker = IntentOutcomeTracker()
        self.success_evaluator = SuccessCriteriaEvaluator()
        self.post_reflector = PostIntentReflection()
        self.trust_surface = TrustSurfaceBuilder()

        self.advisory_engine = AdvisoryEngine(
            tracker=self.intent_outcome_tracker,
            evaluator=self.success_evaluator,
            reflector=self.post_reflector,
            trust_builder=self.trust_surface,
        )

from app.engines.world_engine import WorldEngine

# extend container
ServiceContainer.world_engine = WorldEngine()

from app.governance.assumption_verifier import AssumptionVerifier
from app.governance.uncertainty_gate import UncertaintyGate

ServiceContainer.assumption_verifier = AssumptionVerifier()
ServiceContainer.uncertainty_gate = UncertaintyGate()

from app.engines.executor_engine import GuardedExecutor

ServiceContainer.executor = GuardedExecutor()

from app.observer.shadow import ShadowObserver

# Shadow Observer (Phase 0) — OFF by default
ServiceContainer.shadow_observer = ShadowObserver(enabled=False, interval_sec=60)

from app.observer.collector import ShadowCollector
from app.observer.scheduler import ShadowObserverScheduler, SchedulerConfig

# Shadow Observer scheduler (Phase 0) — OFF by default
ServiceContainer.shadow_collector = ShadowCollector()
ServiceContainer.shadow_scheduler = ShadowObserverScheduler(
    SchedulerConfig(enabled=False, interval_sec=60, max_ticks=0, daemon=True),
    tick_fn=ServiceContainer.shadow_collector.tick,
)

# --- BU-3 Memory Hygiene ---
from app.memory.store import JsonFileStore
from app.memory.curator import MemoryCurator

if not hasattr(ServiceContainer, "memory_store"):
    ServiceContainer.memory_store = JsonFileStore(os.getenv("MEMORY_STORE_PATH", "/red/data/memory.json"))

if not hasattr(ServiceContainer, "memory_curator"):
    ServiceContainer.memory_curator = MemoryCurator(ServiceContainer.memory_store)

# --- BU-3 Audit Log ---
from app.memory.audit import MemoryAuditLog

if not hasattr(ServiceContainer, "memory_audit"):
    ServiceContainer.memory_audit = MemoryAuditLog()

# --- BU-3 Durable Memory Store (Option B) ---
from app.memory.store import JsonFileStore

_mem_path = os.getenv("MEMORY_STORE_PATH")
if _mem_path:
    ServiceContainer.memory_store = JsonFileStore(_mem_path)
    # Rebuild curator to point at durable store
    ServiceContainer.memory_curator = MemoryCurator(ServiceContainer.memory_store)

# --- BU-3 Durable Audit Log (Option B) ---
_audit_path = os.getenv("AUDIT_LOG_PATH", "/tmp/red_memory_audit.jsonl")
ServiceContainer.memory_audit = MemoryAuditLog(jsonl_path=_audit_path)

# --- Hybrid Semantic Layer (Qdrant) ---
from app.memory.semantic_qdrant import SemanticQdrant, QdrantConfig, HashEmbedder

_sem_url = os.getenv("QDRANT_URL", "")
_sem_enabled = os.getenv("ENABLE_SEMANTIC_MEMORY") == "true"

ServiceContainer.semantic_memory = None
if _sem_enabled and _sem_url:
    ServiceContainer.semantic_memory = SemanticQdrant(
        QdrantConfig(url=_sem_url, collection=os.getenv("QDRANT_COLLECTION", "red_memory_semantic")),
        HashEmbedder(dim=int(os.getenv("QDRANT_DIM", "384"))),
    )

# --- Runtime hardening: semantic circuit breaker + counters ---
from app.runtime.circuit_breaker import CircuitBreaker, BreakerConfig

if not hasattr(ServiceContainer, "runtime"):
    ServiceContainer.runtime = {
        "semantic_upsert_ok": 0,
        "semantic_upsert_fail": 0,
        "semantic_upsert_skip": 0,
        "semantic_upsert_budget_exceeded": 0,
        "semantic_last_upsert_ms": None,
        "semantic_last_error": None,
    }

if not hasattr(ServiceContainer, "semantic_breaker"):
    ServiceContainer.semantic_breaker = CircuitBreaker(
        BreakerConfig(
            max_failures=int(os.getenv("SEMANTIC_CB_FAILS", "5")),
            window_sec=int(os.getenv("SEMANTIC_CB_WINDOW_SEC", "60")),
            cooldown_sec=int(os.getenv("SEMANTIC_CB_COOLDOWN_SEC", "300")),
        )
    )
