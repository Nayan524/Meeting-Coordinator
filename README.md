# Agent Relay

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

The repository contains an initial folder scaffold. The backend, agent, calendar tools, and recovery behavior are not implemented yet.
