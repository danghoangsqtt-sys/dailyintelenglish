"""Prompt-loader tests for thumbnail text/palette suggestion generation."""

import pytest

from app.core.exceptions import ValidationError
from app.core.prompt_loader import render_thumbnail_prompt


@pytest.mark.asyncio
async def test_thumbnail_prompt_renders_all_project_and_template_context() -> None:
    prompt = await render_thumbnail_prompt(
        project_name="Future English",
        topic="How AI changes careers",
        genre="debate",
        cefr_level="B2",
        template_name="modern_split",
        template_description="Balanced split layout",
        variant_count=4,
    )

    assert "Future English" in prompt
    assert "How AI changes careers" in prompt
    assert "debate" in prompt
    assert "B2" in prompt
    assert "modern_split" in prompt
    assert "exactly 4 distinct variants" in prompt


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("template_name", "../escape"),
        ("genre", "unknown"),
        ("cefr_level", "Z9"),
        ("variant_count", 2),
        ("variant_count", 6),
    ],
)
async def test_thumbnail_prompt_rejects_unapproved_context(field: str, value: object) -> None:
    context = {
        "project_name": "Future English",
        "topic": "How AI changes careers",
        "genre": "debate",
        "cefr_level": "B2",
        "template_name": "modern_split",
        "template_description": "Balanced split layout",
        "variant_count": 3,
    }
    context[field] = value

    with pytest.raises(ValidationError):
        await render_thumbnail_prompt(**context)

