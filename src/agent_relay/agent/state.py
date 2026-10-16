"""Shared state for the initial extraction workflow."""
from datetime import date
from typing import TypedDict, NotRequired
from agent_relay.schemas.meeting import MeetingRequest


class ExtractionState(TypedDict):
    text: str
    current_date: date
    timezone: str
    meeting_request: NotRequired[MeetingRequest]
