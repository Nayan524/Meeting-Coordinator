# Meeting Coordinator

A meeting coordination agent backed by durable workflow execution.

## Problem statement

Meeting organizers spend time checking participants' availability, resolving scheduling conflicts, and exchanging messages to agree on a time. Build a meeting coordination agent that turns a natural-language request into a scheduled meeting: it clarifies missing details, checks authorized calendars, proposes times that meet the organizer's constraints, and sends invitations after approval. The backend must preserve progress across restarts and service failures, reconcile uncertain results, and prevent duplicate invitations when an interrupted scheduling attempt resumes.

## Planned workflow

1. Accept a natural-language meeting request.
2. Clarify missing participants, duration, time window, or scheduling constraints.
3. Check availability through authorized calendar integrations.
4. Calculate suitable slots and present options to the organizer.
5. Wait for the organizer's selection and approval.
6. Create the meeting invitation and record its outcome.
7. Recover interrupted workflows and reconcile uncertain outcomes before retrying actions.

The initial prototype will use simulated calendars. Availability calculations will use deterministic code; the agent will interpret requests, ask clarifying questions, and coordinate tool calls. Duplicate prevention will depend on the calendar integration's idempotency and reconciliation capabilities; unresolved outcomes must be reported explicitly.

## Planned stack

- Python and FastAPI for the backend API.
- LangGraph for agent workflow orchestration.
- Groq for hosted LLM access, with a configurable model.

## Current status

The FastAPI foundation is implemented, including environment configuration and a liveness endpoint. A single-node LangGraph workflow now uses Groq to extract validated meeting details and clarification questions. Calendar tools, conversation continuation, persistence, and recovery are not implemented yet.

## Local setup (PowerShell)

Run these commands from the repository root. Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn agent_relay.main:app --reload
```

The API runs at http://127.0.0.1:8000. Interactive API documentation is available at http://127.0.0.1:8000/docs.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

`GET /health` returns HTTP 200 with `{"status":"ok"}`. This confirms application liveness; it does not check calendar integrations, model providers, databases, or workers.

## Configuration

Settings are read from environment variables and an optional `.env` file in the working directory. Environment variables take precedence. Start the server from the repository root to load its `.env` file. Secrets must not be committed.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Meeting Coordinator` | Application title shown in API documentation. |
| `ENVIRONMENT` | `development` | One of `development`, `test`, or `production`; currently metadata only. |
| `GROQ_API_KEY` | Unset | Required for extraction; stored as a masked secret in settings. |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model supporting Groq strict structured outputs. |

The health endpoint works without Groq credentials. Extraction sends the supplied request and date/timezone context to Groq. Configure your own API key in `.env`; never commit it. Free-plan quotas depend on your Groq account. Model output is schema-validated, but semantic accuracy still requires evaluation. Dependencies have compatible version ranges; exact dependency locking will be added in a later step.

## Extract a meeting request

Set `GROQ_API_KEY` in your local `.env` file and restart the server. The default model is `openai/gpt-oss-120b`, listed on Groq's free plan and supporting strict JSON-schema output. You can change `GROQ_MODEL` to another compatible model.

`POST /v1/meeting-requests/extract` accepts:

```json
{
  "text": "Meet alex@example.com tomorrow for 45 minutes in the morning",
  "current_date": "2026-10-13",
  "timezone": "America/Los_Angeles"
}
```

Supply the user's current local date and a valid IANA timezone. The response follows `MeetingRequest`: participants, duration in minutes, resolved date, time preference, and clarification questions. Missing duration and time preference remain null and trigger LLM-generated clarification questions. No meeting duration or time preference is assumed. Missing or ambiguous dates remain null. Participant names are not fabricated into email addresses.

Try the endpoint in `/docs`. This step only extracts details: it does not access calendars, send invitations, or save conversations. Questions are returned to the caller; answering them in a continuing workflow will be implemented later.

Errors: 422 for invalid input, 503 for missing credentials, 429 for provider rate limits, 504 for provider timeout, and 502 for provider failures or invalid model output. Provider error bodies and credentials are not returned to clients.

## Verification

Run local tests without sending requests to Groq:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Model availability and quotas: https://console.groq.com/docs/rate-limits

Structured output support: https://console.groq.com/docs/structured-outputs
