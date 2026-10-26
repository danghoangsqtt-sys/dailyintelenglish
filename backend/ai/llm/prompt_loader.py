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

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

from backend.core.constants import (
    CEFR_LEVELS, GENRES, THUMBNAIL_MAX_VARIANTS, THUMBNAIL_MIN_VARIANTS, THUMBNAIL_TEMPLATE_IDS,
)
from backend.core.exceptions import ValidationError
from backend.core import paths

PROMPTS_DIR = paths.PROMPTS_DIR
SCRIPT_PROMPTS_DIR = PROMPTS_DIR / "script"
LEARNING_PROMPTS_DIR = PROMPTS_DIR / "learning"
THUMBNAIL_PROMPTS_DIR = PROMPTS_DIR / "thumbnail"
YOUTUBE_PROMPTS_DIR = PROMPTS_DIR / "youtube"
STORYBOARD_PROMPTS_DIR = PROMPTS_DIR / "storyboard"
MUSIC_PROMPTS_DIR = PROMPTS_DIR / "music"
CHANNEL_PROMPTS_DIR = PROMPTS_DIR / "channel"
SOURCE_PROMPTS_DIR = PROMPTS_DIR / "source"

_env = Environment(
    loader=FileSystemLoader(str(SCRIPT_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


_learning_env = Environment(
    loader=FileSystemLoader(str(LEARNING_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

_thumbnail_env = Environment(
    loader=FileSystemLoader(str(THUMBNAIL_PROMPTS_DIR)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

_youtube_env = Environment(
    loader=FileSystemLoader(str(YOUTUBE_PROMPTS_DIR)),
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


def _render_presentation_block_sync(presentation_mode: str, explainer_structure: str | None, num_speakers: int,
                                    explainer_subject: str | None = None, explainer_style: str | None = None) -> str:
    """Validate explicit Solo configuration, then render its finite structure template."""
    if presentation_mode == "classic":
        # Phase 65 (ENH-047): a chat / would-you-rather Short gives the conversation its own format
        if explainer_style in ("chat", "wyr"):
            return _env.get_template("conversation_short.txt").render(explainer_style=explainer_style)
        return ""
    if presentation_mode != "solo_explainer":
        raise ValidationError("Unsupported presentation mode")
    if num_speakers != 1:
        raise ValidationError("Solo Explainer requires exactly one presenter")
    structure = explainer_structure or "why"
    if structure not in ("why", "how", "list"):
        raise ValidationError("Solo structure must be Why, How or List")
    try:
        template = _env.get_template("solo_explainer.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc
    subject = explainer_subject or "topic"
    if subject not in ("field", "product", "topic", "howto"):
        raise ValidationError("Solo subject must be field, product, topic or howto")
    return template.render(explainer_structure=structure, explainer_subject=subject, explainer_style=explainer_style or "")


async def load_presentation_block(presentation_mode: str = "classic", explainer_structure: str | None = None,
                                  num_speakers: int = 1, explainer_subject: str | None = None,
                                  explainer_style: str | None = None) -> str:
    """Load Solo instructions off the event loop; a classic project keeps its existing prompt rules.
    Phase 57 (ENH-039): `explainer_subject` adds what the presentation presents (field, product, topic, how-to)."""
    return await asyncio.to_thread(_render_presentation_block_sync, presentation_mode, explainer_structure, num_speakers,
                                   explainer_subject, explainer_style)


def _render_script_prompt_sync(*, genre: str, cefr_level: str, **context: object) -> str:
    """Blocking: compose and render the full prompt. Runs entirely in a worker thread."""
    genre_instructions = _read_genre_block_sync(genre)
    mode = context.pop("presentation_mode", "classic")
    structure = context.pop("explainer_structure", None)
    subject = context.pop("explainer_subject", None)
    style = context.pop("explainer_style", None)
    solo = _render_presentation_block_sync(mode, structure, int(context.get("num_speakers", 0)), subject, style)
    if solo and mode == "solo_explainer" and len(context.get("speakers", [])) != 1:
        raise ValidationError("Solo Explainer requires exactly one presenter")
    genre_instructions = solo or genre_instructions
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
        presentation_mode=mode,
        **context,
    )


async def load_genre_block(genre: str) -> str:
    """Read the raw genre-specific instruction block.

    Args:
        genre: One of the genre values in backend.core.constants.GENRES.

    Returns:
        The block's plain text content.

    Raises:
        ValidationError: If `genre` is not a recognized GENRES value.
    """
    return await asyncio.to_thread(_read_genre_block_sync, genre)


async def load_cefr_block(cefr_level: str) -> str:
    """Read the raw CEFR constraint block.

    Args:
        cefr_level: One of the CEFR level values in backend.core.constants.CEFR_LEVELS.

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
        genre: One of backend.core.constants.GENRES.
        cefr_level: One of backend.core.constants.CEFR_LEVELS.
        **context: Remaining variables referenced by script_base.txt.

    Returns:
        The fully rendered prompt text.

    Raises:
        ValidationError: If the genre or CEFR value is not recognized.
        jinja2.UndefinedError: If script_base.txt references a variable that
            was not supplied in `context`.
    """
    return await asyncio.to_thread(_render_script_prompt_sync, genre=genre, cefr_level=cefr_level, **context)


def _render_learning_prompt_sync(
    *, topic: str, cefr_level: str, genre: str, transcript_text: str, required_vocabulary: list[str] | None = None,
    audience_line: str | None = None,
) -> str:
    """Blocking: validate cefr_level/genre, then render learning_pack.txt. Runs in a worker thread."""
    if cefr_level.upper() not in CEFR_LEVELS:
        raise ValidationError(f"No learning prompt support for CEFR level: {cefr_level!r}")
    if genre not in GENRES:
        raise ValidationError(f"No learning prompt support for genre: {genre!r}")
    try:
        template = _learning_env.get_template("learning_pack.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc

    return template.render(
        topic=topic, cefr_level=cefr_level, genre=genre, transcript_text=transcript_text,
        required_vocabulary=required_vocabulary or [], **({"audience_line": audience_line} if audience_line else {}),
    )


async def render_learning_prompt(
    *, topic: str, cefr_level: str, genre: str, transcript_text: str, required_vocabulary: list[str] | None = None,
    audience_line: str | None = None,
) -> str:
    """Render the Learning Content generation prompt for one project's script.

    Args:
        topic: The project's topic.
        cefr_level: One of backend.core.constants.CEFR_LEVELS.
        genre: One of backend.core.constants.GENRES.
        transcript_text: The full script transcript (all lines joined) that
            the learning pack must be extracted from.
        required_vocabulary: Phase 57 (ENH-039) -- items of the owner's vocabulary list that the transcript uses;
            the pack must teach them first.

    Returns:
        The fully rendered prompt text.

    Raises:
        ValidationError: If the CEFR level or genre value is not recognized,
            or the template file is missing.
    """
    return await asyncio.to_thread(
        _render_learning_prompt_sync,
        topic=topic,
        cefr_level=cefr_level,
        genre=genre,
        transcript_text=transcript_text,
        required_vocabulary=required_vocabulary,
        audience_line=audience_line,
    )


def _render_thumbnail_prompt_sync(
    *,
    project_name: str,
    topic: str,
    genre: str,
    cefr_level: str,
    template_name: str,
    template_description: str,
    variant_count: int,
    audience_line: str | None = None,
) -> str:
    """Blocking: validate inputs and render the thumbnail suggestion prompt."""
    if genre not in GENRES:
        raise ValidationError(f"No thumbnail prompt support for genre: {genre!r}")
    if cefr_level.upper() not in CEFR_LEVELS:
        raise ValidationError(f"No thumbnail prompt support for CEFR level: {cefr_level!r}")
    if template_name not in THUMBNAIL_TEMPLATE_IDS:
        raise ValidationError(f"Unknown thumbnail template: {template_name!r}")
    if not THUMBNAIL_MIN_VARIANTS <= variant_count <= THUMBNAIL_MAX_VARIANTS:
        raise ValidationError(
            f"Thumbnail variant_count must be between {THUMBNAIL_MIN_VARIANTS} "
            f"and {THUMBNAIL_MAX_VARIANTS}"
        )
    try:
        template = _thumbnail_env.get_template("thumbnail_suggestions.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(
        project_name=project_name,
        topic=topic,
        genre=genre,
        cefr_level=cefr_level,
        template_name=template_name,
        template_description=template_description,
        variant_count=variant_count,
        **({"audience_line": audience_line} if audience_line else {}),
    )


async def render_thumbnail_prompt(
    *,
    project_name: str,
    topic: str,
    genre: str,
    cefr_level: str,
    template_name: str,
    template_description: str,
    variant_count: int,
    audience_line: str | None = None,
) -> str:
    """Render the Gemini text-suggestion prompt for a thumbnail generation batch."""
    return await asyncio.to_thread(
        _render_thumbnail_prompt_sync,
        project_name=project_name,
        topic=topic,
        genre=genre,
        cefr_level=cefr_level,
        template_name=template_name,
        template_description=template_description,
        variant_count=variant_count,
        audience_line=audience_line,
    )


def _render_regenerate_line_prompt_sync(
    *,
    genre: str,
    cefr_level: str,
    topic: str,
    speaker: dict,
    current_text: str,
    line_id: str,
    speaker_id: str,
    presentation_mode: str = "classic",
    explainer_structure: str | None = None,
) -> str:
    """Blocking: validate genre/cefr, then render regenerate_line.txt."""
    solo = _render_presentation_block_sync(presentation_mode, explainer_structure, 1)
    if genre not in GENRES:
        raise ValidationError(f"No prompt support for genre: {genre!r}")
    if cefr_level.upper() not in CEFR_LEVELS:
        raise ValidationError(f"No prompt support for CEFR level: {cefr_level!r}")
    try:
        template = _env.get_template("regenerate_line.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc

    return template.render(
        genre=genre,
        cefr_level=cefr_level,
        topic=topic,
        speaker=speaker,
        current_text=current_text,
        line_id=line_id,
        speaker_id=speaker_id,
        solo_instructions=solo,
        cefr_constraints=_read_cefr_block_sync(cefr_level) if solo else "",
    )


async def render_regenerate_line_prompt(
    *,
    genre: str,
    cefr_level: str,
    topic: str,
    speaker: dict,
    current_text: str,
    line_id: str,
    speaker_id: str,
    presentation_mode: str = "classic",
    explainer_structure: str | None = None,
) -> str:
    """Render the single-line regeneration prompt using prompts/script/regenerate_line.txt.

    Args:
        genre: One of backend.core.constants.GENRES.
        cefr_level: One of backend.core.constants.CEFR_LEVELS.
        topic: Project topic.
        speaker: Speaker dict with name, gender, accent.
        current_text: Current text of the line to rewrite.
        line_id: Existing line UUID.
        speaker_id: Speaker UUID.

    Returns:
        The rendered prompt string.
    """
    return await asyncio.to_thread(
        _render_regenerate_line_prompt_sync,
        genre=genre,
        cefr_level=cefr_level,
        topic=topic,
        speaker=speaker,
        current_text=current_text,
        line_id=line_id,
        speaker_id=speaker_id,
        presentation_mode=presentation_mode,
        explainer_structure=explainer_structure,
    )


def _render_youtube_prompt_sync(
    *, project_name: str, topic: str, genre: str, cefr_level: str, transcript_text: str, audience: str | None = None,
) -> str:
    """Blocking: validate genre/CEFR, then render youtube_package.txt."""
    if genre not in GENRES:
        raise ValidationError(f"No YouTube prompt support for genre: {genre!r}")
    if cefr_level.upper() not in CEFR_LEVELS:
        raise ValidationError(f"No YouTube prompt support for CEFR level: {cefr_level!r}")
    try:
        template = _youtube_env.get_template("youtube_package.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(
        project_name=project_name,
        topic=topic,
        genre=genre,
        cefr_level=cefr_level,
        transcript_text=transcript_text,
        **_audience_fields(audience),
    )


def _audience_fields(audience: str | None) -> dict:
    """Phase 72 (ENH-054): the audience code and its prompt line, when known (the templates default to both)."""
    if not audience:
        return {}
    from backend.content.audience import line

    return {"audience": audience, "audience_line": line(audience)}


async def render_youtube_prompt(
    *, project_name: str, topic: str, genre: str, cefr_level: str, transcript_text: str, audience: str | None = None,
) -> str:
    """Render the YouTube package (titles/description/tags) generation prompt."""
    return await asyncio.to_thread(
        _render_youtube_prompt_sync,
        project_name=project_name,
        topic=topic,
        genre=genre,
        cefr_level=cefr_level,
        transcript_text=transcript_text,
        audience=audience,
    )


_storyboard_env = Environment(
    loader=FileSystemLoader(str(STORYBOARD_PROMPTS_DIR)),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


async def render_explainer_prompt(*, vox: bool = False, **fields) -> str:
    """Render the bounded Solo proposal/repair template outside the event loop (Phase 59: the VOX variant)."""
    def render() -> str:
        try:
            return _storyboard_env.get_template("explainer_vox.txt" if vox else "explainer.txt").render(**fields)
        except TemplateNotFound as exc:
            raise ValidationError("The Solo explainer prompt template is missing") from exc
    return await asyncio.to_thread(render)


def _render_storyboard_prompt_sync(**fields) -> str:
    """Blocking: render the Task 24.2 storyboard prompt (script lines, cast, scene library)."""
    try:
        template = _storyboard_env.get_template("storyboard.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(**fields)


async def render_storyboard_prompt(
    *,
    topic: str,
    genre: str,
    cefr_level: str,
    cast: list[dict],
    lines: list[dict],
    scenes: list[dict],
    framing: int,
    image_cap: int,
    previous_error: str = "",
    activities: list[dict] | None = None,
) -> str:
    """Render the storyboard proposal prompt (Task 24.2); `previous_error` turns it into the repair. `activities` (Gate B-23
    finding): the Activity Library's approved activity names (`name`, `characters` with an own picture), so an insert names
    one the video can actually show."""
    return await asyncio.to_thread(
        _render_storyboard_prompt_sync, topic=topic, genre=genre, cefr_level=cefr_level, cast=cast,
        lines=lines, line_count=len(lines), scenes=scenes, framing=framing, image_cap=image_cap,
        max_places=max(1, image_cap // max(1, framing)), previous_error=previous_error, activities=activities or [],
        max_inserts=max(1, min(6, image_cap - framing)),
    )


_music_env = Environment(
    loader=FileSystemLoader(str(MUSIC_PROMPTS_DIR)),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


def _render_music_pick_prompt_sync(**fields) -> str:
    """Blocking: render the Task 22.8 music pick prompt."""
    try:
        template = _music_env.get_template("music_pick.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(**fields)


async def render_music_pick_prompt(
    *, topic: str, genre: str, cefr_level: str, target_minutes: float, candidates: list[dict],
    previous_error: str = "",
) -> str:
    """Render the auto-select prompt (Task 22.8); `previous_error` turns it into the repair."""
    return await asyncio.to_thread(
        _render_music_pick_prompt_sync, topic=topic, genre=genre, cefr_level=cefr_level,
        target_minutes=target_minutes, candidates=candidates, previous_error=previous_error,
    )


_channel_env = Environment(
    loader=FileSystemLoader(str(CHANNEL_PROMPTS_DIR)),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


def _render_channel_prompt_sync(**fields) -> str:
    try:
        template = _channel_env.get_template("channel_plan.txt")
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(**fields)


async def render_channel_prompt(*, request, audience_line: str | None = None) -> str:
    """Task 36.5 (D104): the AI channel map prompt from the owner's direction (`models.channel.PlanRequest`)."""
    extra = {"audience_line": audience_line} if audience_line else {}
    return await asyncio.to_thread(_render_channel_prompt_sync, request=request, **extra)


_source_env = Environment(
    loader=FileSystemLoader(str(SOURCE_PROMPTS_DIR)),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


def _render_source_prompt_sync(name: str, **fields) -> str:
    try:
        template = _source_env.get_template(name)
    except TemplateNotFound as exc:
        raise ValidationError(f"Prompt template not found: {exc}") from exc
    return template.render(**fields)


async def render_source_prompt(name: str, **fields) -> str:
    """Phase 57 (ENH-039): Step 1 help prompts -- topic ideas and reading a photographed dialogue or word list."""
    return await asyncio.to_thread(_render_source_prompt_sync, name, **fields)
