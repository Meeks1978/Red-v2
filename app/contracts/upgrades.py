from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass(frozen=True)
class UpgradeProposal:
    proposal_id: str
    summary: str
    rationale: str
    risk: str = "low"
    diff: str = ""
    rollback_plan: str = ""
    evidence: List[Dict[str, Any]] = field(default_factory=list)
