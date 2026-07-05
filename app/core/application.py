"""FastAPI application factory."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.api.router import api_router
from app.core.logging import configure_logging
from app.core.settings import get_settings
from app.exceptions.handlers import register_exception_handlers
from app.middleware.request_logger import log_requests
from app.core.lifespan import lifespan

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    configure_logging()

    settings = get_settings()

    logger.info("Starting %s", settings.app_name)

    app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    )
    app.middleware("http")(log_requests)
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        logger.info("Root endpoint called")

        return {
            "application": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        }

    return app
