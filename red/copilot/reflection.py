from __future__ import annotations

from typing import Any, Dict, List

from .models import IntentRecord


def propose_memory_candidates(rec: IntentRecord) -> List[Dict[str, Any]]:
    cands: List[Dict[str, Any]] = []

    cands.append({
        "type": "working_note",
        "content": rec.goal,
        "confidence": 0.7,
        "source": "copilot.reflection",
        "trace_id": rec.trace_id,
    })

    for a in rec.assumptions:
        cands.append({
            "type": "assumption",
            "content": a.statement,
            "confidence": a.confidence,
            "source": "copilot.assumptions",
            "trace_id": rec.trace_id,
        })

    return cands


def attach_reflection(rec: IntentRecord) -> IntentRecord:
    rec.memory_candidates = propose_memory_candidates(rec)
    return rec
