"""Input contract for text extraction."""
from datetime import date as CalendarDate
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from agent_relay.schemas.meeting import NonEmptyText


class ExtractionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: NonEmptyText = Field(max_length=8000)
    current_date: CalendarDate = Field(description="Current local date in the user's timezone.")
    timezone: NonEmptyText = Field(description="IANA timezone, e.g. America/Los_Angeles.")

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Provide a valid IANA timezone.") from exc
        return value
