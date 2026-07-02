"""FastAPI application factory."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Agentic RAG Assistant",
        description="Production-grade Agentic RAG Assistant",
        version="0.1.0",
    )

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "message": "Welcome to Agentic RAG Assistant"
        }

    return app