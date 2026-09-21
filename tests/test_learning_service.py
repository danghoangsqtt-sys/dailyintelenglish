"""Tests for LearningService (ROADMAP Task 1.5 — Sprint 1.5A).

No real network calls: since Task 13.7, `generate_learning_pack` is exercised
through an injected `FakeProvider`-backed `AIRouter` -- mirrors
tests/test_script_service.py's approach for ScriptService. The router/provider
layer's own retry/fallback/timeout policy is covered by tests/test_ai_router.py
and tests/test_ai_providers.py.
"""

import json

import pytest

from app.core.exceptions import LearningGenerationError, NotFoundError, ProviderUnavailableError
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import learning_service, project_service
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter

SAMPLE_CONFIG = {
    "topic": "Remote work culture",
    "cefr_level": "B1",
    "genre": "interview",
}

SAMPLE_SCRIPT_LINES = [
    {"text": "Welcome to the show! Today we're talking about remote work."},
    {"text": "Thanks for having me. I've been working remotely for five years."},
]

VALID_PACK = {
    "vocabulary": [
        {
            "word": "remote",
            "part_of_speech": "adjective",
            "ipa": "/rɪˈmoʊt/",
            "definition_en": "far away, not in the same place",
            "definition_vi": "từ xa",
            "example_sentence": "I've been working remotely for five years.",
        }
    ],
    "idioms": [
        {
            "phrase": "thanks for having me",
            "meaning_en": "a polite way to thank a host for an invitation",
            "meaning_vi": "cảm ơn đã mời tôi",
            "example_sentence": "Thanks for having me.",
        }
    ],
    "grammar": [
        {
            "point": "Present Perfect Continuous",
            "structure": "subject + have/has + been + verb-ing",
            "explanation_en": "used for an action that started in the past and continues now",
            "explanation_vi": "diễn tả hành động bắt đầu trong quá khứ và tiếp diễn đến hiện tại",
            "examples": ["I've been working remotely for five years."],
        }
    ],
    "questions": [
        {
            "question": "How long has the guest been working remotely?",
            "options": ["1 year", "3 years", "5 years", "10 years"],
            "correct_answer": "5 years",
            "explanation": "The guest says they've been working remotely for five years.",
        }
    ],
}


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    """Every test gets a deterministic fake key by default, regardless of the real
    ambient .env -- the explicit missing-key test overrides this to "" itself."""
    monkeypatch.setattr(learning_service.settings, "GEMINI_API_KEY", "test-key-not-real")


def _pack_result(pack: dict) -> GenerationResult:
    """A scripted successful `AIRouter.generate()` result carrying `pack` as JSON text."""
    return _pack_result_from_text(json.dumps(pack))


def _pack_result_from_text(text: str) -> GenerationResult:
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
    """Build an `AIRouter` over two `FakeProvider`s -- no network, deterministic."""
    gemini = FakeProvider("fake-gemini", gemini_outcomes)
    local = FakeProvider("fake-ollama", local_outcomes or [])
    return AIRouter(local=local, gemini=gemini, mode=mode)


async def _no_op_sleep(delay: float) -> None:
    """Task 14.1 amendment A: patched onto `app.services.ai.router.sleep` in the
    provider-exhaustion test below so real transient-error backoff (1s+2s+4s)
    doesn't actually elapse -- see tests/test_ai_router.py's `sleep_calls` fixture
    for the same pattern."""
    return None


def make_project_config(**overrides) -> ScriptConfig:
    defaults = dict(
        name="Learning Content Test Episode",
        topic="Remote work culture",
        cefr_level="B1",
        duration_minutes=8.0,
        num_speakers=2,
        genre="interview",
        accent="american",
        speakers=[
            SpeakerConfig(name="Alex", gender="male", accent="american"),
            SpeakerConfig(name="Sam", gender="female", accent="british"),
        ],
    )
    defaults.update(overrides)
    return ScriptConfig(**defaults)


# --- render_learning_prompt ---


async def test_render_learning_prompt_injects_all_variables():
    prompt = await learning_service.render_learning_prompt(
        topic="Remote work culture",
        cefr_level="B1",
        genre="interview",
        transcript_text="Welcome to the show!\nThanks for having me.",
    )

    assert "Remote work culture" in prompt
    assert "interview" in prompt
    assert "B1" in prompt
    assert "Welcome to the show!" in prompt
    assert "Thanks for having me." in prompt


async def test_render_learning_prompt_different_cefr_and_genre():
    prompt = await learning_service.render_learning_prompt(
        topic="Climate change",
        cefr_level="C1",
        genre="debate",
        transcript_text="Some transcript text.",
    )

    assert "Climate change" in prompt
    assert "debate" in prompt
    assert "C1" in prompt


async def test_render_learning_prompt_rejects_unknown_cefr_level():
    from app.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="CEFR level"):
        await learning_service.render_learning_prompt(
            topic="Test", cefr_level="Z9", genre="interview", transcript_text="text"
        )


async def test_render_learning_prompt_rejects_unknown_genre():
    from app.core.exceptions import ValidationError

    with pytest.raises(ValidationError, match="genre"):
        await learning_service.render_learning_prompt(
            topic="Test", cefr_level="B1", genre="not-a-real-genre", transcript_text="text"
        )


# --- generate_learning_pack ---


async def test_generate_learning_pack_success_via_gateway():
    router = _gateway_router(AIMode.GEMINI, [_pack_result(VALID_PACK)])

    pack = await learning_service.generate_learning_pack(
        "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES, router=router
    )

    assert len(pack.vocabulary) == 1
    assert pack.vocabulary[0].word == "remote"
    assert len(pack.idioms) == 1
    assert len(pack.grammar) == 1
    assert len(pack.questions) == 1
    assert pack.questions[0].correct_answer == "5 years"


async def test_generate_learning_pack_wraps_provider_error(monkeypatch):
    """Once the router (its own retry/fallback policy -- see test_ai_router.py) exhausts
    every attempt, generate_learning_pack wraps the failure.

    Task 14.1 amendment A: 4 outcomes (not 2) for a real AI_TRANSIENT_MAX_ATTEMPTS
    exhaustion, `app.services.ai.router.sleep` patched to a no-op.
    """
    monkeypatch.setattr("app.services.ai.router.sleep", _no_op_sleep)
    router = _gateway_router(AIMode.GEMINI, [ProviderUnavailableError("down")] * 4)

    with pytest.raises(LearningGenerationError, match="Learning content generation failed"):
        await learning_service.generate_learning_pack(
            "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES, router=router
        )


async def test_generate_learning_pack_invalid_json_raises():
    router = _gateway_router(AIMode.GEMINI, [_pack_result_from_text("not valid json")])

    with pytest.raises(LearningGenerationError, match="not valid JSON"):
        await learning_service.generate_learning_pack(
            "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES, router=router
        )


async def test_generate_learning_pack_schema_validation_failure_raises():
    bad_pack = {"vocabulary": [{"word": "remote"}]}  # missing required fields
    router = _gateway_router(AIMode.GEMINI, [_pack_result(bad_pack)])

    with pytest.raises(LearningGenerationError, match="schema validation"):
        await learning_service.generate_learning_pack(
            "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES, router=router
        )


async def test_generate_learning_pack_empty_script_raises_without_calling_router():
    router = _gateway_router(AIMode.GEMINI, [])

    with pytest.raises(LearningGenerationError, match="script is empty"):
        await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, [], router=router)


async def test_generate_learning_pack_missing_api_key_raises_without_calling_router(monkeypatch):
    """AI_MODE=gemini (the packaged default) still hard-requires a Gemini key
    upfront -- byte-identical behavior to before Task 13.7's migration."""
    monkeypatch.setattr(learning_service.settings, "AI_MODE", "gemini")
    monkeypatch.setattr(learning_service.settings, "GEMINI_API_KEY", "")
    router = _gateway_router(AIMode.GEMINI, [])

    with pytest.raises(LearningGenerationError, match="not configured"):
        await learning_service.generate_learning_pack(
            "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES, router=router
        )


async def test_generate_learning_pack_local_mode_needs_no_gemini_key():
    """Task 13.7: the upfront key guard is mode-aware -- AI_MODE=local/hybrid must not
    be blocked by a missing Gemini key, since local generation never needs one."""
    router = _gateway_router(AIMode.LOCAL, gemini_outcomes=[], local_outcomes=[_pack_result(VALID_PACK)])

    pack = await learning_service.generate_learning_pack(
        "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES, router=router
    )

    assert len(pack.vocabulary) == 1


async def test_generate_learning_pack_preserves_cefr_level_in_prompt(monkeypatch):
    """The rendered prompt actually carries the project's CEFR level through to the provider."""
    captured = {}

    class _CapturingProvider:
        name = "fake-gemini"

        async def generate(self, request):
            captured["prompt"] = request.prompt
            return _pack_result(VALID_PACK)

    router = AIRouter(local=FakeProvider("fake-ollama", []), gemini=_CapturingProvider(), mode=AIMode.GEMINI)

    await learning_service.generate_learning_pack(
        "proj-1", {**SAMPLE_CONFIG, "cefr_level": "C2"}, SAMPLE_SCRIPT_LINES, router=router
    )

    assert "C2" in captured["prompt"]


# --- DB persistence ---


async def test_save_and_get_learning_content_roundtrip(db):
    project = await project_service.create_project(db, make_project_config())

    saved = await learning_service.save_learning_content(db, project["id"], VALID_PACK)

    assert saved["vocabulary"][0]["word"] == "remote"
    assert saved["questions"][0]["correct_answer"] == "5 years"

    fetched = await learning_service.get_learning_content(db, project["id"])
    assert fetched == saved


async def test_get_learning_content_returns_none_before_generation(db):
    project = await project_service.create_project(db, make_project_config())

    result = await learning_service.get_learning_content(db, project["id"])

    assert result is None


async def test_save_learning_content_upserts_on_repeat_save(db):
    project = await project_service.create_project(db, make_project_config())

    first = await learning_service.save_learning_content(db, project["id"], VALID_PACK)
    second_pack = {**VALID_PACK, "vocabulary": [{**VALID_PACK["vocabulary"][0], "word": "distant"}]}
    second = await learning_service.save_learning_content(db, project["id"], second_pack)

    assert first["id"] == second["id"]  # same row, replaced — not duplicated
    assert second["vocabulary"][0]["word"] == "distant"

    fetched = await learning_service.get_learning_content(db, project["id"])
    assert len(fetched["vocabulary"]) == 1
    assert fetched["vocabulary"][0]["word"] == "distant"


async def test_update_learning_content_merges_partial_patch(db):
    project = await project_service.create_project(db, make_project_config())
    await learning_service.save_learning_content(db, project["id"], VALID_PACK)

    updated = await learning_service.update_learning_content(
        db, project["id"], {"grammar": []}
    )

    assert updated["grammar"] == []
    # Untouched fields are preserved, not wiped out by the partial patch.
    assert updated["vocabulary"] == VALID_PACK["vocabulary"]
    assert updated["idioms"] == VALID_PACK["idioms"]
    assert updated["questions"] == VALID_PACK["questions"]


async def test_update_learning_content_raises_not_found_when_nothing_generated(db):
    project = await project_service.create_project(db, make_project_config())

    with pytest.raises(NotFoundError):
        await learning_service.update_learning_content(db, project["id"], {"grammar": []})


async def test_deleting_project_cascades_to_learning_content(db):
    project = await project_service.create_project(db, make_project_config())
    await learning_service.save_learning_content(db, project["id"], VALID_PACK)

    await project_service.delete_project(db, project["id"])

    assert await learning_service.get_learning_content(db, project["id"]) is None


# Note: the responseJsonSchema-not-responseSchema wire-payload regression (BUG-011)
# is now covered once, at the shared gateway layer, by
# tests/test_ai_providers.py::test_gemini_provider_wire_payload_uses_response_json_schema_not_response_schema
# -- every Task 13.7-migrated consumer (script/learning/thumbnail/youtube) shares
# that one code path, so per-service duplication of this test is no longer needed.
