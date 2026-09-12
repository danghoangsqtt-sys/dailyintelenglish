"""Tests for YouTubeService (Task 1.9, Sub-task 1.9a).

No real network calls: `youtube_service._call_gemini` is monkeypatched, mirroring
tests/test_learning_service.py's approach for LearningService.
"""

import json

import pytest

from app.core.exceptions import ValidationError, YouTubePackageGenerationError
from app.core.constants import YOUTUBE_CHAPTER_MIN_LINES, YOUTUBE_CHAPTER_WORDS_PER_MINUTE
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import project_service, youtube_service

SAMPLE_PROJECT = {
    "name": "Future English",
    "topic": "Remote work culture",
    "cefr_level": "B1",
    "genre": "interview",
}

SAMPLE_SCRIPT_LINES = [
    {"text": "Welcome to the show! Today we're talking about remote work."},
    {"text": "Thanks for having me. I've been working remotely for five years."},
]

VALID_PACKAGE = {
    "titles": [
        {"variant": "click_worthy", "text": "You Won't Believe How Remote Work Changed"},
        {"variant": "educational", "text": "Learn English: Remote Work Vocabulary (B1)"},
        {"variant": "seo", "text": "Remote Work English Podcast B1 Interview"},
    ],
    "description": "An English-learning podcast episode about remote work culture, B1 level.",
    "tags": ["remote work", "english learning", "b1 podcast", "interview"],
}


class FakeResponse:
    """Stand-in for httpx.Response — carries only what youtube_service reads."""

    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or json.dumps(json_data or {})

    def json(self) -> dict:
        return self._json_data


def gemini_ok_response(package: dict, tokens_used: int = 400) -> FakeResponse:
    body = {
        "candidates": [{"content": {"parts": [{"text": json.dumps(package)}]}, "finishReason": "STOP"}],
        "usageMetadata": {"totalTokenCount": tokens_used},
    }
    return FakeResponse(200, body)


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(youtube_service.asyncio, "sleep", fake_sleep)
    return sleeps


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setattr(youtube_service.settings, "GEMINI_API_KEY", "test-key-not-real")


def queue_responses(monkeypatch, responses: list[FakeResponse]):
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str, schema: dict):
        index = calls["n"]
        calls["n"] += 1
        return responses[index], 12.3

    monkeypatch.setattr(youtube_service, "_call_gemini", fake_call_gemini)
    return calls


def make_project_config(**overrides) -> ScriptConfig:
    defaults = dict(
        name="YouTube Package Test Episode",
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


# --- estimate_chapters (pure function, no Gemini) ---


def test_estimate_chapters_empty_script_returns_empty_string():
    assert youtube_service.estimate_chapters([]) == ""


def test_estimate_chapters_first_chapter_is_always_introduction():
    lines = [{"text": "Hello and welcome to the show today."}]
    chapters = youtube_service.estimate_chapters(lines)
    assert chapters == "00:00 Introduction"


def test_estimate_chapters_starts_new_chapter_every_n_lines():
    lines = [{"text": f"Line number {i} has exactly five words."} for i in range(2 * YOUTUBE_CHAPTER_MIN_LINES + 1)]
    chapters = youtube_service.estimate_chapters(lines).split("\n")
    assert len(chapters) == 3  # a new chapter starts at index 0, N, and 2N
    for chapter in chapters:
        timestamp = chapter.split(" ", 1)[0]
        minutes, seconds = timestamp.split(":")
        assert minutes.isdigit() and seconds.isdigit() and len(seconds) == 2
    assert chapters[0] == "00:00 Introduction"


def test_estimate_chapters_timestamps_increase_with_word_count():
    long_line = " ".join(["word"] * 200)  # forces a large estimated elapsed time
    lines = [{"text": "intro"}] + [{"text": long_line} for _ in range(YOUTUBE_CHAPTER_MIN_LINES)]
    chapters = youtube_service.estimate_chapters(lines).split("\n")
    assert len(chapters) == 2
    assert chapters[0] == "00:00 Introduction"
    # Cumulative word count up to (not including) the second chapter's triggering line:
    # "intro" (1 word) + 3 long lines (200 words each) — the 4th long line is the trigger itself.
    words_before_second_chapter = 1 + 3 * 200
    expected_seconds = round(words_before_second_chapter / YOUTUBE_CHAPTER_WORDS_PER_MINUTE * 60)
    minutes, seconds = divmod(expected_seconds, 60)
    assert chapters[1].startswith(f"{minutes:02d}:{seconds:02d} ")
    assert chapters[1] != chapters[0]  # timestamp genuinely advanced, not stuck at 00:00


# --- generate_package ---


async def test_generate_package_success_on_http_200(monkeypatch):
    calls = queue_responses(monkeypatch, [gemini_ok_response(VALID_PACKAGE)])

    package = await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 1
    assert len(package["titles"]) == 3
    assert {title["variant"] for title in package["titles"]} == {"click_worthy", "educational", "seo"}
    assert package["description"] == VALID_PACKAGE["description"]
    assert package["tags"] == VALID_PACKAGE["tags"]
    assert package["chapters_text"] == "00:00 Introduction"


async def test_generate_package_retries_on_429_then_succeeds(monkeypatch, no_real_sleep):
    calls = queue_responses(
        monkeypatch, [FakeResponse(429, text="rate limited"), gemini_ok_response(VALID_PACKAGE)]
    )

    await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 2
    assert no_real_sleep == [1.0]


async def test_generate_package_exhausts_retries_raises(monkeypatch, no_real_sleep):
    calls = queue_responses(monkeypatch, [FakeResponse(429, text="rate limited")] * 4)

    with pytest.raises(YouTubePackageGenerationError, match="HTTP 429 after 4 attempt"):
        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 4


async def test_generate_package_non_429_error_does_not_retry(monkeypatch, no_real_sleep):
    calls = queue_responses(monkeypatch, [FakeResponse(500, text="internal error")])

    with pytest.raises(YouTubePackageGenerationError, match="HTTP 500"):
        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 1
    assert no_real_sleep == []


async def test_generate_package_invalid_json_raises(monkeypatch):
    body = {"candidates": [{"content": {"parts": [{"text": "not valid json"}]}}]}
    queue_responses(monkeypatch, [FakeResponse(200, body)])

    with pytest.raises(YouTubePackageGenerationError, match="valid JSON"):
        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)


async def test_generate_package_schema_validation_failure_raises(monkeypatch):
    bad_package = {"titles": [{"variant": "click_worthy", "text": "x"}], "description": "", "tags": []}
    queue_responses(monkeypatch, [gemini_ok_response(bad_package)])

    with pytest.raises(YouTubePackageGenerationError, match="schema validation"):
        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)


async def test_generate_package_duplicate_title_variants_rejected(monkeypatch):
    bad_package = {
        "titles": [
            {"variant": "click_worthy", "text": "One"},
            {"variant": "click_worthy", "text": "Two"},
            {"variant": "seo", "text": "Three"},
        ],
        "description": "desc",
        "tags": ["tag"],
    }
    queue_responses(monkeypatch, [gemini_ok_response(bad_package)])

    with pytest.raises(YouTubePackageGenerationError, match="schema validation"):
        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)


async def test_generate_package_empty_script_raises_without_calling_gemini(monkeypatch):
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str, schema: dict):
        calls["n"] += 1
        raise AssertionError("Gemini should never be called for an empty script")

    monkeypatch.setattr(youtube_service, "_call_gemini", fake_call_gemini)

    with pytest.raises(ValidationError, match="script is empty"):
        await youtube_service.generate_package(SAMPLE_PROJECT, [])

    assert calls["n"] == 0


async def test_generate_package_missing_api_key_raises_without_calling_gemini(monkeypatch):
    monkeypatch.setattr(youtube_service.settings, "GEMINI_API_KEY", "")
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str, schema: dict):
        calls["n"] += 1
        raise AssertionError("Gemini should never be called without an API key")

    monkeypatch.setattr(youtube_service, "_call_gemini", fake_call_gemini)

    with pytest.raises(YouTubePackageGenerationError, match="not configured"):
        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 0


async def test_call_gemini_includes_response_json_schema(monkeypatch):
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
            return FakeResponse(200, json_data={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    monkeypatch.setattr(youtube_service.httpx, "AsyncClient", FakeAsyncClient)

    schema = {"type": "object"}
    await youtube_service._call_gemini("test prompt", schema)

    gen_config = captured["json"]["generationConfig"]
    assert gen_config["responseMimeType"] == "application/json"
    assert gen_config["responseJsonSchema"] == schema
    assert "responseSchema" not in gen_config


# --- DB persistence ---


async def test_save_and_get_package_roundtrip(db):
    project = await project_service.create_project(db, make_project_config())
    package = {**VALID_PACKAGE, "chapters_text": "00:00 Introduction"}

    saved = await youtube_service.save_package(db, project["id"], package)

    assert len(saved["titles"]) == 3
    assert saved["tags"] == VALID_PACKAGE["tags"]
    assert saved["chapters_text"] == "00:00 Introduction"

    fetched = await youtube_service.get_package(db, project["id"])
    assert fetched == saved


async def test_get_package_returns_none_before_generation(db):
    project = await project_service.create_project(db, make_project_config())

    assert await youtube_service.get_package(db, project["id"]) is None


async def test_save_package_upserts_on_repeat_save(db):
    project = await project_service.create_project(db, make_project_config())
    package = {**VALID_PACKAGE, "chapters_text": "00:00 Introduction"}

    first = await youtube_service.save_package(db, project["id"], package)
    second_package = {**package, "description": "A totally different description."}
    second = await youtube_service.save_package(db, project["id"], second_package)

    assert first["id"] == second["id"]  # same row, replaced — not duplicated
    assert second["description"] == "A totally different description."

    fetched = await youtube_service.get_package(db, project["id"])
    assert fetched["description"] == "A totally different description."


async def test_deleting_project_cascades_to_youtube_package(db):
    project = await project_service.create_project(db, make_project_config())
    package = {**VALID_PACKAGE, "chapters_text": "00:00 Introduction"}
    await youtube_service.save_package(db, project["id"], package)

    await project_service.delete_project(db, project["id"])

    assert await youtube_service.get_package(db, project["id"]) is None
