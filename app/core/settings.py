"""Application settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    app_name: str = "Agentic RAG Assistant"
    app_version: str = "0.1.0"
    app_description: str = "Production-grade Agentic RAG Assistant"

    environment: str = "development"
    debug: bool = True

    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings."""
    return Settings()
