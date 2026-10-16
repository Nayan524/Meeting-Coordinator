"""Read participant schedules from Google Calendar."""

import json
from datetime import datetime, time
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from langchain_core.tools import tool

from agent_relay.schemas.meeting import MeetingRequest
from agent_relay.config import get_settings


@tool
def check_availability(meeting_request: MeetingRequest) -> dict:
    """Return JSON-compatible availability data for each participant.

    Use the configured Google Calendar token and an 8 AM to 5 PM
    America/Los_Angeles window on the requested date. Daylight saving time is
    handled by ZoneInfo. This does not interpret preferences, create invitations,
    or persist results. Failures must not be treated as free time.
    """
    token = get_settings().google_calendar_access_token
    if token is None or not token.get_secret_value().strip():
        raise ValueError("GOOGLE_CALENDAR_ACCESS_TOKEN is not configured.")
    access_token = token.get_secret_value()
    if not meeting_request.participants:
        raise ValueError("At least one participant email is required.")
    if any("@" not in email or any(c.isspace() for c in email)
           for email in meeting_request.participants):
        raise ValueError("Participants must be email addresses, not names.")
    if meeting_request.date is None:
        raise ValueError("A meeting date is required to look up availability.")
    local_timezone = ZoneInfo("America/Los_Angeles")
    start_time = datetime.combine(meeting_request.date, time(8), tzinfo=local_timezone)
    end_time = datetime.combine(meeting_request.date, time(17), tzinfo=local_timezone)

    start, end = start_time.isoformat(), end_time.isoformat()
    results = []
    for email in meeting_request.participants:
        request = Request(
            "https://www.googleapis.com/calendar/v3/freeBusy",
            data=json.dumps({
                "items": [{"id": email}], "timeMin": start, "timeMax": end,
                "timeZone": "America/Los_Angeles",
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
            schedule = data["calendars"].get(email)
            if not isinstance(schedule, dict):
                raise ValueError("Missing participant calendar")
            if schedule.get("errors"):
                results.append({"email": email, "status": "error", "errors": schedule["errors"]})
            elif isinstance(schedule.get("busy"), list):
                results.append({"email": email, "status": "success", "busy": schedule["busy"]})
            else:
                raise ValueError("Missing busy intervals")
        except HTTPError as exc:
            results.append({"email": email, "status": "error", "error": {
                "code": str(exc.code), "message": "Google Calendar request failed.",
            }})
        except (URLError, TimeoutError):
            results.append({"email": email, "status": "error", "error": {
                "code": "connection_error", "message": "Google Calendar could not be reached.",
            }})
        except (ValueError, TypeError, KeyError, AttributeError):
            results.append({"email": email, "status": "error", "error": {
                "code": "invalid_response", "message": "Invalid schedule response.",
            }})
    return {"start_time": start, "end_time": end,
            "timezone": "America/Los_Angeles", "participants": results}
