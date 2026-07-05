"""Application lifespan management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""

    logger.info("Application startup")

    # Future:
    # - Initialize database
    # - Initialize ChromaDB
    # - Initialize Redis
    # - Load embedding model

    yield

    logger.info("Application shutdown")

    # Future:
    # - Close database
    # - Close Redis
    # - Cleanup resources