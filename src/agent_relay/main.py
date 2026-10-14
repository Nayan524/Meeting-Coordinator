"""FastAPI entry point: uvicorn agent_relay.main:app."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from agent_relay.config import Settings, get_settings


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application with validated settings."""
    settings = settings if settings is not None else get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Meeting coordination backend API.",
    )
    application.state.settings = settings

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        """Report application liveness; no external services are checked."""
        return HealthResponse()

    return application


app = create_app()
