"""Tests for conversation analysis service behavior."""

import asyncio

from app.services import conversation_analysis_service as service


def test_format_conversation_compacts_and_omits_middle_messages():
    transcript = []
    for i in range(30):
        transcript.append({"role": "user", "content": f"Question {i} " + ("x " * 200)})
        transcript.append({"role": "assistant", "content": f"Reply {i} " + ("y " * 200)})

    formatted = service._format_conversation(transcript, "Client")

    assert "omitted for brevity" in formatted
    assert len(formatted) <= service.MAX_ANALYSIS_CONVERSATION_CHARS
    for line in formatted.splitlines():
        assert len(line) <= 320


def test_parse_analysis_json_extracts_wrapped_object():
    wrapped = "Analysis result:\n```json\n{\"overall_score\": 4.2}\n```"
    parsed = service._parse_analysis_json(wrapped)
    assert parsed["overall_score"] == 4.2


def test_analyze_conversation_uses_system_user_messages_and_token_limit(monkeypatch):
    captured = {}

    class DummyResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": '{"overall_score": 4.0}'}}]}

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return DummyResponse()

    monkeypatch.setenv("FIREWORKS_API_KEY", "test-key")
    monkeypatch.setattr(service.httpx, "AsyncClient", DummyAsyncClient)

    result = asyncio.run(
        service.analyze_conversation(
            transcript=[
                {"role": "user", "content": "Can we talk about smoking?"},
                {"role": "assistant", "content": "I know I should quit but it's hard."},
            ],
            persona_name="Marcus",
        )
    )

    payload = captured["payload"]
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == service.ANALYSIS_SYSTEM_PROMPT
    assert payload["messages"][1]["role"] == "user"
    assert "Transcript:" in payload["messages"][1]["content"]
    assert "max_tokens" not in payload
    assert result["overall_score"] == 4.0
