"""Extraction boundary tests using fake model responses; no API key required."""
import json
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import httpx
from groq import APITimeoutError, RateLimitError
from pydantic import ValidationError
from agent_relay.agent.graph import build_extraction_graph
from agent_relay.agent.model import GroqMeetingModel, output_schema
from agent_relay.config import Settings
from agent_relay.main import create_app
from agent_relay.schemas.meeting import MeetingRequest


class ExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, app, payload):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/v1/meeting-requests/extract", json=payload)

    def payload(self):
        return {"text": "Meet alex@example.com tomorrow", "current_date": "2026-10-13", "timezone": "America/Los_Angeles"}

    async def test_graph_preserves_context_and_returns_schema(self):
        model = SimpleNamespace(extract=AsyncMock(return_value=MeetingRequest(
            participants=["alex@example.com"], date="2026-10-14"
        )))
        app = create_app(Settings(_env_file=None, groq_api_key=None))
        app.state.extraction_graph = build_extraction_graph(model)
        response = await self.request(app, self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["date"], "2026-10-14")
        self.assertIsNone(response.json()["duration_minutes"])
        self.assertIsNone(response.json()["time_preference"])
        context = json.loads(model.extract.call_args.args[0][1]["content"])
        self.assertEqual(context["current_date"], "2026-10-13")
        self.assertEqual(context["timezone"], "America/Los_Angeles")

    async def test_questions_come_from_model_without_hardcoded_additions(self):
        questions = ["How long should the meeting last?", "What time would you prefer?"]
        meeting = MeetingRequest(clarification_questions=questions)
        graph = build_extraction_graph(SimpleNamespace(extract=AsyncMock(return_value=meeting)))
        result = await graph.ainvoke({"text": "Schedule a meeting", "current_date": date(2026, 10, 13), "timezone": "America/Los_Angeles"})
        self.assertEqual(result["meeting_request"].clarification_questions, questions)
        self.assertIsNone(result["meeting_request"].duration_minutes)
        self.assertIsNone(result["meeting_request"].time_preference)

    async def test_invalid_input_does_not_call_provider(self):
        app = create_app(Settings(_env_file=None, groq_api_key=None))
        graph = SimpleNamespace(ainvoke=AsyncMock())
        app.state.extraction_graph = graph
        for changes in ({"timezone": "Invalid/Zone"}, {"text": " "}, {"current_date": "not-a-date"}):
            response = await self.request(app, self.payload() | changes)
            self.assertEqual(response.status_code, 422)
        graph.ainvoke.assert_not_called()

    async def test_missing_key_and_health(self):
        app = create_app(Settings(_env_file=None, groq_api_key=None))
        response = await self.request(app, self.payload())
        self.assertEqual(response.status_code, 503)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            self.assertEqual((await client.get("/health")).json(), {"status": "ok"})

    async def test_provider_errors_are_sanitized(self):
        app = create_app(Settings(_env_file=None, groq_api_key=None))
        rate_error = RateLimitError("private-provider-details", response=httpx.Response(429, request=httpx.Request("POST", "https://example.com")), body=None)
        for error, status in [(rate_error, 429), (APITimeoutError(request=httpx.Request("POST", "https://example.com")), 504), (ValueError("private-output"), 502)]:
            app.state.extraction_graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=error))
            response = await self.request(app, self.payload())
            self.assertEqual(response.status_code, status)
            self.assertNotIn("private", response.text)

    def test_output_schema_is_derived_and_adapted_for_strict_mode(self):
        original = MeetingRequest.model_json_schema()
        schema = output_schema()
        self.assertEqual(set(schema["required"]), set(original["properties"]))
        self.assertFalse(schema["additionalProperties"])
        for name, field in original["properties"].items():
            self.assertEqual(schema["properties"][name]["description"], field["description"])
        self.assertIn({"type": "null"}, schema["properties"]["date"]["anyOf"])
        self.assertEqual(schema["properties"], original["properties"])
        self.assertEqual(schema["properties"]["duration_minutes"]["anyOf"][0]["exclusiveMinimum"], 0)
        self.assertIsNone(schema["properties"]["duration_minutes"]["default"])
        self.assertEqual(schema["properties"]["participants"]["items"]["minLength"], 1)
        self.assertEqual(schema["properties"]["time_preference"]["anyOf"][0]["minLength"], 1)
        self.assertEqual(schema["properties"]["date"]["anyOf"][0]["format"], "date")
        # A new model property must propagate without editing a second definition.
        original["properties"]["new_field"] = {"type": "string", "description": "New detail"}
        with patch.object(MeetingRequest, "model_json_schema", return_value=original):
            extended = output_schema()
        self.assertIn("new_field", extended["properties"])
        self.assertIn("new_field", extended["required"])

    async def test_groq_uses_strict_schema_and_validates_output(self):
        settings = Settings(_env_file=None, groq_api_key="fake-test-key")
        client = AsyncMock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"duration_minutes": -1})))])
        with patch("agent_relay.agent.model.AsyncGroq") as factory:
            factory.return_value.__aenter__ = AsyncMock(return_value=client)
            factory.return_value.__aexit__ = AsyncMock(return_value=False)
            with self.assertRaises(ValidationError):
                await GroqMeetingModel(settings).extract([])
        arguments = client.chat.completions.create.call_args.kwargs
        self.assertTrue(arguments["response_format"]["json_schema"]["strict"])
        self.assertEqual(arguments["model"], "openai/gpt-oss-120b")


if __name__ == "__main__":
    unittest.main()
