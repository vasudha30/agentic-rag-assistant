"""Root API endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """Return application information."""

    return {
        "application": "Agentic RAG Assistant",
        "version": "0.1.0",
        "environment": "development",
    }