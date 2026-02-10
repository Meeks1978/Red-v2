from __future__ import annotations

from red.app.engines.advisory_engine import AdvisoryEngine
from red.app.services.intent_outcome import IntentOutcomeTracker, SuccessCriteriaEvaluator, PostIntentReflection
from red.app.trust.surface import TrustSurfaceBuilder


class ServiceContainer:
    """
    Simple DI container. Replace with your existing wiring if you have one.
    """
    def __init__(self) -> None:
        self.intent_outcome_tracker = IntentOutcomeTracker()
        self.success_evaluator = SuccessCriteriaEvaluator()
        self.post_reflector = PostIntentReflection()
        self.trust_surface = TrustSurfaceBuilder()

        self.advisory_engine = AdvisoryEngine(
            tracker=self.intent_outcome_tracker,
            evaluator=self.success_evaluator,
            reflector=self.post_reflector,
            trust_builder=self.trust_surface,
        )

from red.app.engines.world_engine import WorldEngine

# extend container
ServiceContainer.world_engine = WorldEngine()

from red.app.governance.assumption_verifier import AssumptionVerifier
from red.app.governance.uncertainty_gate import UncertaintyGate

ServiceContainer.assumption_verifier = AssumptionVerifier()
ServiceContainer.uncertainty_gate = UncertaintyGate()

from red.app.engines.executor_engine import GuardedExecutor

ServiceContainer.executor = GuardedExecutor()
