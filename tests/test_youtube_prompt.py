"""Tests for the YouTube package Jinja2 prompt (Task 1.9, Sub-task 1.9a)."""

import pytest

from app.core.exceptions import ValidationError
from app.core.prompt_loader import render_youtube_prompt


async def test_render_youtube_prompt_injects_all_variables():
    prompt = await render_youtube_prompt(
        project_name="Future English",
        topic="Remote work culture",
        genre="interview",
        cefr_level="B1",
        transcript_text="Welcome to the show!\nThanks for having me.",
    )

    assert "Future English" in prompt
    assert "Remote work culture" in prompt
    assert "interview" in prompt
    assert "B1" in prompt
    assert "Welcome to the show!" in prompt
    assert "click_worthy" in prompt
    assert "educational" in prompt
    assert "seo" in prompt


async def test_render_youtube_prompt_rejects_unknown_genre():
    with pytest.raises(ValidationError, match="genre"):
        await render_youtube_prompt(
            project_name="Test",
            topic="Test",
            genre="not-a-real-genre",
            cefr_level="B1",
            transcript_text="text",
        )


async def test_render_youtube_prompt_rejects_unknown_cefr_level():
    with pytest.raises(ValidationError, match="CEFR level"):
        await render_youtube_prompt(
            project_name="Test",
            topic="Test",
            genre="interview",
            cefr_level="Z9",
            transcript_text="text",
        )


async def test_render_youtube_prompt_different_cefr_and_genre():
    prompt = await render_youtube_prompt(
        project_name="Climate Show",
        topic="Climate change",
        genre="debate",
        cefr_level="C1",
        transcript_text="Some transcript text.",
    )

    assert "Climate change" in prompt
    assert "debate" in prompt
    assert "C1" in prompt
