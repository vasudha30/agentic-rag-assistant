"""Main API router."""

from fastapi import APIRouter

from app.api.v1.endpoints.debug import router as debug_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.root import router as root_router

api_router = APIRouter()

api_router.include_router(root_router)
api_router.include_router(health_router)
api_router.include_router(debug_router)
