"""Tests for ScriptService (ROADMAP Task 1.4 — Sprint 1.4B).

No real network calls: `script_service._call_gemini` is monkeypatched with a
fake async function that returns canned (FakeResponse, latency_ms) pairs, and
`asyncio.sleep` is monkeypatched to a no-op so retry tests run instantly.
"""

import json

import pytest

from app.core.exceptions import ScriptGenerationError
from app.services import script_service

SAMPLE_CONFIG = {
    "topic": "Remote work culture",
    "cefr_level": "B1",
    "genre": "interview",
    "accent": "american",
    "duration_minutes": 8,
    "num_speakers": 2,
    "language_features": {
        "collocation": True,
        "idiom": True,
        "slang": False,
        "local_expressions": False,
        "phrasal_verbs": True,
        "business_register": False,
    },
    "speakers": [
        {"id": "11111111-1111-1111-1111-111111111111", "name": "Alex", "gender": "male", "accent": "american"},
        {"id": "22222222-2222-2222-2222-222222222222", "name": "Sam", "gender": "female", "accent": "american"},
    ],
}

VALID_LINES = [
    {
        "id": "line_001",
        "speaker_id": "11111111-1111-1111-1111-111111111111",
        "text": "Welcome to the show!",
        "language_notes": {"collocations": ["Welcome to"], "idioms": [], "grammar_point": "Present Simple"},
    },
    {
        "id": "line_002",
        "speaker_id": "22222222-2222-2222-2222-222222222222",
        "text": "Thanks for having me.",
        "language_notes": {"collocations": [], "idioms": [], "grammar_point": "Present Simple"},
    },
]


class FakeResponse:
    """Stand-in for httpx.Response — carries only what script_service reads."""

    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or json.dumps(json_data or {})

    def json(self) -> dict:
        return self._json_data


def gemini_ok_response(lines: list[dict], tokens_used: int = 500) -> FakeResponse:
    """A fake HTTP 200 Gemini response wrapping `lines` as the JSON-array text payload."""
    body = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(lines)}]}, "finishReason": "STOP"}],
        "usageMetadata": {"totalTokenCount": tokens_used},
    }
    return FakeResponse(200, body)


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    """Retry tests must not actually wait — patch asyncio.sleep to a no-op."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(script_service.asyncio, "sleep", fake_sleep)
    return sleeps


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(script_service.settings, "GEMINI_API_KEY", "test-key-not-real")


def queue_responses(monkeypatch, responses: list[FakeResponse]):
    """Monkeypatch _call_gemini to return `responses` in order, one per call."""
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str, schema: dict | None = None):
        index = calls["n"]
        calls["n"] += 1
        return responses[index], 12.3

    monkeypatch.setattr(script_service, "_call_gemini", fake_call_gemini)
    return calls


async def test_generate_script_success_on_http_200(monkeypatch):
    calls = queue_responses(monkeypatch, [gemini_ok_response(VALID_LINES)])

    lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG)

    assert calls["n"] == 1
    assert len(lines) == 2
    assert lines[0].speaker_id == "11111111-1111-1111-1111-111111111111"
    assert lines[0].text == "Welcome to the show!"
    assert lines[1].speaker_id == "22222222-2222-2222-2222-222222222222"


async def test_generate_script_retries_on_429_then_succeeds(monkeypatch, no_real_sleep):
    calls = queue_responses(
        monkeypatch,
        [FakeResponse(429, text="rate limited"), gemini_ok_response(VALID_LINES)],
    )

    lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG)

    assert calls["n"] == 2
    assert len(lines) == 2
    assert no_real_sleep == [1.0]  # GEMINI_RETRY_BASE_DELAY, exactly one backoff step


async def test_generate_script_backoff_sequence_is_1s_2s_4s(monkeypatch, no_real_sleep):
    queue_responses(
        monkeypatch,
        [
            FakeResponse(429, text="rate limited"),
            FakeResponse(429, text="rate limited"),
            FakeResponse(429, text="rate limited"),
            gemini_ok_response(VALID_LINES),
        ],
    )

    await script_service.generate_script("proj-1", SAMPLE_CONFIG)

    assert no_real_sleep == [1.0, 2.0, 4.0]


async def test_generate_script_exhausts_retries_raises(monkeypatch, no_real_sleep):
    calls = queue_responses(monkeypatch, [FakeResponse(429, text="rate limited")] * 4)

    with pytest.raises(ScriptGenerationError, match="HTTP 429 after 4 attempt"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)

    assert calls["n"] == 4
    assert no_real_sleep == [1.0, 2.0, 4.0]


async def test_generate_script_non_429_error_does_not_retry(monkeypatch, no_real_sleep):
    calls = queue_responses(monkeypatch, [FakeResponse(500, text="internal error")])

    with pytest.raises(ScriptGenerationError, match="HTTP 500"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)

    assert calls["n"] == 1
    assert no_real_sleep == []


async def test_generate_script_invalid_json_raises(monkeypatch):
    body = {"candidates": [{"content": {"parts": [{"text": "not valid json"}]}}]}
    queue_responses(monkeypatch, [FakeResponse(200, body)])

    with pytest.raises(ScriptGenerationError, match="valid JSON"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)


async def test_generate_script_schema_validation_failure_raises(monkeypatch):
    bad_lines = [{"id": "line_001", "speaker_id": "11111111-1111-1111-1111-111111111111"}]  # missing "text"
    queue_responses(monkeypatch, [gemini_ok_response(bad_lines)])

    with pytest.raises(ScriptGenerationError, match="schema validation"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)


async def test_generate_script_rejects_name_as_speaker_id(monkeypatch):
    """Regression test for Sprint 1.4A fix #1: speaker_id must be a UUID, not a name."""
    lines_with_name_id = [{**VALID_LINES[0], "speaker_id": "Alex"}]
    queue_responses(monkeypatch, [gemini_ok_response(lines_with_name_id)])

    with pytest.raises(ScriptGenerationError, match="schema validation"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)


async def test_generate_script_rejects_unknown_speaker_uuid(monkeypatch):
    hallucinated = [{**VALID_LINES[0], "speaker_id": "99999999-9999-9999-9999-999999999999"}]
    queue_responses(monkeypatch, [gemini_ok_response(hallucinated)])

    with pytest.raises(ScriptGenerationError, match="not in project"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)


async def test_generate_script_empty_script_raises(monkeypatch):
    queue_responses(monkeypatch, [gemini_ok_response([])])

    with pytest.raises(ScriptGenerationError, match="empty script"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)


async def test_generate_script_missing_api_key_raises_without_calling_gemini(monkeypatch):
    monkeypatch.setattr(script_service.settings, "GEMINI_API_KEY", "")
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str, schema: dict | None = None):
        calls["n"] += 1
        raise AssertionError("Gemini should never be called without an API key")

    monkeypatch.setattr(script_service, "_call_gemini", fake_call_gemini)

    with pytest.raises(ScriptGenerationError, match="not configured"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG)

    assert calls["n"] == 0


async def test_call_gemini_includes_response_json_schema(monkeypatch):
    """_call_gemini includes responseJsonSchema (and not responseSchema) in generationConfig (BUG-011)."""
    captured = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, params=None, json=None):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse(200, json_data={"candidates": [{"content": {"parts": [{"text": "[]"}]}}]})

    monkeypatch.setattr(script_service.httpx, "AsyncClient", FakeAsyncClient)

    schema = {"type": "array"}
    await script_service._call_gemini("test prompt", schema=schema)

    assert "generationConfig" in captured["json"]
    assert captured["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert captured["json"]["generationConfig"]["responseJsonSchema"] == schema
    assert "responseSchema" not in captured["json"]["generationConfig"]


async def test_generate_script_wire_payload_includes_response_json_schema(monkeypatch):
    """generate_script transmits responseJsonSchema in generationConfig over the wire."""
    captured = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, params=None, json=None):
            captured["json"] = json
            return FakeResponse(200, json_data={"candidates": [{"content": {"parts": [{"text": json_module.dumps(VALID_LINES)}]}}]})

    import json as json_module
    monkeypatch.setattr(script_service.httpx, "AsyncClient", FakeAsyncClient)

    lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG)
    assert len(lines) == 2
    assert "generationConfig" in captured["json"]
    gen_config = captured["json"]["generationConfig"]
    assert "responseJsonSchema" in gen_config
    assert "responseSchema" not in gen_config
    assert gen_config["responseJsonSchema"]["type"] == "array"


async def test_regenerate_line_wire_payload_includes_response_json_schema(monkeypatch):
    """regenerate_line transmits responseJsonSchema in generationConfig over the wire."""
    captured = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, params=None, json=None):
            captured["json"] = json
            return FakeResponse(200, json_data={"candidates": [{"content": {"parts": [{"text": json_module.dumps(VALID_LINES[0])}]}}]})

    import json as json_module
    monkeypatch.setattr(script_service.httpx, "AsyncClient", FakeAsyncClient)

    line = await script_service.regenerate_line(
        "proj-1", SAMPLE_CONFIG, "line_001", "old text", "11111111-1111-1111-1111-111111111111"
    )
    assert line.id == "line_001"
    gen_config = captured["json"]["generationConfig"]
    assert "responseJsonSchema" in gen_config
    assert "responseSchema" not in gen_config
    assert gen_config["responseJsonSchema"]["type"] == "object"


async def test_generate_with_retry_never_downgrades_to_schema_less(monkeypatch):
    """If Gemini returns a fatal error or network fails, _generate_with_retry must not retry schema-less."""
    calls = []

    async def fake_call_gemini(prompt: str, schema: dict | None = None):
        calls.append(schema)
        raise script_service.httpx.RequestError("Network error")

    monkeypatch.setattr(script_service, "_call_gemini", fake_call_gemini)

    schema = {"type": "array"}
    with pytest.raises(ScriptGenerationError, match="Gemini API request failed"):
        await script_service._generate_with_retry("prompt", schema=schema)

    assert len(calls) == 1
    assert calls[0] == schema
