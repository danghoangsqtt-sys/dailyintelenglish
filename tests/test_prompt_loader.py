"""Tests for the script-prompt Jinja2 loader (ROADMAP Task 1.4 — prompt templates)."""

import jinja2
import pytest

from app.core.constants import CEFR_LEVELS, GENRES
from app.core.exceptions import ValidationError
from app.core.prompt_loader import load_cefr_block, load_genre_block, render_script_prompt

SAMPLE_CONTEXT = {
    "topic": "How AI assistants are changing daily routines",
    "duration_minutes": 10,
    "num_speakers": 2,
    "accent": "american",
    "speakers": [
        {"id": "11111111-1111-1111-1111-111111111111", "name": "Alex", "gender": "male", "accent": "american"},
        {"id": "22222222-2222-2222-2222-222222222222", "name": "Sam", "gender": "female", "accent": "american"},
    ],
    "language_features": {
        "collocation": True,
        "idiom": True,
        "slang": False,
        "local_expressions": False,
        "phrasal_verbs": True,
        "business_register": False,
    },
}


@pytest.mark.parametrize("genre", GENRES)
async def test_all_genre_blocks_load(genre):
    text = await load_genre_block(genre)
    assert text.strip()
    assert "{{" not in text and "}}" not in text


@pytest.mark.parametrize("cefr_level", CEFR_LEVELS)
async def test_all_cefr_blocks_load(cefr_level):
    text = await load_cefr_block(cefr_level)
    assert text.strip()
    assert "{{" not in text and "}}" not in text


async def test_cefr_block_load_is_case_insensitive():
    assert await load_cefr_block("b1") == await load_cefr_block("B1")


async def test_load_genre_block_missing_raises_validation_error():
    with pytest.raises(ValidationError):
        await load_genre_block("not_a_real_genre")


async def test_load_cefr_block_missing_raises_validation_error():
    with pytest.raises(ValidationError):
        await load_cefr_block("Z9")


@pytest.mark.parametrize(
    "bad_genre",
    ["../script_base", "../../etc/passwd", "..\\..\\windows\\system32", "script_base", "."],
)
async def test_load_genre_block_rejects_path_traversal_before_filesystem_access(bad_genre):
    with pytest.raises(ValidationError):
        await load_genre_block(bad_genre)


@pytest.mark.parametrize("bad_cefr", ["../cefr_a1", "../../etc/passwd", "a1; rm -rf", "b1/../c2"])
async def test_load_cefr_block_rejects_path_traversal_before_filesystem_access(bad_cefr):
    with pytest.raises(ValidationError):
        await load_cefr_block(bad_cefr)


async def test_render_script_prompt_injects_variables():
    prompt = await render_script_prompt(genre="interview", cefr_level="B1", **SAMPLE_CONTEXT)

    assert "How AI assistants are changing daily routines" in prompt
    assert "interview" in prompt
    assert "B1" in prompt
    assert "10 minutes" in prompt
    assert "id: 11111111-1111-1111-1111-111111111111 | name: Alex" in prompt
    assert "id: 22222222-2222-2222-2222-222222222222 | name: Sam" in prompt
    assert "collocation" in prompt
    assert "phrasal verbs" in prompt
    features_section = prompt.split("Language Features to Target")[1].split("Script Rules")[0]
    assert "slang" not in features_section
    assert "{{" not in prompt and "}}" not in prompt


async def test_render_script_prompt_includes_genre_and_cefr_blocks():
    prompt = await render_script_prompt(genre="debate", cefr_level="C1", **SAMPLE_CONTEXT)

    assert await load_genre_block("debate") in prompt
    assert await load_cefr_block("C1") in prompt


async def test_render_script_prompt_with_no_language_features_shows_fallback():
    context = {**SAMPLE_CONTEXT, "language_features": dict.fromkeys(SAMPLE_CONTEXT["language_features"], False)}

    prompt = await render_script_prompt(genre="small_talk", cefr_level="A1", **context)

    assert "None requested" in prompt


async def test_render_script_prompt_missing_variable_raises():
    incomplete_context = {k: v for k, v in SAMPLE_CONTEXT.items() if k != "topic"}

    with pytest.raises(jinja2.UndefinedError):
        await render_script_prompt(genre="news", cefr_level="B2", **incomplete_context)


async def test_render_script_prompt_unknown_genre_raises_validation_error():
    with pytest.raises(ValidationError):
        await render_script_prompt(genre="not_a_real_genre", cefr_level="B1", **SAMPLE_CONTEXT)


async def test_render_script_prompt_unknown_cefr_raises_validation_error():
    with pytest.raises(ValidationError):
        await render_script_prompt(genre="news", cefr_level="Z9", **SAMPLE_CONTEXT)


# --- Speaker identity: UUID, not name ---


async def test_speaker_id_output_instruction_requires_uuid_not_name():
    prompt = await render_script_prompt(genre="interview", cefr_level="B1", **SAMPLE_CONTEXT)

    assert "the exact `id` (UUID) of the speaker" in prompt
    assert "never an invented id" in prompt


async def test_duplicate_speaker_names_are_still_distinguished_by_uuid():
    context = {
        **SAMPLE_CONTEXT,
        "speakers": [
            {"id": "11111111-1111-1111-1111-111111111111", "name": "Alex", "gender": "male", "accent": "american"},
            {"id": "33333333-3333-3333-3333-333333333333", "name": "Alex", "gender": "female", "accent": "british"},
        ],
    }

    prompt = await render_script_prompt(genre="debate", cefr_level="B1", **context)

    assert "id: 11111111-1111-1111-1111-111111111111 | name: Alex" in prompt
    assert "id: 33333333-3333-3333-3333-333333333333 | name: Alex" in prompt
    assert "always tell them apart by `id`, never by name alone" in prompt


# --- Solo mode ---


async def test_solo_mode_omits_balance_and_monologue_rules():
    context = {
        **SAMPLE_CONTEXT,
        "num_speakers": 1,
        "speakers": [{"id": "11111111-1111-1111-1111-111111111111", "name": "Alex", "gender": "male", "accent": "american"}],
    }

    prompt = await render_script_prompt(genre="interview", cefr_level="B1", **context)

    assert "Speaker balance" not in prompt
    assert "No monologues" not in prompt
    assert "Solo format" in prompt


async def test_solo_mode_overrides_genre_turn_pattern():
    context = {
        **SAMPLE_CONTEXT,
        "num_speakers": 1,
        "speakers": [{"id": "11111111-1111-1111-1111-111111111111", "name": "Alex", "gender": "male", "accent": "american"}],
    }

    prompt = await render_script_prompt(genre="debate", cefr_level="B1", **context)

    assert "Solo override" in prompt
    assert "Ignore any turn-taking" in prompt


async def test_multi_speaker_mode_keeps_balance_and_monologue_rules():
    prompt = await render_script_prompt(genre="interview", cefr_level="B1", **SAMPLE_CONTEXT)

    assert "Speaker balance" in prompt
    assert "No monologues" in prompt
    assert "Solo override" not in prompt


# --- CEFR ceiling vs. language-feature toggle precedence ---


async def test_cefr_blocks_no_longer_mandate_features_unconditionally():
    for level in CEFR_LEVELS:
        text = await load_cefr_block(level)
        assert "are expected" not in text
        assert "is encouraged" not in text


async def test_precedence_rule_present_and_toggle_off_excludes_feature():
    context = {**SAMPLE_CONTEXT, "language_features": {**SAMPLE_CONTEXT["language_features"], "idiom": False}}

    prompt = await render_script_prompt(genre="debate", cefr_level="C2", **context)

    assert "Precedence: CEFR Constraints vs. Language Feature Toggles" in prompt
    features_section = prompt.split("Language Features to Target")[1].split("Script Rules")[0]
    assert "idiom" not in features_section


@pytest.mark.parametrize("genre", GENRES)
@pytest.mark.parametrize("cefr_level", CEFR_LEVELS)
async def test_every_genre_cefr_combination_renders_cleanly(genre, cefr_level):
    prompt = await render_script_prompt(genre=genre, cefr_level=cefr_level, **SAMPLE_CONTEXT)

    assert prompt.strip()
    assert "{{" not in prompt and "}}" not in prompt
    assert "Undefined" not in prompt


async def test_render_regenerate_line_prompt_renders_cleanly():
    from app.core.prompt_loader import render_regenerate_line_prompt

    prompt = await render_regenerate_line_prompt(
        genre="interview",
        cefr_level="B1",
        topic="Remote work culture",
        speaker={"name": "Alex", "gender": "male", "accent": "american"},
        current_text="I work remotely.",
        line_id="line-123",
        speaker_id="speaker-456",
    )

    assert prompt.strip()
    assert "{{" not in prompt and "}}" not in prompt
    assert "Alex" in prompt
    assert "I work remotely." in prompt
    assert "line-123" in prompt
    assert "speaker-456" in prompt
