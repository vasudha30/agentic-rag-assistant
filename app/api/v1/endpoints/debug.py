"""Debug endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/debug/error", tags=["Debug"])
async def debug_error() -> None:
    """Raise an exception for testing."""

    raise RuntimeError("This is a test exception")
