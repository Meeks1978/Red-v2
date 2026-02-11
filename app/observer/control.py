from __future__ import annotations

from app.services.container import ServiceContainer


def start_shadow_observer() -> None:
    ServiceContainer.shadow_observer.enabled = True
    ServiceContainer.shadow_scheduler.config.enabled = True
    ServiceContainer.shadow_scheduler.start()


def stop_shadow_observer() -> None:
    ServiceContainer.shadow_scheduler.stop()
    ServiceContainer.shadow_scheduler.config.enabled = False
    ServiceContainer.shadow_observer.enabled = False
