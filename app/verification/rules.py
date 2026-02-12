from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass
class RuleResult:
    ok: bool
    rule_id: str
    reason: str
    violations: List[str]
    required_rechecks: List[str]
    debug: Dict[str, Any]


class VerificationRule(Protocol):
    rule_id: str
    stage: str  # "pre" or "post"

    def evaluate(self, ctx: Dict[str, Any]) -> RuleResult:
        ...


def _ok(rule_id: str, reason: str = "ok", debug: Optional[Dict[str, Any]] = None) -> RuleResult:
    return RuleResult(
        ok=True,
        rule_id=rule_id,
        reason=reason,
        violations=[],
        required_rechecks=[],
        debug=debug or {},
    )


def _fail(
    rule_id: str,
    reason: str,
    violations: List[str],
    required_rechecks: Optional[List[str]] = None,
    debug: Optional[Dict[str, Any]] = None,
) -> RuleResult:
    return RuleResult(
        ok=False,
        rule_id=rule_id,
        reason=reason,
        violations=violations,
        required_rechecks=required_rechecks or [],
        debug=debug or {},
    )


# -------------------------
# PRE rules (plan-time)
# -------------------------

class MacroShapeRule:
    rule_id = "pre.macro_shape"
    stage = "pre"

    def evaluate(self, ctx: Dict[str, Any]) -> RuleResult:
        selected = ctx.get("selected") or {}
        steps = None

        if isinstance(selected, dict):
            steps = selected.get("steps")
            if steps is None and isinstance(selected.get("plan"), dict):
                steps = selected["plan"].get("steps")

        if steps is None:
            return _fail(self.rule_id, "No steps found in selected plan", ["missing_steps"], ["rebuild_plan_shape"])

        if not isinstance(steps, list) or not steps:
            return _fail(self.rule_id, "Steps must be a non-empty list", ["invalid_steps"], ["rebuild_plan_steps"])

        bad = []
        for i, s in enumerate(steps):
            if not isinstance(s, dict):
                bad.append(f"step[{i}] not object")
                continue
            if not s.get("runner_id") or not s.get("action"):
                bad.append(f"step[{i}] missing runner_id/action")
        if bad:
            return _fail(self.rule_id, "Invalid step schema", ["; ".join(bad)], ["regenerate_steps"])

        return _ok(self.rule_id, "macro steps schema ok", {"step_count": len(steps)})


class AllowedActionsRule:
    rule_id = "pre.allowed_actions"
    stage = "pre"

    def __init__(self, allowed: Optional[List[str]] = None) -> None:
        self.allowed = set(allowed or ["run_cmd", "run_powershell", "open_app", "type_text", "key_combo"])

    def evaluate(self, ctx: Dict[str, Any]) -> RuleResult:
        selected = ctx.get("selected") or {}
        steps = selected.get("steps")
        if steps is None and isinstance(selected.get("plan"), dict):
            steps = selected["plan"].get("steps")
        if not isinstance(steps, list):
            return _ok(self.rule_id, "no steps to check")

        bad = []
        for i, s in enumerate(steps):
            action = (s or {}).get("action")
            if action and action not in self.allowed:
                bad.append(f"{i}:{action}")
        if bad:
            return _fail(self.rule_id, "Disallowed action present", ["disallowed_actions:" + ",".join(bad)], ["revise_actions"])

        return _ok(self.rule_id, "actions allowlisted", {"allowed": sorted(self.allowed)})


class ExecuteRequiresApprovalTokenRule:
    rule_id = "pre.execute_requires_approval_token"
    stage = "pre"

    def evaluate(self, ctx: Dict[str, Any]) -> RuleResult:
        execute_requested = bool(ctx.get("execute_requested"))
        approval_token_present = bool(ctx.get("approval_token_present"))

        if execute_requested and not approval_token_present:
            return _fail(
                self.rule_id,
                "execute requested but approval token missing",
                ["missing_approval_token"],
                ["request_approval_token"],
            )
        return _ok(self.rule_id, "approval gating ok")


class StateGateRule:
    rule_id = "pre.state_gate"
    stage = "pre"

    def evaluate(self, ctx: Dict[str, Any]) -> RuleResult:
        execute_requested = bool(ctx.get("execute_requested"))
        state = (ctx.get("state") or "DISARMED").upper()

        if execute_requested and state not in ("ARMED_IDLE", "ARMED_ACTIVE"):
            return _fail(
                self.rule_id,
                f"execute blocked by state={state}",
                [f"state_block:{state}"],
                ["arm_state"],
                {"state": state},
            )

        return _ok(self.rule_id, "state gate ok", {"state": state})


# -------------------------
# POST rules (receipt-time)
# -------------------------

class ReceiptMustExistWhenExecuteRule:
    rule_id = "post.receipt_exists"
    stage = "post"

    def evaluate(self, ctx: Dict[str, Any]) -> RuleResult:
        execute_attempted = bool(ctx.get("execute_attempted"))
        receipt = ctx.get("receipt")
        if execute_attempted and not receipt:
            return _fail(self.rule_id, "execute attempted but no receipt returned", ["missing_receipt"], ["retry_or_check_runner"])
        return _ok(self.rule_id, "receipt presence ok")


class BasicOutputNonEmptyRule:
    rule_id = "post.output_nonempty"
    stage = "post"

    def evaluate(self, ctx: Dict[str, Any]) -> RuleResult:
        receipt = ctx.get("receipt") or {}
        out = receipt.get("out") or receipt.get("output") or {}
        stdout = out.get("stdout")
        if stdout is None:
            return _ok(self.rule_id, "no stdout to validate")

        if isinstance(stdout, str) and stdout.strip() == "":
            return _fail(self.rule_id, "stdout empty", ["empty_stdout"], ["inspect_runner_output"])
        return _ok(self.rule_id, "stdout ok")


def default_rules() -> List[VerificationRule]:
    return [
        MacroShapeRule(),
        AllowedActionsRule(),
        ExecuteRequiresApprovalTokenRule(),
        StateGateRule(),
        ReceiptMustExistWhenExecuteRule(),
        BasicOutputNonEmptyRule(),
    ]
