"""Root API endpoints."""

from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter()


@router.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Return application metadata."""

    settings = get_settings()

    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }