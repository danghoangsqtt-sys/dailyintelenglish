"""Renderer, Gemini-contract, cleanup, and persistence-unit tests for ThumbnailService."""

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from backend.core.config import settings
from backend.core.constants import (
    THUMBNAIL_HEIGHT_16X9, THUMBNAIL_HEIGHT_9X16, THUMBNAIL_TEMPLATE_IDS, THUMBNAIL_WIDTH_16X9, THUMBNAIL_WIDTH_9X16,
)
from backend.core.exceptions import ConflictError, ThumbnailGenerationError
from backend.schemas.thumbnail import ThumbnailEditRequest, ThumbnailSuggestion
from backend.media import thumbnail_service
from backend.ai.llm.contracts import AIMode, GenerationResult
from backend.ai.llm.fake_provider import FakeProvider
from backend.ai.llm.router import AIRouter

PROJECT = {
    "id": "project-1",
    "name": "Future English",
    "topic": "How AI changes careers",
    "genre": "debate",
    "cefr_level": "B2",
}


# Task 36.3: what `thumbnail_compose.composition_inputs` gathers; no picture and no character -> the brand gradient.
COMPOSITION = {"backgrounds": [], "characters": [], "cefr": "B2", "episode": None, "outside_image": None}


def suggestion(index: int = 0) -> ThumbnailSuggestion:
    """Build one valid, visibly distinct thumbnail suggestion."""
    palettes = [
        ("#111827", "#60A5FA", "#F59E0B", "#FFFFFF"),
        ("#3B0764", "#C084FC", "#22D3EE", "#FFFFFF"),
        ("#052E16", "#4ADE80", "#FDE047", "#FFFFFF"),
    ]
    primary, secondary, accent, text = palettes[index % len(palettes)]
    return ThumbnailSuggestion.model_validate(
        {
            "headline": f"AI Career Shift {index + 1}",
            "supporting_text": "Build practical English for tomorrow",
            "topic_keywords": ["AI", f"career-{index + 1}"],
            "palette": {
                "primary": primary,
                "secondary": secondary,
                "accent": accent,
                "text": text,
            },
        }
    )


def suggestion_json(count: int = 3) -> str:
    """Serialize a valid Gemini suggestion pack fixture."""
    return json.dumps({"variants": [suggestion(index).model_dump() for index in range(count)]})


def persisted_row(record: dict) -> dict:
    """Adapt one render record to the shape loaded from the thumbnails table."""
    return {
        "id": record["id"],
        "project_id": record["project_id"],
        "template_name": record["template_name"],
        "variant_index": record["variant_index"],
        "image_path_16x9": record["assets"]["16x9"]["png"],
        "image_path_9x16": record["assets"]["9x16"]["png"],
        "is_selected": 1,
        "created_at": "2026-09-12T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_the_two_thumbnail_kinds_are_listed_and_outside_ai_waits_for_its_picture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 36.3/36.4 (D92): `composed` and `outside_ai` replace the five Pillow templates and ai_scene."""
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    templates = await thumbnail_service.list_templates("project-1")
    assert [template["id"] for template in templates] == list(THUMBNAIL_TEMPLATE_IDS) == ["composed", "outside_ai", "qwen_scene"]
    assert [template["available"] for template in templates] == [True, False, False]
    assert templates[1]["preview_url"] == "/static/thumbnail_templates/outside_ai.png"
    picture = thumbnail_service.outside_image_path("project-1")
    picture.parent.mkdir(parents=True)
    Image.new("RGB", (1280, 720), "#336699").save(picture)
    templates = await thumbnail_service.list_templates("project-1")
    assert templates[1]["available"] and templates[1]["preview_url"].endswith("/thumbnails/outside-image")
    for template_id in ("composed", "outside_ai"):
        assert (Path(thumbnail_service.PROJECT_ROOT) / "frontend" / "static" / "thumbnail_templates" /
                f"{template_id}.png").is_file()


@pytest.mark.asyncio
@pytest.mark.parametrize("template_name", ["composed"])
async def test_each_template_renders_png_and_jpg_at_both_aspects(
    template_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    template = await thumbnail_service.load_template(template_name)

    records = await thumbnail_service.render_batch("project-1", template, [suggestion()], COMPOSITION)

    assert len(records) == 1
    expected_sizes = {
        "16x9": (THUMBNAIL_WIDTH_16X9, THUMBNAIL_HEIGHT_16X9),
        "9x16": (THUMBNAIL_WIDTH_9X16, THUMBNAIL_HEIGHT_9X16),
    }
    for aspect, expected_size in expected_sizes.items():
        for image_format in ("png", "jpg"):
            path = Path(records[0]["assets"][aspect][image_format])
            assert path.is_file()
            with Image.open(path) as image:
                assert image.size == expected_size
                assert image.format == image_format.upper().replace("JPG", "JPEG")
                assert image.mode == "RGB"


@pytest.mark.asyncio
async def test_ab_variants_have_distinct_rendered_pixels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    template = await thumbnail_service.load_template("composed")

    records = await thumbnail_service.render_batch(
        "project-1", template, [suggestion(index) for index in range(3)], COMPOSITION
    )

    hashes = {
        hashlib.sha256(Path(record["assets"]["16x9"]["png"]).read_bytes()).hexdigest()
        for record in records
    }
    assert len(hashes) == 3
    assert [record["variant_index"] for record in records] == [0, 1, 2]
    assert {record["template_name"] for record in records} == {"composed"}


@pytest.mark.asyncio
async def test_render_failure_removes_every_partial_variant_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    template = await thumbnail_service.load_template("composed")
    real_render = thumbnail_service._render_image
    calls = 0

    def fail_after_first_image(*args: object, **kwargs: object) -> Image.Image:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise OSError("simulated render failure")
        return real_render(*args, **kwargs)

    monkeypatch.setattr(thumbnail_service, "_render_image", fail_after_first_image)

    with pytest.raises(ThumbnailGenerationError, match="simulated render failure"):
        await thumbnail_service.render_batch("project-1", template, [suggestion()], COMPOSITION)

    project_dir = tmp_path / "thumbnails" / "project-1"
    assert list(project_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_edit_render_stages_new_revision_and_preserves_noneditable_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    template = await thumbnail_service.load_template("composed")
    original = (await thumbnail_service.render_batch("project-1", template, [suggestion()], COMPOSITION))[0]
    row = persisted_row(original)
    edit = ThumbnailEditRequest.model_validate(
        {
            "revision": original["revision"],
            "headline": "A Better Headline",
            "palette": {
                "primary": "#201040",
                "secondary": "#8050E0",
                "accent": "#00FFAA",
                "text": "#FFFFFF",
            },
        }
    )

    edited = await thumbnail_service.render_edited_thumbnail(row, edit)

    assert edited["id"] == original["id"]
    assert edited["variant_index"] == original["variant_index"]
    assert edited["revision"] != original["revision"]
    assert edited["suggestion"]["headline"] == "A Better Headline"
    assert edited["suggestion"]["supporting_text"] == original["suggestion"]["supporting_text"]
    assert edited["suggestion"]["topic_keywords"] == original["suggestion"]["topic_keywords"]
    assert Path(edited["assets"]["16x9"]["png"]).is_file()
    assert Path(original["assets"]["16x9"]["png"]).is_file()


@pytest.mark.asyncio
async def test_edit_render_rejects_stale_revision_before_creating_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    template = await thumbnail_service.load_template("composed")
    original = (await thumbnail_service.render_batch("project-1", template, [suggestion()], COMPOSITION))[0]
    row = persisted_row(original)
    edit = ThumbnailEditRequest.model_validate(
        {
            "revision": "00000000-0000-0000-0000-000000000001",
            "headline": "Stale Headline",
            "palette": original["suggestion"]["palette"],
        }
    )

    with pytest.raises(ConflictError):
        await thumbnail_service.render_edited_thumbnail(row, edit)

    project_dir = tmp_path / "thumbnails" / "project-1"
    assert [path.name for path in project_dir.iterdir()] == [original["revision"]]


# Note: the responseJsonSchema-not-responseSchema wire-payload regression (BUG-011)
# was Gemini-specific and no longer applies -- Phase 18/Task 18.2 deleted
# GeminiProvider (D23) in favour of OpenAICompatProvider, which never sends
# `response_format`/a JSON schema at all (see tests/test_openai_compat_provider.py,
# Task 18.1, for that provider's own request-shape coverage).


def _suggestion_result(pack_json: str) -> GenerationResult:
    return GenerationResult(
        text=pack_json,
        provider="fake-provider",
        model="fake-model",
        latency_ms=1.0,
        attempt=1,
        prompt_hash="abc123",
    )


def _gateway_router(mode: AIMode, gemini_outcomes: list, local_outcomes: list | None = None) -> AIRouter:
    """`gemini_outcomes`/`local_outcomes` are historical parameter names
    (predating Phase 18's cloud-first router roles) for what's now
    `primary`/`fallback` -- every call site here uses `AIMode.CLOUD`
    (single-provider, mechanical rename from `AIMode.GEMINI`)."""
    gemini = FakeProvider("fake-gemini", gemini_outcomes)
    local = FakeProvider("fake-ollama", local_outcomes or [])
    return AIRouter(primary=gemini, fallback=local, mode=mode)


@pytest.mark.asyncio
async def test_generate_suggestions_applies_pydantic_validation_and_exact_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    template = await thumbnail_service.load_template("composed")
    router = _gateway_router(AIMode.CLOUD, [_suggestion_result(suggestion_json(3))])

    pack = await thumbnail_service.generate_suggestions(PROJECT, template, 3, router=router)

    assert len(pack.variants) == 3


@pytest.mark.asyncio
async def test_generate_suggestions_rejects_wrong_count_and_invalid_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    template = await thumbnail_service.load_template("composed")

    router = _gateway_router(AIMode.CLOUD, [_suggestion_result(suggestion_json(3))])
    with pytest.raises(ThumbnailGenerationError, match="expected exactly 4"):
        await thumbnail_service.generate_suggestions(PROJECT, template, 4, router=router)

    payload = json.loads(suggestion_json(3))
    payload["variants"][0]["palette"]["primary"] = "not-a-color"
    router = _gateway_router(AIMode.CLOUD, [_suggestion_result(json.dumps(payload))])
    with pytest.raises(ThumbnailGenerationError, match="schema validation"):
        await thumbnail_service.generate_suggestions(PROJECT, template, 3, router=router)


@pytest.mark.asyncio
async def test_generate_suggestions_runs_end_to_end_under_ai_mode_local() -> None:
    """Task 14.7 (Amendment E): local-only is now the default -- proves
    generate_suggestions completes via the local (Ollama) route with no
    Gemini key configured, matching the same
    _gateway_router(AIMode.LOCAL, ...) pattern already used for script/
    learning/YouTube generation. Not a claim about real Ollama structured-
    output quality for this schema (measured for real in Task 14.9)."""
    template = await thumbnail_service.load_template("composed")
    router = _gateway_router(AIMode.LOCAL, gemini_outcomes=[], local_outcomes=[_suggestion_result(suggestion_json(3))])

    pack = await thumbnail_service.generate_suggestions(PROJECT, template, 3, router=router)

    assert len(pack.variants) == 3


def test_renamed_ai_fields_are_mapped_onto_the_schema() -> None:
    """Task 36.3 real-AI finding: `supporting_line`, `keywords`, `colors` / flat `*_color`, hex without `#`."""
    raw = {"variants": [
        {"headline": "Morning Talk", "supporting_line": "B1 English", "keywords": ["routine"],
         "colors": {"primary": "2E7D32", "secondary": "1B5E20", "accent": "#FFD23F", "text": "FFFFFF"}},
        {"headline": "Coffee Chat", "supporting_text": "", "topic_keywords": ["coffee"], "primary_color": "EF6C00",
         "secondary_color": "E65100", "accent_color": "C6FF00", "text_color": "FAFAFA"},
        suggestion(2).model_dump(),  # an answer already in the schema's shape stays as it is
    ]}
    pack = thumbnail_service.ThumbnailSuggestionPack.model_validate(thumbnail_service.normalize_suggestion_pack(raw))
    assert pack.variants[0].supporting_text == "B1 English" and pack.variants[0].palette.primary == "#2E7D32"
    assert pack.variants[1].topic_keywords == ["coffee"] and pack.variants[1].palette.text == "#FAFAFA"
    assert thumbnail_service.normalize_suggestion_pack("not a pack") == "not a pack"
