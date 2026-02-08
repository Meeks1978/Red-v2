from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException
import sqlite3

from app.db import connect, DEFAULT_DB_PATH
from app.world_events import STORE as EVENT_STORE

router = APIRouter(tags=["receipts-explain"])

DB_PATH = os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)


def _get_receipt(receipt_id: int) -> Dict[str, Any]:
    conn = connect(DB_PATH)
    row = conn.execute(
        "SELECT receipt_id, created_at, token_id, proposal_id, runner_id, action, macro_json, result_json "
        "FROM receipts WHERE receipt_id = ?",
        (receipt_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="receipt not found")

    return {
        "receipt_id": row["receipt_id"],
        "created_at": row["created_at"],
        "token_id": row["token_id"],
        "proposal_id": row["proposal_id"],
        "runner_id": row["runner_id"],
        "action": row["action"],
        "macro": json.loads(row["macro_json"]),
        "result": json.loads(row["result_json"]),
    }


@router.get("/v1/receipts/{receipt_id}/explain")
def explain_receipt(receipt_id: int, events_limit: int = 200) -> Dict[str, Any]:
    """
    Explain v1:
      - loads receipt record
      - returns recent world_events (client can filter by token_id/proposal_id/trace_id manually)
    """
    receipt = _get_receipt(receipt_id)

    # Pull recent events (simple, fast). You can filter in UI by token_id/proposal_id.
    recent = EVENT_STORE.list(limit=events_limit)["events"]

    return {
        "ok": True,
        "receipt": receipt,
        "events_hint": {
            "filter_by": {
                "token_id": receipt.get("token_id"),
                "proposal_id": receipt.get("proposal_id"),
                "runner_id": receipt.get("runner_id"),
            }
        },
        "recent_events": recent,
    }
