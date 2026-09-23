"""Tests for ScriptService (ROADMAP Task 1.4 — Sprint 1.4B).

No real network calls: since Task 13.7, `generate_script`/`regenerate_line` are
exercised through an injected `FakeProvider`-backed `AIRouter` (see
`app/services/ai/fake_provider.py`, `tests/test_ai_router.py`) instead of
monkeypatching a per-service HTTP transport -- the router/provider layer's own
retry/fallback/timeout policy is already covered by `tests/test_ai_router.py` and
`tests/test_ai_providers.py`, so these tests only prove `script_service` calls the
gateway correctly and applies its own script-specific validation on top.
"""

import json

import pytest

from app.core.exceptions import ProviderUnavailableError, ScriptGenerationError
from app.services import script_service
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter

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


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    """Every test gets a deterministic fake key by default, regardless of the real
    ambient .env -- the explicit missing-key test overrides this to "" itself."""
    monkeypatch.setattr(script_service.settings, "GEMINI_API_KEY", "test-key-not-real")


def _script_result(lines: list[dict]) -> GenerationResult:
    """A scripted successful `AIRouter.generate()` result carrying `lines` as JSON text."""
    return _script_result_from_text(json.dumps(lines))


def _script_result_from_text(text: str) -> GenerationResult:
    """A scripted `AIRouter.generate()` result carrying raw `text` (e.g. invalid JSON)."""
    return GenerationResult(
        text=text,
        provider="fake-provider",
        model="fake-model",
        latency_ms=1.0,
        attempt=1,
        prompt_hash="abc123",
    )


def _gateway_router(mode: AIMode, gemini_outcomes: list, local_outcomes: list | None = None) -> AIRouter:
    """Build an `AIRouter` over two `FakeProvider`s -- no network, deterministic.
    `gemini_outcomes`/`local_outcomes` are historical parameter names (predating
    Phase 18's cloud-first router roles) for what's now `primary`/`fallback` --
    every call site here uses `AIMode.CLOUD` (single-provider, mechanical
    rename from `AIMode.GEMINI`), never `AIMode.CLOUD_FIRST`, so no role
    inversion applies."""
    gemini = FakeProvider("fake-gemini", gemini_outcomes)
    local = FakeProvider("fake-ollama", local_outcomes or [])
    return AIRouter(primary=gemini, fallback=local, mode=mode)


async def _no_op_sleep(delay: float) -> None:
    """Task 14.1 amendment A: patched onto `app.services.ai.router.sleep` in the
    provider-exhaustion tests below so real transient-error backoff (1s+2s+4s)
    doesn't actually elapse -- see tests/test_ai_router.py's `sleep_calls` fixture
    for the same pattern."""
    return None


async def test_generate_script_success_via_gateway():
    router = _gateway_router(AIMode.CLOUD, [_script_result(VALID_LINES)])

    lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)

    assert len(lines) == 2
    assert lines[0].speaker_id == "11111111-1111-1111-1111-111111111111"
    assert lines[0].text == "Welcome to the show!"
    assert lines[1].speaker_id == "22222222-2222-2222-2222-222222222222"


async def test_generate_script_wraps_provider_error_as_script_generation_error(monkeypatch):
    """Once the router (its own retry/fallback policy -- see test_ai_router.py) exhausts
    every attempt, generate_script wraps the failure, matching regenerate_line's contract.

    Task 14.1 amendment A: the router now makes AI_TRANSIENT_MAX_ATTEMPTS=4 attempts
    with backoff before giving up, so 4 outcomes (not 2) are needed for a real
    exhaustion, and `app.services.ai.router.sleep` is patched to a no-op so this test
    doesn't really wait out 1s+2s+4s of backoff.
    """
    monkeypatch.setattr("app.services.ai.router.sleep", _no_op_sleep)
    router = _gateway_router(AIMode.CLOUD, [ProviderUnavailableError("down")] * 4)

    with pytest.raises(ScriptGenerationError, match="Script generation failed"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)


async def test_generate_script_invalid_json_raises():
    router = _gateway_router(AIMode.CLOUD, [_script_result_from_text("not valid json")])

    with pytest.raises(ScriptGenerationError, match="not valid JSON"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)


async def test_generate_script_schema_validation_failure_raises():
    bad_lines = [{"id": "line_001", "speaker_id": "11111111-1111-1111-1111-111111111111"}]  # missing "text"
    router = _gateway_router(AIMode.CLOUD, [_script_result(bad_lines)])

    with pytest.raises(ScriptGenerationError, match="schema validation"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)


async def test_generate_script_rejects_name_as_speaker_id():
    """Regression test for Sprint 1.4A fix #1: speaker_id must be a UUID, not a name."""
    lines_with_name_id = [{**VALID_LINES[0], "speaker_id": "Alex"}]
    router = _gateway_router(AIMode.CLOUD, [_script_result(lines_with_name_id)])

    with pytest.raises(ScriptGenerationError, match="schema validation"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)


async def test_generate_script_rejects_unknown_speaker_uuid():
    hallucinated = [{**VALID_LINES[0], "speaker_id": "99999999-9999-9999-9999-999999999999"}]
    router = _gateway_router(AIMode.CLOUD, [_script_result(hallucinated)])

    with pytest.raises(ScriptGenerationError, match="not in project"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)


async def test_generate_script_empty_script_raises():
    router = _gateway_router(AIMode.CLOUD, [_script_result([])])

    with pytest.raises(ScriptGenerationError, match="empty script"):
        await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)


async def test_generate_script_local_mode_needs_no_gemini_key():
    """Task 13.7: local generation never needs a Gemini key."""
    router = _gateway_router(AIMode.LOCAL, gemini_outcomes=[], local_outcomes=[_script_result(VALID_LINES)])

    lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG, router=router)

    assert len(lines) == 2


async def test_generate_script_cloud_first_mode_with_no_key_falls_through_to_local_without_raising(monkeypatch):
    """Phase 18/invariant 32, end to end at the service layer (PM Amendment B,
    replacing the deleted upfront-key guard's own
    `test_generate_script_missing_api_key_raises_without_calling_router`,
    whose entire premise -- a missing cloud key must raise before the router
    is even built -- is now the wrong behaviour): `AI_MODE=cloud_first` with
    `AI_ALLOW_CLOUD=true` but no configured `OPENAI_COMPAT_API_KEY` must NOT
    raise. `compute_effective_mode` collapses it to `local` automatically, and
    generation proceeds via the *real* `build_ai_router_from_settings()`
    wiring (no injected `router=`, unlike every other test in this file) --
    reaching `OllamaProvider`'s own HTTP call, mocked here via
    `httpx.MockTransport` so this never touches a real network or Ollama
    process, matching this file's "no real network calls" header."""
    import httpx

    from app.services.ai import ollama_provider as ollama_provider_module

    monkeypatch.setattr(script_service.settings, "AI_MODE", "cloud_first")
    monkeypatch.setattr(script_service.settings, "AI_ALLOW_CLOUD", True)
    monkeypatch.setattr(script_service.settings, "OPENAI_COMPAT_API_KEY", "")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"response": json.dumps(VALID_LINES), "eval_count": 1})

    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(ollama_provider_module.httpx, "AsyncClient", _factory)

    lines = await script_service.generate_script("proj-1", SAMPLE_CONFIG)  # router=None -- real wiring

    assert len(lines) == 2


async def test_regenerate_line_via_injected_gateway_router_returns_validated_line():
    """regenerate_line accepts an injected AIRouter (Task 13.4) -- proves the
    gateway migration actually routes through AIRouter.generate(), not just that
    the legacy httpx path still happens to work."""
    from app.services.ai.contracts import AIMode, GenerationResult
    from app.services.ai.fake_provider import FakeProvider
    from app.services.ai.router import AIRouter

    scripted = GenerationResult(
        text=json.dumps(VALID_LINES[0]),
        provider="fake-gemini",
        model="fake-model",
        latency_ms=1.0,
        attempt=1,
        prompt_hash="abc123",
    )
    gemini = FakeProvider("fake-gemini", [scripted])
    local = FakeProvider("fake-ollama", [])
    router = AIRouter(primary=gemini, fallback=local, mode=AIMode.CLOUD)

    line = await script_service.regenerate_line(
        "proj-1",
        SAMPLE_CONFIG,
        "line_001",
        "old text",
        "11111111-1111-1111-1111-111111111111",
        router=router,
    )
    assert line.id == "line_001"
    assert gemini.call_count == 1
    assert local.call_count == 0


async def test_regenerate_line_wraps_provider_error_as_script_generation_error(monkeypatch):
    """Task 14.1 amendment A: see test_generate_script_wraps_provider_error_as_script_generation_error
    above -- 4 outcomes for a real exhaustion, `sleep` patched to a no-op."""
    from app.core.exceptions import ProviderUnavailableError
    from app.services.ai.contracts import AIMode
    from app.services.ai.fake_provider import FakeProvider
    from app.services.ai.router import AIRouter

    monkeypatch.setattr("app.services.ai.router.sleep", _no_op_sleep)
    gemini = FakeProvider("fake-gemini", [ProviderUnavailableError("down")] * 4)
    local = FakeProvider("fake-ollama", [])
    router = AIRouter(primary=gemini, fallback=local, mode=AIMode.CLOUD)

    with pytest.raises(ScriptGenerationError, match="Line regeneration failed"):
        await script_service.regenerate_line(
            "proj-1",
            SAMPLE_CONFIG,
            "line_001",
            "old text",
            "11111111-1111-1111-1111-111111111111",
            router=router,
        )


async def test_regenerate_line_still_rejects_speaker_id_change_via_gateway():
    from app.services.ai.contracts import AIMode, GenerationResult
    from app.services.ai.fake_provider import FakeProvider
    from app.services.ai.router import AIRouter

    wrong_speaker_line = dict(VALID_LINES[0])
    wrong_speaker_line["speaker_id"] = "22222222-2222-2222-2222-222222222222"
    scripted = GenerationResult(
        text=json.dumps(wrong_speaker_line),
        provider="fake-gemini",
        model="fake-model",
        latency_ms=1.0,
        attempt=1,
        prompt_hash="abc123",
    )
    gemini = FakeProvider("fake-gemini", [scripted])
    local = FakeProvider("fake-ollama", [])
    router = AIRouter(primary=gemini, fallback=local, mode=AIMode.CLOUD)

    with pytest.raises(ScriptGenerationError, match="changed speaker_id"):
        await script_service.regenerate_line(
            "proj-1",
            SAMPLE_CONFIG,
            "line_001",
            "old text",
            "11111111-1111-1111-1111-111111111111",
            router=router,
        )


async def test_update_script_line_clears_stale_cached_audio(db):
    """Task 10.1 (BUG-018): a line's cached TTS audio was synthesized from the text
    being replaced here, so it must not survive the text change."""
    await db.execute(
        "INSERT INTO projects (id, name, status, created_at, updated_at) "
        "VALUES ('p1', 'Test', 'script_generated', 't', 't')"
    )
    await db.execute(
        "INSERT INTO speakers (id, project_id, speaker_index, name) "
        "VALUES ('sp1', 'p1', 0, 'Alex')"
    )
    await db.execute(
        "INSERT INTO script_lines "
        "(id, project_id, line_index, speaker_id, text, language_notes, "
        "audio_cache_path, duration_seconds) "
        "VALUES ('line_001', 'p1', 0, 'sp1', 'Old text.', '{}', 'old-cache.mp3', 3.5)"
    )
    await db.commit()

    updated = await script_service.update_script_line(
        db, "p1", "line_001", "New text.", {"collocations": [], "idioms": [], "grammar_point": None}
    )

    assert updated["text"] == "New text."
    assert updated["duration_seconds"] is None
    cursor = await db.execute(
        "SELECT audio_cache_path, duration_seconds FROM script_lines WHERE id = 'line_001'"
    )
    row = await cursor.fetchone()
    assert row["audio_cache_path"] is None
    assert row["duration_seconds"] is None
