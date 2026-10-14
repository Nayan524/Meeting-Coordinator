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

The FastAPI foundation is implemented, including environment configuration and a liveness endpoint. The LangGraph agent, Groq integration, calendar tools, persistence, and recovery behavior are not implemented yet.

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
| `GROQ_API_KEY` | Unset | Reserved for the upcoming agent integration; stored as a masked secret in settings. |
| `GROQ_MODEL` | Unset | Reserved for the upcoming configurable Groq model. |

Groq settings are optional for this backend foundation. No model calls are made yet. Dependencies have compatible version ranges; exact dependency locking will be added in a later step.
