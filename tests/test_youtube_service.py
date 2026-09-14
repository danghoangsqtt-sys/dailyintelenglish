"""Tests for YouTubeService (Task 1.9, Sub-task 1.9a).

No real network calls: `youtube_service._call_gemini` is monkeypatched, mirroring
tests/test_learning_service.py's approach for LearningService.
"""

import io
import json
import zipfile

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
    """Monkeypatch _call_gemini to return `responses` in order, recording each `model` used."""
    calls = {"n": 0, "models": []}

    async def fake_call_gemini(prompt: str, schema: dict, model: str | None = None):
        index = calls["n"]
        calls["n"] += 1
        calls["models"].append(model)
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


# --- real_chapters_from_timestamps (pure function, no Gemini) ---


def test_real_chapters_empty_timestamps_returns_empty_string():
    assert youtube_service.real_chapters_from_timestamps([]) == ""


def test_real_chapters_first_chapter_is_always_introduction():
    timestamps = [{"start_sec": 0.0, "end_sec": 1.0, "text": "Hello!"}]
    assert youtube_service.real_chapters_from_timestamps(timestamps) == "00:00 Introduction"


def test_real_chapters_uses_real_seconds_not_word_count():
    timestamps = [{"start_sec": float(i), "end_sec": float(i + 1), "text": f"Line {i}"} for i in range(YOUTUBE_CHAPTER_MIN_LINES + 1)]
    chapters = youtube_service.real_chapters_from_timestamps(timestamps).split("\n")
    assert len(chapters) == 2
    assert chapters[0] == "00:00 Introduction"
    minutes, seconds = divmod(YOUTUBE_CHAPTER_MIN_LINES, 60)
    assert chapters[1].startswith(f"{minutes:02d}:{seconds:02d} ")
    assert f"Line {YOUTUBE_CHAPTER_MIN_LINES}" in chapters[1]


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
    assert package["chapters_estimated"] is True


async def test_generate_package_without_timestamps_falls_back_to_estimate(monkeypatch):
    queue_responses(monkeypatch, [gemini_ok_response(VALID_PACKAGE)])

    package = await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES, timestamps=None)

    assert package["chapters_estimated"] is True
    assert package["chapters_text"] == youtube_service.estimate_chapters(SAMPLE_SCRIPT_LINES)


async def test_generate_package_with_timestamps_uses_measured_chapters(monkeypatch):
    queue_responses(monkeypatch, [gemini_ok_response(VALID_PACKAGE)])
    timestamps = [
        {"start_sec": 0.0, "end_sec": 1.0, "text": SAMPLE_SCRIPT_LINES[0]["text"]},
        {"start_sec": 5.0, "end_sec": 6.0, "text": SAMPLE_SCRIPT_LINES[1]["text"]},
    ]

    package = await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES, timestamps=timestamps)

    assert package["chapters_estimated"] is False
    assert package["chapters_text"] == youtube_service.real_chapters_from_timestamps(timestamps)


async def test_generate_package_retries_on_429_then_succeeds(monkeypatch, no_real_sleep):
    calls = queue_responses(
        monkeypatch, [FakeResponse(429, text="rate limited"), gemini_ok_response(VALID_PACKAGE)]
    )

    await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 2
    assert no_real_sleep == [1.0]


async def test_generate_package_exhausts_one_model_then_falls_back(monkeypatch, no_real_sleep):
    """After 4 failed attempts on the primary model, the next fallback model is tried."""
    calls = queue_responses(
        monkeypatch,
        [FakeResponse(429, text="rate limited")] * 4 + [gemini_ok_response(VALID_PACKAGE)],
    )

    package = await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert len(package["titles"]) == 3
    assert calls["n"] == 5
    assert calls["models"] == [youtube_service.GEMINI_MODEL_FALLBACKS[0]] * 4 + [
        youtube_service.GEMINI_MODEL_FALLBACKS[1]
    ]


async def test_generate_package_retries_on_503_then_succeeds(monkeypatch, no_real_sleep):
    """503 (model temporarily overloaded) is retried just like 429, not treated as fatal."""
    calls = queue_responses(
        monkeypatch, [FakeResponse(503, text="model overloaded"), gemini_ok_response(VALID_PACKAGE)]
    )

    await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 2
    assert no_real_sleep == [1.0]


async def test_generate_package_exhausts_all_fallback_models_raises(monkeypatch, no_real_sleep):
    """Only once every model in GEMINI_MODEL_FALLBACKS is exhausted does generation fail."""
    fallbacks = youtube_service.GEMINI_MODEL_FALLBACKS
    calls = queue_responses(monkeypatch, [FakeResponse(429, text="rate limited")] * (4 * len(fallbacks)))

    with pytest.raises(YouTubePackageGenerationError, match="exhausting all fallback models") as exc_info:
        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

    assert calls["n"] == 4 * len(fallbacks)
    assert calls["models"] == [model for model in fallbacks for _ in range(4)]
    for model in fallbacks:
        assert model in str(exc_info.value)


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

    async def fake_call_gemini(prompt: str, schema: dict, model: str | None = None):
        calls["n"] += 1
        raise AssertionError("Gemini should never be called for an empty script")

    monkeypatch.setattr(youtube_service, "_call_gemini", fake_call_gemini)

    with pytest.raises(ValidationError, match="script is empty"):
        await youtube_service.generate_package(SAMPLE_PROJECT, [])

    assert calls["n"] == 0


async def test_generate_package_missing_api_key_raises_without_calling_gemini(monkeypatch):
    monkeypatch.setattr(youtube_service.settings, "GEMINI_API_KEY", "")
    calls = {"n": 0}

    async def fake_call_gemini(prompt: str, schema: dict, model: str | None = None):
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


async def test_save_package_persists_chapters_estimated_flag(db):
    project = await project_service.create_project(db, make_project_config())
    measured = {**VALID_PACKAGE, "chapters_text": "00:00 Introduction", "chapters_estimated": False}

    saved = await youtube_service.save_package(db, project["id"], measured)
    assert saved["chapters_estimated"] is False

    fetched = await youtube_service.get_package(db, project["id"])
    assert fetched["chapters_estimated"] is False

    # Regenerating without audio (chapters_estimated defaults True) flips it back.
    estimated_again = {**VALID_PACKAGE, "chapters_text": "00:00 Introduction"}
    resaved = await youtube_service.save_package(db, project["id"], estimated_again)
    assert resaved["chapters_estimated"] is True


# --- transcript and Learning Content formatting ---


def _project_with_speakers() -> dict:
    return {
        "speakers": [
            {"id": "speaker-alex", "name": "Alex"},
            {"id": "speaker-linh", "name": "Linh"},
        ]
    }


def _full_learning_content() -> dict:
    return {
        "vocabulary": [
            {
                "word": "nuance",
                "part_of_speech": "noun",
                "ipa": "/ˈnjuːɑːns/",
                "definition_en": "a subtle difference",
                "definition_vi": "một sắc thái khác biệt tinh tế",
                "example_sentence": "Linh explained every nuance clearly.",
            }
        ],
        "idioms": [
            {
                "phrase": "break the ice",
                "meaning_en": "make people feel more comfortable",
                "meaning_vi": "phá vỡ sự ngại ngùng ban đầu",
                "example_sentence": "Alex told a joke to break the ice.",
            }
        ],
        "grammar": [
            {
                "point": "Present perfect",
                "structure": "have/has + past participle",
                "explanation_en": "Links a past action to the present.",
                "explanation_vi": "Liên kết hành động quá khứ với hiện tại.",
                "examples": ["We have learned a lot.", "She has finished."],
            }
        ],
        "questions": [
            {
                "question": "Who explained the nuance?",
                "options": ["Alex", "Linh"],
                "correct_answer": "Linh",
                "explanation": "The transcript attributes the explanation to Linh.",
            }
        ],
    }


def test_build_transcript_without_learning_content_includes_clear_notice():
    script_lines = [
        {"speaker_id": "speaker-alex", "text": "Welcome to the lesson."},
        {"speaker_id": "unknown-speaker", "text": "Fallback names stay honest."},
    ]

    text = youtube_service._build_transcript_and_learning_text(
        _project_with_speakers(), script_lines, None
    )

    assert "=== FULL TRANSCRIPT ===" in text
    assert "Alex: Welcome to the lesson." in text
    assert "unknown-speaker: Fallback names stay honest." in text
    assert "Learning Content was not generated for this project." in text
    assert "=== VOCABULARY ===" not in text


def test_build_transcript_with_full_learning_content_formats_every_section():
    script_lines = [
        {"speaker_id": "speaker-alex", "text": "First line."},
        {"speaker_id": "speaker-linh", "text": "Second line."},
    ]

    text = youtube_service._build_transcript_and_learning_text(
        _project_with_speakers(), script_lines, _full_learning_content()
    )

    assert text.index("Alex: First line.") < text.index("Linh: Second line.")
    assert "=== VOCABULARY ===" in text
    assert "nuance (noun) — /ˈnjuːɑːns/ — a subtle difference" in text
    assert "=== IDIOMS & COLLOCATIONS ===" in text
    assert "break the ice — make people feel more comfortable" in text
    assert "=== GRAMMAR POINTS ===" in text
    assert "Examples: We have learned a lot. | She has finished." in text
    assert "=== COMPREHENSION QUESTIONS ===" in text
    assert "Options: Alex | Linh — Correct answer: Linh" in text


def test_build_transcript_with_generated_empty_pack_keeps_all_section_headings():
    empty_pack = {"vocabulary": [], "idioms": [], "grammar": [], "questions": []}

    text = youtube_service._build_transcript_and_learning_text(
        _project_with_speakers(),
        [{"speaker_id": "speaker-alex", "text": "Nothing was extracted."}],
        empty_pack,
    )

    assert "Learning Content was not generated" not in text
    assert "=== VOCABULARY ===" in text
    assert "=== IDIOMS & COLLOCATIONS ===" in text
    assert "=== GRAMMAR POINTS ===" in text
    assert "=== COMPREHENSION QUESTIONS ===" in text
    assert text.count("No items.") == 4


def test_build_transcript_preserves_unicode_special_characters_and_long_text():
    long_text = ("Tiếng Việt có dấu 🚀 — “trích dẫn”, ký hiệu <>& và café. " * 200).strip()
    learning_content = _full_learning_content()
    learning_content["vocabulary"][0]["definition_vi"] = long_text

    text = youtube_service._build_transcript_and_learning_text(
        _project_with_speakers(),
        [{"speaker_id": "speaker-linh", "text": long_text}],
        learning_content,
    )

    assert f"Linh: {long_text}" in text
    assert long_text in text
    assert text.encode("utf-8").decode("utf-8") == text


# --- build_export_zip ---


def test_build_export_zip_contains_all_five_files(tmp_path):
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"fake-mp4-bytes")
    srt_path = tmp_path / "subtitles.srt"
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello!\n", encoding="utf-8")
    thumbnail_path = tmp_path / "thumb.png"
    thumbnail_path.write_bytes(b"fake-png-bytes")

    package = {
        **VALID_PACKAGE,
        "chapters_text": "00:00 Introduction",
        "chapters_estimated": False,
    }
    video_job = {"mp4_path": str(video_path), "srt_path": str(srt_path)}
    thumbnail_row = {"image_path_16x9": str(thumbnail_path)}

    project = _project_with_speakers()
    script_lines = [
        {"speaker_id": "speaker-alex", "text": "Xin chào! 👋"},
        {"speaker_id": "speaker-linh", "text": "Hôm nay chúng ta học tiếng Anh."},
    ]
    zip_bytes = youtube_service.build_export_zip(
        package,
        video_job,
        thumbnail_row,
        project,
        script_lines,
        _full_learning_content(),
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        names = set(archive.namelist())
        assert names == {
            "video.mp4",
            "subtitles.srt",
            "thumbnail.png",
            "metadata.txt",
            "transcript_and_vocabulary.txt",
        }
        assert archive.read("video.mp4") == b"fake-mp4-bytes"
        metadata = archive.read("metadata.txt").decode("utf-8")
        assert "TITLES" in metadata
        assert VALID_PACKAGE["description"] in metadata
        assert "Measured (from real audio)" in metadata
        transcript = archive.read("transcript_and_vocabulary.txt").decode("utf-8")
        assert "Alex: Xin chào! 👋" in transcript
        assert "Linh: Hôm nay chúng ta học tiếng Anh." in transcript
        assert "một sắc thái khác biệt tinh tế" in transcript
