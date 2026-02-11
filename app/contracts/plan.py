from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class SuccessCriteria:
    description: str
    required_signals: List[str] = field(default_factory=list)
    must_not_happen: List[str] = field(default_factory=list)

@dataclass(frozen=True)
class PlanStep:
    step_id: str
    description: str
    tool_hint: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class Plan:
    plan_id: str
    intent_id: str
    summary: str
    assumptions: List[str] = field(default_factory=list)
    success: Optional[SuccessCriteria] = None
    steps: List[PlanStep] = field(default_factory=list)

@dataclass(frozen=True)
class PlanVariant:
    name: str
    plan: Plan
    cost: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class PlanBundle:
    selected: Plan
    variants: List[PlanVariant] = field(default_factory=list)
    cost_surface: Dict[str, Any] = field(default_factory=dict)
