"""Application entry point for the Agentic RAG Assistant."""

from fastapi import FastAPI

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