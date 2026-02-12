from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.verification.rules import RuleResult, VerificationRule, default_rules


@dataclass
class VerificationReport:
    ok: bool
    stage: str
    reason: str
    violations: List[str]
    required_rechecks: List[str]
    rule_results: List[RuleResult]
    debug: Dict[str, Any]


class VerificationEngine:
    """
    Deterministic verifier (no LLM).
    """

    def __init__(self, rules: Optional[List[VerificationRule]] = None) -> None:
        self.rules = rules or default_rules()

    def verify(self, *, stage: str, ctx: Dict[str, Any]) -> VerificationReport:
        results: List[RuleResult] = []
        violations: List[str] = []
        rechecks: List[str] = []
        ok = True

        for rule in self.rules:
            if getattr(rule, "stage", None) != stage:
                continue
            try:
                rr = rule.evaluate(ctx)
            except Exception as e:
                rr = RuleResult(
                    ok=False,
                    rule_id=getattr(rule, "rule_id", "unknown"),
                    reason=f"rule exception: {e}",
                    violations=["rule_exception"],
                    required_rechecks=["inspect_rule"],
                    debug={"exc": str(e)},
                )
            results.append(rr)
            if not rr.ok:
                ok = False
                violations.extend(rr.violations)
                rechecks.extend(rr.required_rechecks)

        reason = "ok" if ok else f"{stage} verification failed"
        return VerificationReport(
            ok=ok,
            stage=stage,
            reason=reason,
            violations=violations,
            required_rechecks=rechecks,
            rule_results=results,
            debug={"rules_run": [r.rule_id for r in results]},
        )
