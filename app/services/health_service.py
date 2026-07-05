"""Health service."""

from __future__ import annotations

from app.schemas.health import HealthResponse


class HealthService:
    """Service responsible for health checks."""

    def get_health(self) -> HealthResponse:
        """Return application health."""

        return HealthResponse(
            status="healthy",
        )
