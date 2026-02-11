from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.contracts.intent import IntentEnvelope
from app.contracts.advisory import AdvisoryResponse, ReasonSurface
from app.contracts.plan import PlanBundle
from app.contracts.execution import ExecutionPlan, ExecutionResult, BoundStep
from app.contracts.verification import VerificationReport, VerificationViolation


def now_ms() -> int:
    return int(time.time() * 1000)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class OrchestrationContext:
    trace_id: str
    world: Dict[str, Any]
    memory: Dict[str, Any]
    semantic: Dict[str, Any]
    governance: Dict[str, Any]
    budgets: Dict[str, Any]


@dataclass
class OrchestrationOutput:
    ok: bool
    trace_id: str
    advisory: AdvisoryResponse
    bundle: PlanBundle
    bound: Dict[str, Any]
    verification_pre: VerificationReport
    execution: Optional[ExecutionResult]
    verification_post: Optional[VerificationReport]
    reason_surface: ReasonSurface
    debug: Dict[str, Any]


class OrchestratorEngine:
    """
    Orchestrates the 9 engines. This is the "Reasoning Core glue".

    Hard rules:
    - Default is NO execution.
    - Execution happens only when explicitly requested AND executor is enabled AND governance state allows.
    - Always returns a trust surface.
    """

    def __init__(self, engines, core_container) -> None:
        self.e = engines
        self.core = core_container

    def _gather_ctx(self, trace_id: str) -> OrchestrationContext:
        # World snapshot (BU-4 will enrich later)
        try:
            world_snapshot = self.e.world.snapshot()
            world = {"ts_ms": world_snapshot.ts_ms, "facts_count": len(getattr(world_snapshot, "facts", {}) or {})}
        except Exception as ex:
            world = {"error": str(ex)[:200]}

        # Memory stats (BU-3 already)
        try:
            mem_stats = getattr(self.core, "memory_store", None)
            # you already have /v1/memory/stats; here we just report runtime counters
            memory = {"note": "use /v1/memory/stats for authoritative counts"}
        except Exception as ex:
            memory = {"error": str(ex)[:200]}

        # Semantic status (BU-3 semantic)
        try:
            semantic_enabled = bool(getattr(self.core, "semantic_memory", None))
            semantic = {"enabled": semantic_enabled}
        except Exception as ex:
            semantic = {"error": str(ex)[:200]}

        # Governance state (minimal: your state machine already exists)
        try:
            governance = {"state": getattr(self.core, "state", None)}
        except Exception:
            governance = {"state": None}

        budgets = {
            "semantic_budget_ms": int(getattr(self.core, "runtime", {}).get("semantic_budget_ms", 50)) if hasattr(self.core, "runtime") else 50
        }

        return OrchestrationContext(
            trace_id=trace_id,
            world=world,
            memory=memory,
            semantic=semantic,
            governance=governance,
            budgets=budgets,
        )

    def reason_only(self, intent_text: str, *, trace_id: Optional[str] = None) -> OrchestrationOutput:
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:10]}"
        ctx = self._gather_ctx(trace_id)

        intent = IntentEnvelope(
            intent_id=new_id("intent"),
            text=intent_text,
            created_at_ms=now_ms(),
            trace_id=trace_id,
        )

        advisory = self.e.advisory.advise(intent, ctx.__dict__)
        bundle = self.e.planning.plan(intent, ctx.__dict__)

        # Bind the first plan's steps into a macro-like structure (dry bind)
        bound_steps = []
        for s in bundle.selected.steps:
            # scaffold: tool_router expects dict runner/action/args; we leave placeholders
            bound_steps.append({"runner_id": "ai-laptop", "action": "run_cmd", "args": {"cmd": ["whoami"]}, "step_id": s.step_id})

        bound = {"steps": bound_steps}

        verification_pre = self.e.verifier.verify({
            "phase": "pre",
            "trace_id": trace_id,
            "intent": intent_text,
            "plan_id": bundle.selected.plan_id,
            "steps": bound_steps,
        })

        rs = advisory.reason_surface

        return OrchestrationOutput(
            ok=True,
            trace_id=trace_id,
            advisory=advisory,
            bundle=bundle,
            bound=bound,
            verification_pre=verification_pre,
            execution=None,
            verification_post=None,
            reason_surface=rs,
            debug={"mode": "reason_only"},
        )

    def act(self, intent_text: str, *, approval_token: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None, execute: bool = False) -> OrchestrationOutput:
        # Build plan as above
        base = self.reason_only(intent_text, trace_id=trace_id)
        trace_id = base.trace_id

        # Decide execution gating
        exec_enabled = bool(getattr(self.e.executor, "enabled", False))
        if not execute:
            return base

        if not exec_enabled:
            # return as blocked with explicit reason surface
            rs = ReasonSurface(
                reason="Execution blocked: ExecutorEngine disabled.",
                confidence=0.2,
                what_would_change_my_mind=["Enable executor explicitly and enter ARMED_ACTIVE."],
            )
            base.ok = False
            base.reason_surface = rs
            base.debug["blocked"] = "executor_disabled"
            return base

        if approval_token is None:
            rs = ReasonSurface(
                reason="Execution blocked: approval_token missing.",
                confidence=0.2,
                what_would_change_my_mind=["Provide approval_token from /approval/request."],
            )
            base.ok = False
            base.reason_surface = rs
            base.debug["blocked"] = "missing_approval"
            return base

        # Convert bound steps to ExecutionPlan
        steps = []
        for st in base.bound.get("steps", []):
            steps.append(BoundStep(runner_id=st["runner_id"], action=st["action"], args=st["args"]))

        exec_plan = ExecutionPlan(
            trace_id=trace_id,
            plan_id=base.bundle.selected.plan_id,
            steps=steps,
            approval_token=approval_token,
            idempotency_key=f"idem:{trace_id}",
        )

        execution = self.e.executor.execute(exec_plan, {"trace_id": trace_id})
        verification_post = self.e.verifier.verify({
            "phase": "post",
            "trace_id": trace_id,
            "execution_ok": execution.ok,
            "error": execution.error,
        })

        # Memory ingest hook (placeholder): you already ingest in middleware; here just emit event skeleton
        try:
            self.e.memory.ingest_event({"kind": "orchestrator_execution", "trace_id": trace_id, "ok": execution.ok})
        except Exception:
            pass

        # Observer tick (bounded)
        try:
            self.e.observer.tick({"trace_id": trace_id})
        except Exception:
            pass

        base.execution = execution
        base.verification_post = verification_post
        base.debug["mode"] = "act"
        return base
