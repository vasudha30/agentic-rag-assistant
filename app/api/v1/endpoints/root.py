"""Root API endpoints."""

from fastapi import APIRouter

from app.core.settings import get_settings
from app.schemas.root import RootResponse

router = APIRouter()


@router.get("/", response_model=RootResponse, tags=["Root"])
async def root() -> RootResponse:
    """Return application metadata."""

    settings = get_settings()

    return RootResponse(
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
