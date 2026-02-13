from __future__ import annotations
from typing import Any, Dict

from app.contracts.execution import ExecutionPlan, ExecutionResult
import os
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from pathlib import Path

class ExecutorEngine:
    def __init__(self) -> None:
        # BU-5: deterministic gating + idempotency + receipts
        self.enabled = _env_bool('EXECUTOR_ENABLED', False)
        self.receipts = ReceiptStore()
        self.last_error = None

    """
    Scaffold. Real execution stays in your existing /v1/execute path.
    This engine remains OFF by default until you wire it.
    """
    enabled: bool = False

    def execute(self, plan: ExecutionPlan, ctx: Dict[str, Any]) -> ExecutionResult:
        return ExecutionResult(ok=False, error="ExecutorEngine scaffold: not wired.")

# --- Compatibility alias (scaffold wiring expects this name) ---
GuardedExecutor = ExecutorEngine


# --- BU-5: deterministic gating + idempotency + receipts ---
def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")

def _now_ms() -> int:
    return int(time.time() * 1000)

@dataclass
class ExecReceipt:
    ok: bool
    blocked: Optional[str]
    reason: str
    trace_id: Optional[str]
    idempotency_key: Optional[str]
    ts_ms: int
    output: Dict[str, Any]

class ReceiptStore:
    """
    JSON file-backed receipt store.
    Designed to never raise on read/write (Phase-7 discipline).
    """
    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(path or os.getenv("EXEC_RECEIPTS_PATH", "/red/data/exec_receipts.json"))
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                self.path.write_text("{}", encoding="utf-8")
        except Exception:
            # Never raise in constructor
            pass

    def _read(self) -> Dict[str, Any]:
        try:
            txt = self.path.read_text(encoding="utf-8")
            return json.loads(txt) if txt.strip() else {}
        except Exception:
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        try:
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        db = self._read()
        v = db.get(key)
        return v if isinstance(v, dict) else None

    def put(self, key: str, receipt: Dict[str, Any]) -> None:
        db = self._read()
        db[key] = receipt
        self._write(db)

