from __future__ import annotations
import time, uuid
from typing import Any, Dict

from app.contracts.intent import IntentEnvelope
from app.contracts.advisory import AdvisoryResponse, ReasonSurface

def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"

class AdvisoryEngine:
    def advise(self, intent: IntentEnvelope, ctx: Dict[str, Any]) -> AdvisoryResponse:
        rs = ReasonSurface(
            reason="Scaffold advisory: no model attached yet.",
            confidence=0.5,
            what_would_change_my_mind=["Attach a reasoning model + implement planning/verification."]
        )
        return AdvisoryResponse(
            recommendation=f"Received intent: {intent.text}",
            reason_surface=rs,
            debug={"intent_id": intent.intent_id, "ctx_keys": sorted(list(ctx.keys()))}
        )
