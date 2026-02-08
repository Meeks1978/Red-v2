from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter

from app.world_events import STORE as EVENT_STORE
from app.world_state import get_state
from app.world_entities import EntityRegistry

router = APIRouter(prefix="/v1/world", tags=["world-replay"])


@router.get("/replay")
def replay(limit: int = 200, since_id: Optional[int] = None, etype: Optional[str] = None) -> Dict[str, Any]:
    """
    Replay v1:
      - returns ordered world_events
      - returns current world_state snapshot + current entity registry snapshot
      (Later: true event-sourced projection per target_event_id)
    """
    events = EVENT_STORE.list(limit=limit, since_id=since_id, etype=etype)

    # Snapshot (current)
    ws = get_state()
    entities = EntityRegistry().list_entities()

    return {
        "ok": True,
        "events": events["events"],
        "snapshot": {
            "world_state": {
                "state": ws.state.value,
                "reason": ws.reason,
                "updated_at": ws.updated_at,
                "updated_by": ws.updated_by,
            },
            "entities": entities,
        },
    }
