"""Tests for LearningService (ROADMAP Task 1.5 — Sprint 1.5A).

No real network calls: `learning_service._call_gemini` is monkeypatched with a
fake async function that returns canned (FakeResponse, latency_ms) pairs, and
`asyncio.sleep` is monkeypatched to a no-op so retry tests run instantly —
mirrors tests/test_script_service.py's approach for ScriptService.
"""

import json

import pytest

from app.core.exceptions import LearningGenerationError, NotFoundError
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import learning_service, project_service

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


class FakeResponse:
    """Stand-in for httpx.Response — carries only what learning_service reads."""

    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or json.dumps(json_data or {})

    def json(self) -> dict:
        return self._json_data


def gemini_ok_response(pack: dict, tokens_used: int = 500) -> FakeResponse:
    """A fake HTTP 200 Gemini response wrapping `pack` as the JSON-object text payload."""
    body = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(pack)}]}, "finishReason": "STOP"}],
        "usageMetadata": {"totalTokenCount": tokens_used},
    }
    return FakeResponse(200, body)


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    """Retry tests must not actually wait — patch asyncio.sleep to a no-op."""
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(learning_service.asyncio, "sleep", fake_sleep)
    return sleeps


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(learning_service.settings, "GEMINI_API_KEY", "test-key-not-real")


def queue_responses(monkeypatch, responses: list[FakeResponse]):
    """Monkeypatch _call_gemini to return `responses` in order, one per call."""
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str):
        index = calls["n"]
        calls["n"] += 1
        return responses[index], 12.3

    monkeypatch.setattr(learning_service, "_call_gemini", fake_call_gemini)
    return calls


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


async def test_generate_learning_pack_success_on_http_200(monkeypatch):
    calls = queue_responses(monkeypatch, [gemini_ok_response(VALID_PACK)])

    pack = await learning_service.generate_learning_pack(
        "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES
    )

    assert calls["n"] == 1
    assert len(pack.vocabulary) == 1
    assert pack.vocabulary[0].word == "remote"
    assert len(pack.idioms) == 1
    assert len(pack.grammar) == 1
    assert len(pack.questions) == 1
    assert pack.questions[0].correct_answer == "5 years"


async def test_generate_learning_pack_retries_on_429_then_succeeds(monkeypatch, no_real_sleep):
    calls = queue_responses(
        monkeypatch,
        [FakeResponse(429, text="rate limited"), gemini_ok_response(VALID_PACK)],
    )

    pack = await learning_service.generate_learning_pack(
        "proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES
    )

    assert calls["n"] == 2
    assert len(pack.vocabulary) == 1
    assert no_real_sleep == [1.0]  # GEMINI_RETRY_BASE_DELAY, exactly one backoff step


async def test_generate_learning_pack_backoff_sequence_is_1s_2s_4s(monkeypatch, no_real_sleep):
    queue_responses(
        monkeypatch,
        [
            FakeResponse(429, text="rate limited"),
            FakeResponse(429, text="rate limited"),
            FakeResponse(429, text="rate limited"),
            gemini_ok_response(VALID_PACK),
        ],
    )

    await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)

    assert no_real_sleep == [1.0, 2.0, 4.0]


async def test_generate_learning_pack_exhausts_retries_raises(monkeypatch, no_real_sleep):
    calls = queue_responses(monkeypatch, [FakeResponse(429, text="rate limited")] * 4)

    with pytest.raises(LearningGenerationError, match="HTTP 429 after 4 attempt"):
        await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 4
    assert no_real_sleep == [1.0, 2.0, 4.0]


async def test_generate_learning_pack_non_429_error_does_not_retry(monkeypatch, no_real_sleep):
    calls = queue_responses(monkeypatch, [FakeResponse(500, text="internal error")])

    with pytest.raises(LearningGenerationError, match="HTTP 500"):
        await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 1
    assert no_real_sleep == []


async def test_generate_learning_pack_invalid_json_raises(monkeypatch):
    body = {"candidates": [{"content": {"parts": [{"text": "not valid json"}]}}]}
    queue_responses(monkeypatch, [FakeResponse(200, body)])

    with pytest.raises(LearningGenerationError, match="valid JSON"):
        await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)


async def test_generate_learning_pack_schema_validation_failure_raises(monkeypatch):
    bad_pack = {"vocabulary": [{"word": "remote"}]}  # missing required fields
    queue_responses(monkeypatch, [gemini_ok_response(bad_pack)])

    with pytest.raises(LearningGenerationError, match="schema validation"):
        await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)


async def test_generate_learning_pack_empty_script_raises_without_calling_gemini(monkeypatch):
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str):
        calls["n"] += 1
        raise AssertionError("Gemini should never be called for an empty script")

    monkeypatch.setattr(learning_service, "_call_gemini", fake_call_gemini)

    with pytest.raises(LearningGenerationError, match="script is empty"):
        await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, [])

    assert calls["n"] == 0


async def test_generate_learning_pack_missing_api_key_raises_without_calling_gemini(monkeypatch):
    monkeypatch.setattr(learning_service.settings, "GEMINI_API_KEY", "")
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str):
        calls["n"] += 1
        raise AssertionError("Gemini should never be called without an API key")

    monkeypatch.setattr(learning_service, "_call_gemini", fake_call_gemini)

    with pytest.raises(LearningGenerationError, match="not configured"):
        await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 0


async def test_generate_learning_pack_preserves_cefr_level_in_prompt(monkeypatch):
    """The rendered prompt actually carries the project's CEFR level through to Gemini."""
    captured = {}

    async def fake_call_gemini(prompt: str):
        captured["prompt"] = prompt
        return gemini_ok_response(VALID_PACK), 5.0

    monkeypatch.setattr(learning_service, "_call_gemini", fake_call_gemini)

    await learning_service.generate_learning_pack(
        "proj-1", {**SAMPLE_CONFIG, "cefr_level": "C2"}, SAMPLE_SCRIPT_LINES
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
