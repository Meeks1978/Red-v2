from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.models.gateway import GATEWAY
from app.contracts.verification import VerificationReport, VerificationViolation


def _has_assumptions(plan_text: str) -> bool:
    return bool(re.search(r"assumption", plan_text, re.I)) or "assumptions" in plan_text.lower()


def _has_steps(plan_text: str) -> bool:
    return bool(re.search(r"\bstep\b", plan_text, re.I)) or bool(re.search(r"\d\.", plan_text))


class VerificationEngine:
    """
    Phase-7 verification: deterministic checks + optional model cross-check.
    No execution. Produces violations + required_rechecks.
    """

    def verify_pre(self, *, intent: str, plan_text: str, bound_steps: List[Dict[str, Any]], trace_id: str) -> VerificationReport:
        violations: List[VerificationViolation] = []

        if not intent.strip():
            violations.append(VerificationViolation(code="intent_empty", message="Intent text is empty."))

        if not plan_text.strip():
            violations.append(VerificationViolation(code="plan_empty", message="Plan text is empty."))

        if not _has_steps(plan_text):
            violations.append(VerificationViolation(code="plan_no_steps", message="Plan does not appear to contain steps."))

        if not _has_assumptions(plan_text):
            violations.append(VerificationViolation(code="plan_no_assumptions", message="Plan does not mention assumptions."))

        if not bound_steps:
            violations.append(VerificationViolation(code="no_bound_steps", message="No bound steps produced."))

        # Optional model cross-check (conservative)
        cross_debug: Dict[str, Any] = {}
        try:
            prompt = (
                "You are a strict verification engine.\n"
                "Check whether the plan is safe, complete, and matches the intent.\n"
                "Return a short JSON object with keys: ok(bool), issues(list[str])."
            )
            user = f"INTENT:\n{intent}\n\nPLAN:\n{plan_text}\n\nBOUND_STEPS:\n{bound_steps}\n"
            res = GATEWAY.chat(
                engine="verification",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user}],
                options={"temperature": 0.0},
            )
            cross_debug = {"model_used": res.used, "fallbacks": res.attempts, "raw": res.content[:800]}
            if res.ok and '"ok"' in res.content:
                # Don’t hard-parse yet; just flag if it obviously says issues
                if "false" in res.content.lower() and "issue" in res.content.lower():
                    violations.append(VerificationViolation(code="model_flags_issues", message="Verifier model flagged issues.", data={"raw": res.content[:800]}))
        except Exception as e:
            cross_debug = {"error": str(e)[:200]}

        ok = len(violations) == 0
        required = [v.code for v in violations]

        return VerificationReport(ok=ok, violations=violations, required_rechecks=required, debug={"cross_check": cross_debug})

    def verify_post(self, *, trace_id: str, execution_ok: bool, error: Optional[str]) -> VerificationReport:
        violations: List[VerificationViolation] = []
        if not execution_ok:
            violations.append(VerificationViolation(code="execution_failed", message="Execution did not succeed.", data={"error": error}))
        return VerificationReport(ok=(len(violations) == 0), violations=violations, required_rechecks=[v.code for v in violations], debug={"trace_id": trace_id})
