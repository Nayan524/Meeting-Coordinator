"""A single-node LangGraph workflow for meeting request extraction."""
from typing import Protocol
from langgraph.graph import START, END, StateGraph
from agent_relay.agent.prompts import extraction_messages
from agent_relay.agent.state import ExtractionState
from agent_relay.schemas.meeting import MeetingRequest


class MeetingModel(Protocol):
    async def extract(self, messages: list[dict[str, str]]) -> MeetingRequest: ...


def build_extraction_graph(model: MeetingModel):
    async def extract_request(state: ExtractionState) -> dict:
        meeting = await model.extract(extraction_messages(
            state["text"], state["current_date"], state["timezone"]
        ))
        return {"meeting_request": meeting}

    graph = StateGraph(ExtractionState)
    graph.add_node("extract_request", extract_request)
    graph.add_edge(START, "extract_request")
    graph.add_edge("extract_request", END)
    return graph.compile()
