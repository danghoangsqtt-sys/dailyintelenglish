"""Renderer, Gemini-contract, cleanup, and persistence-unit tests for ThumbnailService."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.core.config import settings
from app.core.constants import (
    THUMBNAIL_HEIGHT_16X9,
    THUMBNAIL_HEIGHT_9X16,
    THUMBNAIL_TEMPLATE_IDS,
    THUMBNAIL_WIDTH_16X9,
    THUMBNAIL_WIDTH_9X16,
)
from app.core.exceptions import ThumbnailGenerationError
from app.models.thumbnail import ThumbnailSuggestion, ThumbnailSuggestionPack
from app.services import thumbnail_service

PROJECT = {
    "id": "project-1",
    "name": "Future English",
    "topic": "How AI changes careers",
    "genre": "debate",
    "cefr_level": "B2",
}


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


@pytest.mark.asyncio
async def test_list_templates_validates_all_five_assets() -> None:
    templates = await thumbnail_service.list_templates()

    assert [template["id"] for template in templates] == list(THUMBNAIL_TEMPLATE_IDS)
    assert {template["category"] for template in templates} == {
        "minimal",
        "bold",
        "split",
        "dark",
        "educational",
    }
    assert all(template["preview_url"].endswith(f"{template['id']}.png") for template in templates)


@pytest.mark.asyncio
@pytest.mark.parametrize("template_name", THUMBNAIL_TEMPLATE_IDS)
async def test_each_template_renders_png_and_jpg_at_both_aspects(
    template_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    template = await thumbnail_service.load_template(template_name)

    records = await thumbnail_service.render_batch("project-1", template, [suggestion()])

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
    template = await thumbnail_service.load_template("gradient_bold")

    records = await thumbnail_service.render_batch(
        "project-1", template, [suggestion(index) for index in range(3)]
    )

    hashes = {
        hashlib.sha256(Path(record["assets"]["16x9"]["png"]).read_bytes()).hexdigest()
        for record in records
    }
    assert len(hashes) == 3
    assert [record["variant_index"] for record in records] == [0, 1, 2]
    assert {record["template_name"] for record in records} == {"gradient_bold"}


@pytest.mark.asyncio
async def test_render_failure_removes_every_partial_variant_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    template = await thumbnail_service.load_template("minimal_clean")
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
        await thumbnail_service.render_batch("project-1", template, [suggestion()])

    project_dir = tmp_path / "thumbnails" / "project-1"
    assert list(project_dir.iterdir()) == []


@pytest.mark.asyncio
async def test_gemini_network_payload_uses_response_json_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            captured["client_kwargs"] = kwargs

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, **kwargs: object) -> httpx.Response:
            captured["url"] = url
            captured.update(kwargs)
            return httpx.Response(200, json={})

    monkeypatch.setattr(thumbnail_service.httpx, "AsyncClient", FakeClient)
    schema = ThumbnailSuggestionPack.model_json_schema()

    await thumbnail_service._call_gemini("safe prompt", schema)

    generation_config = captured["json"]["generationConfig"]
    assert generation_config["responseJsonSchema"] == schema
    assert "responseSchema" not in generation_config
    assert generation_config["responseMimeType"] == "application/json"


@pytest.mark.asyncio
async def test_generate_suggestions_applies_pydantic_validation_and_exact_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    template = await thumbnail_service.load_template("modern_split")

    async def fake_generate(prompt: str, schema: dict) -> str:
        assert "exactly 3 distinct variants" in prompt
        assert schema == ThumbnailSuggestionPack.model_json_schema()
        return suggestion_json(3)

    monkeypatch.setattr(thumbnail_service, "_generate_with_retry", fake_generate)

    pack = await thumbnail_service.generate_suggestions(PROJECT, template, 3)

    assert len(pack.variants) == 3


@pytest.mark.asyncio
async def test_generate_suggestions_rejects_wrong_count_and_invalid_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    template = await thumbnail_service.load_template("modern_split")

    async def wrong_count(prompt: str, schema: dict) -> str:
        return suggestion_json(3)

    monkeypatch.setattr(thumbnail_service, "_generate_with_retry", wrong_count)
    with pytest.raises(ThumbnailGenerationError, match="expected exactly 4"):
        await thumbnail_service.generate_suggestions(PROJECT, template, 4)

    async def invalid_schema(prompt: str, schema: dict) -> str:
        payload = json.loads(suggestion_json(3))
        payload["variants"][0]["palette"]["primary"] = "not-a-color"
        return json.dumps(payload)

    monkeypatch.setattr(thumbnail_service, "_generate_with_retry", invalid_schema)
    with pytest.raises(ThumbnailGenerationError, match="schema validation"):
        await thumbnail_service.generate_suggestions(PROJECT, template, 3)

