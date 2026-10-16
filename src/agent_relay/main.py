"""FastAPI entry point: uvicorn agent_relay.main:app."""
from typing import Literal
from fastapi import FastAPI, HTTPException
from groq import APIError, APITimeoutError, RateLimitError
from pydantic import BaseModel, ValidationError
from agent_relay.config import Settings, get_settings
from agent_relay.agent.graph import build_extraction_graph
from agent_relay.agent.model import GroqMeetingModel, ModelNotConfiguredError
from agent_relay.schemas.extraction import ExtractionInput
from agent_relay.schemas.meeting import MeetingRequest


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else get_settings()
    application = FastAPI(
        title=settings.app_name, version="0.1.0",
        description="Meeting coordination backend API.",
    )
    application.state.settings = settings
    application.state.extraction_graph = build_extraction_graph(GroqMeetingModel(settings))

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        """Application liveness; no external services are checked."""
        return HealthResponse()

    @application.post("/v1/meeting-requests/extract", response_model=MeetingRequest, tags=["meetings"])
    async def extract_meeting(body: ExtractionInput) -> MeetingRequest:
        """Extract details and clarification questions; does not create invitations."""
        try:
            result = await application.state.extraction_graph.ainvoke(body.model_dump())
        except ModelNotConfiguredError:
            raise HTTPException(503, "Groq API key is not configured.") from None
        except RateLimitError:
            raise HTTPException(429, "Model provider rate limit reached. Try again later.") from None
        except APITimeoutError:
            raise HTTPException(504, "Model provider timed out.") from None
        except APIError:
            raise HTTPException(502, "Model provider request failed.") from None
        except (ValidationError, ValueError):
            raise HTTPException(502, "Model returned an invalid meeting request.") from None
        return result["meeting_request"]

    return application


app = create_app()
