from __future__ import annotations

def _get_state_string() -> str:
    """
    Best-effort read of governance state.
    Must NEVER raise. Default to UNKNOWN (fail-closed).
    """
    try:
        # Common place in this repo: hard gate logic used by /v1/execute
        from app.world_state import get_state as _get_state  # type: ignore
        st = _get_state()
        if isinstance(st, dict):
            v = st.get("state") or st.get("mode") or st.get("value")
            if isinstance(v, str) and v:
                return v
    except Exception:
        pass
    try:
        # Alternate: state store object
        from app.world_state import STATE as _STATE  # type: ignore
        if hasattr(_STATE, "get"):
            v = _STATE.get("state")  # type: ignore
            if isinstance(v, str) and v:
                return v
    except Exception:
        pass
    return "UNKNOWN"

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.contracts.intent import IntentEnvelope
from app.contracts.advisory import AdvisoryResponse, ReasonSurface
from app.contracts.plan import PlanBundle
from app.contracts.execution import ExecutionPlan, ExecutionResult, BoundStep
from app.contracts.verification import VerificationReport

def now_ms() -> int:
    return int(time.time() * 1000)

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

@dataclass
class OrchestrationOutput:
    ok: bool
    trace_id: str
    advisory: AdvisoryResponse
    bundle: PlanBundle
    bound_steps: List[Dict[str, Any]]
    verification_pre: VerificationReport
    execution: Optional[ExecutionResult]
    verification_post: Optional[VerificationReport]
    reason_surface: ReasonSurface
    debug: Dict[str, Any]

class OrchestratorEngine:
    """
    Real engine sequencing (A+C):
      Advisory -> Planning -> Bind -> VerifyPre -> (optional Execute) -> VerifyPost
    """

    def __init__(self, engines, core_container) -> None:
        self.e = engines
        self.core = core_container

    def _ctx(self, trace_id: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        constraints = constraints or {}
        return {
            "trace_id": trace_id,
            "constraints": constraints,
            "memory": {"note": "use /v1/memory/* for authoritative"},
            "semantic": {"enabled": bool(getattr(self.core, "semantic_memory", None))},
            "budgets": {},
            "governance": {},
            "world": {},
        }

    def _bind_steps(self, bundle: PlanBundle) -> List[Dict[str, Any]]:
        # For now we bind a single safe placeholder, but we preserve structure.
        # Next step later is to bind based on step tool_hint/data.
        if not bundle.selected.steps:
            return []
        # Safe placeholder action (still whoami), but preserve selected step intent in args for trace/debug.
        desc = bundle.selected.steps[0].description
        return [{
            "step_id": bundle.selected.steps[0].step_id,
            "runner_id": "ai-laptop",
            "action": "run_cmd",
            "args": {"cmd": ["whoami"], "plan_step_desc": desc[:300]},
        }]

    def reason(self, text: str, *, trace_id: Optional[str] = None, constraints: Optional[Dict[str, Any]] = None) -> OrchestrationOutput:
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:10]}"
        ctx = self._ctx(trace_id, constraints=constraints)

        intent = IntentEnvelope(
            intent_id=new_id("intent"),
            text=text,
            created_at_ms=now_ms(),
            user_context={},
            constraints=constraints or {},
            trace_id=trace_id,
        )

        advisory = self.e.advisory.advise(intent, ctx)
        bundle = self.e.planning.plan(intent, ctx)
        bound_steps = self._bind_steps(bundle)

        # Verification pre uses a readable plan representation
        plan_text = f"{bundle.selected.summary}\nAssumptions: {bundle.selected.assumptions}\nSteps: {[s.description for s in bundle.selected.steps]}"
        verification_pre = self.e.verifier.verify_pre(
            intent=text,
            plan_text=plan_text,
            bound_steps=bound_steps,
            trace_id=trace_id,
        )

        # Trust surface: if verifier fails, lower confidence and explain
        rs = advisory.reason_surface
        if not verification_pre.ok:
            rs = ReasonSurface(
                reason="Plan failed verification_pre.",
                confidence=0.35,
                violated_assumptions=[],
                drift_keys=[],
                what_would_change_my_mind=["Fix verification violations", "Add missing assumptions/steps."],
            )

        return OrchestrationOutput(
            ok=verification_pre.ok,
            trace_id=trace_id,
            advisory=advisory,
            bundle=bundle,
            bound_steps=bound_steps,
            verification_pre=verification_pre,
            execution=None,
            verification_post=None,
            reason_surface=rs,
            debug={"mode": "reason", "planner_cost": (bundle.variants[0].cost if bundle.variants else {})},
        )

    def act(self, text: str, *, execute: bool = False, approval_token: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None) -> OrchestrationOutput:
        base = self.reason(text, trace_id=trace_id)
        if not execute:
            return base

        # --- BU-5 HARD STATE GATE ---
        # Execution is ONLY allowed in ARMED_ACTIVE (fail-closed).
        try:
            _state = _get_state_string()
        except Exception:
            _state = "UNKNOWN"
        if _state != "ARMED_ACTIVE":
            base.ok = False
            try:
                base.reason_surface.reason = f"Execution blocked: state={_state} (requires ARMED_ACTIVE)."
            except Exception:
                pass
            try:
                base.debug["blocked"] = "state_not_active"
                base.debug["state"] = _state
            except Exception:
                pass
            return base

        # Execution gating (kept strict)
        exec_enabled = bool(getattr(self.e.executor, "enabled", False))
        if not exec_enabled:
            base.ok = False

            # --- AUTO-CLOSE INTENT (BU-1) ---
            # Auto-close the intent inside orchestrator so humans never have to call /v1/intent/close manually.
            # This must NEVER break the request path.
            try:
                _intent_id = getattr(base, "intent_id", None) or getattr(base, "intent", None)
                if _intent_id:
                    _final_state = {
                        "ok": bool(getattr(base, "ok", False)),
                        "blocked": getattr(getattr(base, "debug", {}), "get", lambda _k, _d=None: _d)("blocked", None)
                        if isinstance(getattr(base, "debug", None), dict) else None,
                    }
                    _receipts = []
                    try:
                        _receipts.append({"kind": "orchestrator", "ok": bool(getattr(base, "ok", False))})
                    except Exception:
                        _receipts = []
            
                    _payload = {
                        "intent_id": _intent_id,
                        "final_state": _final_state,
                        "receipts": _receipts,
                    }
            
                    # Support multiple possible tracker APIs:
                    #   close(intent_id=..., final_state=..., receipts=...)
                    #   close(payload_dict)
                    _tracker = ServiceContainer.intent_tracker
                    try:
                        _tracker.close(**_payload)
                    except TypeError:
                        _tracker.close(_payload)
            except Exception:
                pass
            base.reason_surface = ReasonSurface(
                reason="Execution blocked: ExecutorEngine disabled.",
                confidence=0.2,
                what_would_change_my_mind=["Enable executor explicitly and enter ARMED_ACTIVE."],
            )
            base.debug["blocked"] = "executor_disabled"
            return base

        if approval_token is None:
            base.ok = False
            base.reason_surface = ReasonSurface(
                reason="Execution blocked: approval_token missing.",
                confidence=0.2,
                what_would_change_my_mind=["Provide approval_token from /approval/request."],
            )
            base.debug["blocked"] = "missing_approval"
            return base

        steps = [BoundStep(runner_id=s["runner_id"], action=s["action"], args=s["args"]) for s in base.bound_steps]
        exec_plan = ExecutionPlan(
            trace_id=base.trace_id,
            plan_id=base.bundle.selected.plan_id,
            steps=steps,
            approval_token=approval_token,
            idempotency_key=f"idem:{base.trace_id}",
        )

        verification_post = None
        execution = self.e.executor.execute(exec_plan, {"trace_id": base.trace_id})
        try:
            verification_post = self.e.verifier.verify_post(trace_id=base.trace_id, execution_ok=execution.ok, error=execution.error)
        except Exception as _e:
            # Must never crash request path
            verification_post = None
# Memory ingest hook (placeholder)
        try:
            self.e.memory.ingest_event({"kind": "orchestrator_execution", "trace_id": base.trace_id, "ok": execution.ok})
        except Exception:
            pass

        # Observer tick (bounded)
        try:
            self.e.observer.tick({"trace_id": base.trace_id})
        except Exception:
            pass

        base.execution = execution
        base.verification_post = verification_post
        base.ok = execution.ok and verification_post.ok
        base.debug["mode"] = "act"
        return base
