from typing import Optional, Dict, Any

# Local import inside constructor to avoid circular issues


class WorldModelerEngine:
    """
    BU-4 World Modeler (stable constructor version).

    Safe to instantiate with no arguments.
    Never raises during startup.
    """

    def __init__(self, store: Optional["WorldStore"] = None):
        # Delayed import prevents circular import at module load
        from app.engines.world_engine import WorldStore

        self.store = store or WorldStore()

    def snapshot(self) -> Dict[str, Any]:
        try:
            return {
                "ok": True,
                "store_path": str(self.store.db_path),
            }
        except Exception:
            return {
                "ok": False,
                "error": "snapshot_failed"
            }

    def analyze(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Phase-7 safe scaffold.
        Must never raise.
        """
        return {
            "drift_events": [],
            "gate_decisions": [],
            "trust_surfaces": [],
        }
