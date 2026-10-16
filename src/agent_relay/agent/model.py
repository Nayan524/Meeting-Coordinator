"""Groq model access with strict JSON output and local schema validation."""
from groq import AsyncGroq
from agent_relay.config import Settings
from agent_relay.schemas.meeting import MeetingRequest


class ModelNotConfiguredError(RuntimeError):
    """Raised when extraction is requested without a Groq API key."""


def output_schema() -> dict:
    """Derive the output contract, changing only strict-mode object requirements.

    Preserve Pydantic constraints and metadata. Groq documents requiring all
    properties and additionalProperties=false; keyword-level support for length,
    numeric, and date constraints still needs a live integration check.
    Defaults describe intent but do not substitute for generated required fields.
    """
    schema = MeetingRequest.model_json_schema()

    def adapt(node: dict) -> None:
        if node.get("type") == "object":
            node["required"] = list(node.get("properties", {}))
            node["additionalProperties"] = False
        # Visit schema nodes, not arbitrary metadata or property names.
        for keyword in ("properties", "$defs"):
            for child in node.get(keyword, {}).values():
                adapt(child)
        items = node.get("items")
        if isinstance(items, dict):
            adapt(items)
        for keyword in ("anyOf", "allOf", "oneOf", "prefixItems"):
            for child in node.get(keyword, []):
                adapt(child)

    adapt(schema)
    return schema


class GroqMeetingModel:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract(self, messages: list[dict[str, str]]) -> MeetingRequest:
        key = self.settings.groq_api_key
        if key is None or not key.get_secret_value().strip():
            raise ModelNotConfiguredError("GROQ_API_KEY is not configured.")
        async with AsyncGroq(
            api_key=key.get_secret_value(), timeout=30.0, max_retries=1
        ) as client:
            completion = await client.chat.completions.create(
                model=self.settings.groq_model,
                messages=messages,
                temperature=0,
                max_completion_tokens=2048,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "meeting_request", "strict": True,
                        "schema": output_schema(),
                    },
                },
            )
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("Model returned no structured content.")
        return MeetingRequest.model_validate_json(content)
