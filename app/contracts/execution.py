from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class BoundStep:
    runner_id: str
    action: str
    args: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ExecutionPlan:
    trace_id: str
    plan_id: str
    steps: List[BoundStep] = field(default_factory=list)
    approval_token: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None

@dataclass(frozen=True)
class StepReceipt:
    step_index: int
    ok: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    receipts: List[StepReceipt] = field(default_factory=list)
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
