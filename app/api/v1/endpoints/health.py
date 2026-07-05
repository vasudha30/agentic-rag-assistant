"""Health check endpoints."""

from fastapi import APIRouter, Depends

from app.dependencies.services import get_health_service
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
async def health(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Health endpoint."""

    return service.get_health()
