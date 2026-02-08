from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db import connect, tx, DEFAULT_DB_PATH


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ReceiptStore:
    """
    Simple SQLite-backed receipt store.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("RED_DB_PATH", DEFAULT_DB_PATH)
        self._conn = connect(self.db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            token_id TEXT,
            proposal_id TEXT,
            runner_id TEXT,
            action TEXT,
            macro_json TEXT NOT NULL,
            result_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_receipts_created_at ON receipts(created_at);
        CREATE INDEX IF NOT EXISTS idx_receipts_token_id ON receipts(token_id);
        """
        self._conn.executescript(ddl)
        if self._conn.in_transaction:
            self._conn.commit()

    def write(
        self,
        *,
        token_id: Optional[str],
        proposal_id: Optional[str],
        runner_id: Optional[str],
        action: Optional[str],
        macro: Dict[str, Any],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        created_at = _now_iso()
        with tx(self._conn) as c:
            cur = c.execute(
                "INSERT INTO receipts "
                "(created_at, token_id, proposal_id, runner_id, action, macro_json, result_json) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    created_at,
                    token_id,
                    proposal_id,
                    runner_id,
                    action,
                    json.dumps(macro),
                    json.dumps(result),
                ),
            )
            receipt_id = cur.lastrowid

        return {
            "receipt_id": receipt_id,
            "created_at": created_at,
            "token_id": token_id,
            "proposal_id": proposal_id,
            "runner_id": runner_id,
            "action": action,
            "macro": macro,
            "result": result,
        }


# ---- Compatibility function expected by execute_api.py ----

_store = ReceiptStore()


def record_receipt(*, approval_token: Any, macro: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compatibility shim. execute_api.py expects record_receipt().
    approval_token is an ApprovalToken model instance; we extract key fields.
    """
    token_id = getattr(approval_token, "token_id", None)
    proposal_id = getattr(approval_token, "proposal_id", None)

    runner_id = None
    action = None
    scopes = getattr(approval_token, "scopes", None) or []
    if scopes:
        runner_id = getattr(scopes[0], "runner_id", None)
        action = getattr(scopes[0], "action", None)

    return _store.write(
        token_id=token_id,
        proposal_id=proposal_id,
        runner_id=runner_id,
        action=action,
        macro=macro,
        result=result,
    )
