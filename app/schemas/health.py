"""Health response schema."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health response."""

    status: str
