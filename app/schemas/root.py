"""Root response schema."""

from pydantic import BaseModel


class RootResponse(BaseModel):
    """Root response."""

    application: str
    version: str
    environment: str
