"""Loads and renders script-generation prompt templates (Jinja2).

Templates live in `prompts/script/`: one Jinja2 base template
(`script_base.txt`) composed at render time with a plain-text genre
instruction block (`{genre}.txt`) and a plain-text CEFR constraint block
(`cefr_{level}.txt`). The genre/CEFR blocks are not templates themselves —
they are injected into the base template as rendered string variables.

The public API is async: file reads and the Jinja2 render all block the
event loop, so every blocking call is pushed to a worker thread via
`asyncio.to_thread` (AR-02/AR-05) rather than exposed as sync functions
that a future async ScriptService could accidentally call directly.
"""

import asyncio
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from app.core.constants import CEFR_LEVELS, GENRES
from app.core.exceptions import ValidationError

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"
SCRIPT_PROMPTS_DIR = PROMPTS_DIR / "script"

_env = Environment(
    loader=FileSystemLoader(str(SCRIPT_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _read_genre_block_sync(genre: str) -> str:
    """Blocking: validate `genre` against GENRES, then read its instruction block.

    Validating membership before touching the filesystem means an
    unrecognized value (including anything path-traversal-shaped) is
    rejected before a Path is ever built from it.
    """
    if genre not in GENRES:
        raise ValidationError(f"No script prompt block for genre: {genre!r}")
    return (SCRIPT_PROMPTS_DIR / f"{genre}.txt").read_text(encoding="utf-8")


def _read_cefr_block_sync(cefr_level: str) -> str:
    """Blocking: validate `cefr_level` (case-insensitively) against CEFR_LEVELS, then read its block."""
    normalized = cefr_level.upper()
    if normalized not in CEFR_LEVELS:
        raise ValidationError(f"No script prompt block for CEFR level: {cefr_level!r}")
    return (SCRIPT_PROMPTS_DIR / f"cefr_{normalized.lower()}.txt").read_text(encoding="utf-8")


def _render_script_prompt_sync(*, genre: str, cefr_level: str, **context: object) -> str:
    """Blocking: compose and render the full prompt. Runs entirely in a worker thread."""
    genre_instructions = _read_genre_block_sync(genre)
    cefr_constraints = _read_cefr_block_sync(cefr_level)
    try:
        template = _env.get_template("script_base.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc

    return template.render(
        genre=genre,
        cefr_level=cefr_level,
        genre_instructions=genre_instructions,
        cefr_constraints=cefr_constraints,
        **context,
    )


async def load_genre_block(genre: str) -> str:
    """Read the raw genre-specific instruction block.

    Args:
        genre: One of the genre values in app.core.constants.GENRES.

    Returns:
        The block's plain text content.

    Raises:
        ValidationError: If `genre` is not a recognized GENRES value.
    """
    return await asyncio.to_thread(_read_genre_block_sync, genre)


async def load_cefr_block(cefr_level: str) -> str:
    """Read the raw CEFR constraint block.

    Args:
        cefr_level: One of the CEFR level values in app.core.constants.CEFR_LEVELS.

    Returns:
        The block's plain text content.

    Raises:
        ValidationError: If `cefr_level` is not a recognized CEFR_LEVELS value.
    """
    return await asyncio.to_thread(_read_cefr_block_sync, cefr_level)


async def render_script_prompt(*, genre: str, cefr_level: str, **context: object) -> str:
    """Render the full script-generation prompt for one genre x CEFR combination.

    Composes `script_base.txt` with the genre and CEFR instruction blocks
    injected as `genre_instructions` / `cefr_constraints`, plus whatever
    other template variables are passed in `context` (topic, duration_minutes,
    num_speakers, accent, speakers, language_features, ...). `speakers` items
    must each carry an `id` (the speaker's UUID) — the template renders it as
    the value the LLM must echo back in `speaker_id`, since display names are
    not guaranteed unique.

    Args:
        genre: One of app.core.constants.GENRES.
        cefr_level: One of app.core.constants.CEFR_LEVELS.
        **context: Remaining variables referenced by script_base.txt.

    Returns:
        The fully rendered prompt text.

    Raises:
        ValidationError: If the genre or CEFR value is not recognized.
        jinja2.UndefinedError: If script_base.txt references a variable that
            was not supplied in `context`.
    """
    return await asyncio.to_thread(_render_script_prompt_sync, genre=genre, cefr_level=cefr_level, **context)
