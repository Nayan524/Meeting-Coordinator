"""Structured output for natural-language meeting request extraction."""

from datetime import date as CalendarDate
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1)
]


class MeetingRequest(BaseModel):
    """Extracted meeting details; incomplete requests can await clarification.

    Participant names are preserved as supplied, not resolved calendar identities.
    Date resolution requires current date and user timezone in the extraction step.
    This schema validates data shape, not calendar access or scheduling readiness.
    """

    model_config = ConfigDict(extra="forbid")

    participants: list[NonEmptyText] = Field(
        default_factory=list,
        description="Participant names or emails supplied by the user. Empty if missing.",
    )
    duration_minutes: Annotated[int, Field(strict=True, gt=0)] | None = Field(
        default=None,
        description="Requested meeting duration in minutes. Null when missing; ask for clarification.",
    )
    date: CalendarDate | None = Field(
        default=None,
        description=(
            "Meeting date in YYYY-MM-DD format, resolved using current date and user "
            "timezone. Null when missing or ambiguous; never invent a date."
        ),
    )
    time_preference: NonEmptyText | None = Field(
        default=None,
        description="User's stated time preference. Null when missing; ask for clarification.",
    )
    clarification_questions: list[NonEmptyText] = Field(
        default_factory=list,
        description=(
            "Relevant questions for missing or ambiguous details, including unresolved "
            "participant identities. Empty when no clarification is needed."
        ),
    )
