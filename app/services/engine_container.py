from __future__ import annotations
from typing import Any, Dict

from app.services.container import ServiceContainer  # your existing container

from app.engines.orchestrator_engine import OrchestratorEngine
from app.engines.advisory_engine import AdvisoryEngine
from app.engines.planning_engine import PlanningEngine
from app.engines.observer_engine import ObserverEngine
from app.engines.executor_engine import ExecutorEngine
from app.engines.tool_router_engine import ToolRouterEngine
from app.engines.verification_engine import VerificationEngine
from app.engines.memory_curator_engine import MemoryCuratorEngine
from app.engines.world_modeler_engine import WorldModelerEngine
from app.engines.upgrade_advisor_engine import UpgradeAdvisorEngine

class EngineContainer:
    """
    Wires the 9 engines without altering existing execution stack.
    """
    def __init__(self) -> None:
        self.core: Any = ServiceContainer
        self.advisory = AdvisoryEngine()
        self.planning = PlanningEngine()
        self.observer = ObserverEngine()
        self.executor = ExecutorEngine()
        self.tool_router = ToolRouterEngine()
        self.verifier = VerificationEngine()
        self.memory = MemoryCuratorEngine(ServiceContainer)
        self.world = WorldModelerEngine()
        self.upgrades = UpgradeAdvisorEngine()
        self.orchestrator = OrchestratorEngine(self, ServiceContainer)

ENGINES = EngineContainer()

# --- Orchestrator glue (Reasoning Core coordinator) ---
from app.engines.orchestrator_engine import OrchestratorEngine
