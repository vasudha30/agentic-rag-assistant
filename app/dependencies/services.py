"""Service dependencies."""

from __future__ import annotations

from app.services.health_service import HealthService


def get_health_service() -> HealthService:
    """Return the health service."""

    return HealthService()
