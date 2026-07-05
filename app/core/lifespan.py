"""Application lifespan management."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown."""

    logger.info("Application startup")

    # Future:
    # - Initialize PostgreSQL
    # - Initialize Redis
    # - Initialize ChromaDB
    # - Initialize OpenAI
    # - Initialize Gemini

    yield

    logger.info("Application shutdown")

    # Future:
    # - Close database connections
    # - Close Redis
    # - Cleanup resources
