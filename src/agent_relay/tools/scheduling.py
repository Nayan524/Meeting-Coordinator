"""Calculate common free intervals without using an LLM or calendar API."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from langchain_core.tools import tool

from agent_relay.schemas.meeting import MeetingRequest


@tool
def find_meeting_slots(meeting_request: MeetingRequest, availability: dict) -> dict:
    """Return all common free intervals long enough for the requested duration.

    Pass the result of check_availability as availability. Morning means 8 AM
    to noon; afternoon means noon to 5 PM in America/Los_Angeles. Other time
    preferences require clarification and are not interpreted here. Returned
    intervals are free ranges, not fixed-duration invitations. Missing or failed
    participant lookups prevent calculation. Busy intervals use [start, end).
    """
    if not meeting_request.participants:
        raise ValueError("Participants are required.")
    if meeting_request.date is None or meeting_request.duration_minutes is None:
        raise ValueError("Meeting date and duration are required.")
    preference = (meeting_request.time_preference or "").strip().casefold()
    windows = {"morning": (time(8), time(12)), "afternoon": (time(12), time(17))}
    if preference not in windows:
        raise ValueError("Provide morning or afternoon; other preferences need clarification.")
    zone = ZoneInfo("America/Los_Angeles")
    start_hour, end_hour = windows[preference]
    window_start = datetime.combine(meeting_request.date, start_hour, tzinfo=zone)
    window_end = datetime.combine(meeting_request.date, end_hour, tzinfo=zone)
    duration = timedelta(minutes=meeting_request.duration_minutes)

    def parse_time(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is None:
            raise ValueError("Availability timestamps must include timezone offsets.")
        return parsed.astimezone(zone)

    if (parse_time(availability["start_time"]) > window_start
            or parse_time(availability["end_time"]) < window_end):
        raise ValueError("Availability data must cover the entire preference window.")
    records = availability["participants"]
    busy = []
    for email in dict.fromkeys(meeting_request.participants):
        matches = [row for row in records if row["email"].casefold() == email.casefold()]
        if len(matches) != 1 or matches[0].get("status") != "success":
            raise ValueError(f"Complete successful availability is required for {email}.")
        intervals = matches[0].get("busy")
        if not isinstance(intervals, list):
            raise ValueError(f"Busy intervals are missing for {email}.")
        for interval in intervals:
            start, end = parse_time(interval["start"]), parse_time(interval["end"])
            if end <= start:
                raise ValueError("Busy interval end must be after start.")
            start, end = max(start, window_start), min(end, window_end)
            if start < end:
                busy.append((start, end))

    # Sorting plus a single sweep merges busy time and emits its complement.
    busy.sort()
    cursor = window_start
    slots = []
    for start, end in busy:
        if start - cursor >= duration:
            slots.append({"start": cursor.isoformat(), "end": start.isoformat()})
        cursor = max(cursor, end)
    if window_end - cursor >= duration:
        slots.append({"start": cursor.isoformat(), "end": window_end.isoformat()})
    return {
        "timezone": zone.key,
        "duration_minutes": meeting_request.duration_minutes,
        "available_slots": slots,
    }
