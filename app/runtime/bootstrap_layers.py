# red/app/runtime/bootstrap_layers.py
from __future__ import annotations
from datetime import datetime, timezone

from app.runtime.layer_status import layer_status_store

def bootstrap_layer_defaults() -> None:
    ts = datetime.now(timezone.utc).isoformat()

    # Set conservative defaults. Update these as you wire real checks.
    for lid in range(1, 40):
        layer_status_store.set(lid, "not_started", last_check=ts)

    # If you already KNOW something is wired/tested today, set it here (or remove these).
    # Example:
    # layer_status_store.set(6, "wired", last_check=ts, detail={"note":"control plane reachable"})
