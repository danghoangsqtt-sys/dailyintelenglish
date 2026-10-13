"""Generate, render, persist, and safely resolve thumbnail variants."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import aiosqlite
from PIL import Image
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from backend.core.config import settings
from backend.core.constants import (
    THUMBNAIL_HEIGHT_16X9, THUMBNAIL_HEIGHT_9X16, THUMBNAIL_JPEG_QUALITY, THUMBNAIL_WIDTH_16X9, THUMBNAIL_WIDTH_9X16,
)
from backend.core.exceptions import (
    ConflictError, NotFoundError, ProviderError, SchemaValidationError, ThumbnailGenerationError,
)
from backend.core.paths import get_project_root
from backend.ai.llm.prompt_loader import render_thumbnail_prompt
from backend.schemas.thumbnail import (
    ThumbnailAspect, ThumbnailEditRequest, ThumbnailFormat, ThumbnailSuggestion, ThumbnailSuggestionPack,
    ThumbnailTemplateConfig,
)
from backend.ai.llm.contracts import GenerationRequest
from backend.ai.llm.router import AIRouter, build_ai_router_from_settings
from backend.ai.llm.validation import parse_and_validate
from backend.media import thumbnail_compose

logger = logging.getLogger(__name__)

PROJECT_ROOT = get_project_root()
ASPECT_SIZES: dict[ThumbnailAspect, tuple[int, int]] = {
    "16x9": (THUMBNAIL_WIDTH_16X9, THUMBNAIL_HEIGHT_16X9),
    "9x16": (THUMBNAIL_WIDTH_9X16, THUMBNAIL_HEIGHT_9X16),
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


_ZONE = {"x": 0.05, "y": 0.2, "width": 0.5, "height": 0.5, "min_font_size": 28, "max_font_size": 116}
TEMPLATES = {
    "composed": ThumbnailTemplateConfig.model_validate({
        "id": "composed", "display_name": "Characters + illustration", "category": "bold", "base_image": "composed.png",
        "description": "The episode's characters (as in the video) over a topic illustration, a big headline, the CEFR "
                       "badge and the channel logo. Each variant changes the picture, the layout and the expressions.",
        "headline_zone": _ZONE, "supporting_zone": _ZONE, "uppercase_headline": True,
    }),
    "outside_ai": ThumbnailTemplateConfig.model_validate({
        "id": "outside_ai", "display_name": "Your outside-AI picture", "category": "bold", "base_image": "outside_ai.png",
        "description": "A picture you made with an outside AI from the episode prompt; the app adds only the headline, the "
                       "CEFR badge and the logo.",
        "headline_zone": _ZONE, "supporting_zone": _ZONE, "uppercase_headline": True,
    }),
}


async def load_template(template_name: str) -> ThumbnailTemplateConfig:
    """One of the two thumbnail kinds (Task 36.3/36.4)."""
    if template_name not in TEMPLATES:
        raise ThumbnailGenerationError(f"Unknown thumbnail template: {template_name!r}")
    return TEMPLATES[template_name]


def outside_image_path(project_id: str) -> Path:
    return settings.DATA_DIR / "thumbnails" / project_id / "outside_source.png"


def topic_picture_path(project_id: str) -> Path:
    """Phase 39 (D118): the topic picture drawn on the local GPU (Qwen-Image-2.1-Turbo); the composed thumbnail uses it
    as its first background."""
    return settings.DATA_DIR / "thumbnails" / project_id / "topic_qwen.png"


async def list_templates(project_id: str | None = None) -> list[dict]:
    """The two thumbnail kinds; `outside_ai` is available once the owner's picture is uploaded."""
    has_outside = bool(project_id) and await asyncio.to_thread(outside_image_path(project_id).is_file)
    return [
        {**TEMPLATES["composed"].model_dump(), "available": True,
         "preview_url": "/static/thumbnail_templates/composed.png"},
        {**TEMPLATES["outside_ai"].model_dump(), "available": has_outside,
         "preview_url": f"/api/projects/{project_id}/thumbnails/outside-image" if has_outside
         else "/static/thumbnail_templates/outside_ai.png"},
    ]


async def storyboard_actions(db: aiosqlite.Connection, project_id: str) -> list[str]:
    """The insert actions of the approved storyboard: what the episode's illustrations show."""
    from backend.library import storyboard_service

    beats = await storyboard_service.approved_beats(db, project_id) or []
    return [beat.get("action") or beat.get("new_place") for beat in beats
            if beat["kind"] == "insert" and (beat.get("action") or beat.get("new_place"))]


def outside_prompt(project: dict, composition: dict, actions: list[str]) -> dict:
    """Task 36.4 (D90): one prompt per episode for an outside image AI, with the character pictures to attach (the same
    approved sprites the video uses), so the characters keep their faces and outfits."""
    characters = sorted(composition.get("characters") or [], key=lambda item: item["slot"])
    pictures = []
    for number, character in enumerate(characters, start=1):
        name = next((candidate for candidate in ("smile__open", "smile__closed", "calm__closed")
                     if candidate in character["names"]), None)
        if name:
            pictures.append({"name": character["name"], "number": number,
                             "url": f"/api/visuals/library/sprites/{character['character_id']}/{name}/content"})
    if len(characters) == 2:
        who = (f"{characters[0]['name']} (attached picture 1) on the left and {characters[1]['name']} (attached picture 2) on "
               "the right, turned slightly towards each other")
    elif characters:
        who = f"{characters[0]['name']} (attached picture 1)"
    else:
        who = "two friendly young adults having a conversation"
    illustration = ", ".join(dict.fromkeys(actions[:3])) or project["topic"]
    text = (
        f"Create a YouTube thumbnail, landscape 16:9 (1280 x 720), for an episode of the English-learning channel Daily Beyond "
        f"English. Topic: {project['topic']}. Show {who}, upper body, big expressive smiles, looking at the viewer. Keep each "
        "person's face, hair and outfit exactly as in the attached picture. Background: a bright, detailed illustration of "
        f"{illustration}. Semi-realistic style, vivid colours, high contrast, sharp focus, eye-catching even at a small size. "
        "Keep the left 45% of the picture calmer and slightly darker for a title. No text, no letters, no numbers, no logo, "
        "no watermark."
    )
    return {"prompt": text, "pictures": pictures}


_SUGGESTION_PACK_ADAPTER = TypeAdapter(ThumbnailSuggestionPack)
_SUPPORTING_KEYS = ("supporting_text", "supporting_line", "supporting", "subline", "subtitle", "tagline")
_KEYWORD_KEYS = ("topic_keywords", "keywords", "topics", "tags")
_PALETTE_KEYS = ("palette", "colors", "colours", "color_palette")


def _hex(value: object) -> object:
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 6 and all(char in "0123456789abcdefABCDEF" for char in text):
            return f"#{text}"
    return value


def normalize_suggestion_pack(parsed: object) -> object:
    """Real-AI finding (Task 36.3, Gemini 3.1 flash lite through the cloud gateway): the answer keeps the meaning but renames
    fields -- `supporting_line`, `keywords`, `colors` or flat `primary_color`, hex without `#`. Map those onto the schema;
    anything else is left for validation to reject."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("variants"), list):
        return parsed
    variants = []
    for item in parsed["variants"]:
        if not isinstance(item, dict):
            variants.append(item)
            continue
        fixed = {"headline": item.get("headline") or item.get("title")}
        fixed["supporting_text"] = next((item[key] for key in _SUPPORTING_KEYS if isinstance(item.get(key), str)), "")
        fixed["topic_keywords"] = next((item[key] for key in _KEYWORD_KEYS if isinstance(item.get(key), list)), None)
        palette = next((item[key] for key in _PALETTE_KEYS if isinstance(item.get(key), dict)), None) or {}
        palette = {str(key).removesuffix("_color").removesuffix("_colour"): value for key, value in palette.items()}
        for role in ("primary", "secondary", "accent", "text"):
            palette.setdefault(role, item.get(f"{role}_color") or item.get(f"{role}_colour"))
        fixed["palette"] = {role: _hex(palette.get(role)) for role in ("primary", "secondary", "accent", "text")}
        variants.append(fixed)
    return {**parsed, "variants": variants}


async def generate_suggestions(
    project: dict,
    template: ThumbnailTemplateConfig,
    variant_count: int,
    router: AIRouter | None = None,
) -> ThumbnailSuggestionPack:
    """Generate and semantically validate one text/palette suggestion pack.

    Migrated from a duplicated direct-Gemini retry/fallback-model transport to
    `AIRouter` (Phase 13, Task 13.7) -- see `script_service.generate_script` for the
    identical reasoning.

    Args:
        router: Injected `AIRouter` (tests pass a `FakeProvider`-backed one with
            zero network calls); defaults to `build_ai_router_from_settings()`.

    Phase 18: an unconfigured cloud key/model no longer raises here --
    `build_ai_router_from_settings()`'s `compute_effective_mode` already
    degrades to local automatically, per invariant 32.
    """
    prompt = await render_thumbnail_prompt(
        project_name=project["name"],
        topic=project["topic"],
        genre=project["genre"],
        cefr_level=project["cefr_level"],
        template_name=template.id,
        template_description=template.description,
        variant_count=variant_count,
    )
    router = router or build_ai_router_from_settings()
    request = GenerationRequest(
        prompt=prompt,
        json_schema=ThumbnailSuggestionPack.model_json_schema(),
        deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS,
        purpose="thumbnail_suggestions",
    )
    try:
        result = await router.generate(request)
    except ProviderError as exc:
        raise ThumbnailGenerationError(f"Thumbnail suggestion generation failed: {exc}") from exc

    text = result.text
    try:
        text = json.dumps(normalize_suggestion_pack(json.loads(text)))
    except (json.JSONDecodeError, TypeError):
        pass  # parse_and_validate reports it
    try:
        pack = parse_and_validate(text, _SUGGESTION_PACK_ADAPTER)
    except SchemaValidationError as exc:
        raise ThumbnailGenerationError(str(exc)) from exc
    if len(pack.variants) != variant_count:
        raise ThumbnailGenerationError(
            f"Gemini returned {len(pack.variants)} variants; expected exactly {variant_count}"
        )
    return pack


def _render_image(
    template: ThumbnailTemplateConfig,
    suggestion: ThumbnailSuggestion,
    aspect: ThumbnailAspect,
    composition: dict,
    variant_index: int,
) -> Image.Image:
    """Render one suggestion at one aspect ratio (Task 36.3/36.4: `thumbnail_compose`)."""
    if template.id == "outside_ai" and not (composition.get("outside_image") and Path(composition["outside_image"]).is_file()):
        raise ThumbnailGenerationError("Upload your outside-AI picture first")
    return thumbnail_compose.render(composition, suggestion, aspect, variant_index, template.id)


def _render_record_sync(
    project_id: str,
    thumbnail_id: str,
    variant_index: int,
    template: ThumbnailTemplateConfig,
    suggestion: ThumbnailSuggestion,
    revision: str,
    composition: dict,
) -> dict:
    """Render and stage one complete four-file thumbnail revision."""
    variant_dir = settings.DATA_DIR / "thumbnails" / project_id / revision
    variant_dir.parent.mkdir(parents=True, exist_ok=True)
    variant_dir.mkdir()
    try:
        assets: dict[str, dict[str, str]] = {}
        for aspect in ASPECT_SIZES:
            image = _render_image(template, suggestion, aspect, composition, variant_index)
            try:
                png_path = variant_dir / f"{aspect}.png"
                jpg_path = variant_dir / f"{aspect}.jpg"
                image.save(png_path, format="PNG", optimize=True)
                image.save(jpg_path, format="JPEG", quality=THUMBNAIL_JPEG_QUALITY)
            finally:
                image.close()
            assets[aspect] = {"png": str(png_path), "jpg": str(jpg_path)}
        sidecar = {
            "id": thumbnail_id,
            "project_id": project_id,
            "template_name": template.id,
            "variant_index": variant_index,
            "revision": revision,
            "suggestion": suggestion.model_dump(),
            "assets": assets,
            "composition": composition,  # Task 36.3: an edit re-renders the same picture
        }
        (variant_dir / "render.json").write_text(
            json.dumps(sidecar, indent=2), encoding="utf-8"
        )
        return sidecar
    except Exception:
        shutil.rmtree(variant_dir, ignore_errors=True)
        raise


def _render_batch_sync(
    project_id: str,
    template: ThumbnailTemplateConfig,
    suggestions: list[ThumbnailSuggestion],
    composition: dict,
) -> list[dict]:
    """Render one selected template once per suggestion, producing four derivatives per row."""
    project_dir = settings.DATA_DIR / "thumbnails" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    try:
        for variant_index, suggestion in enumerate(suggestions):
            thumbnail_id = str(uuid.uuid4())
            records.append(
                _render_record_sync(
                    project_id,
                    thumbnail_id,
                    variant_index,
                    template,
                    suggestion,
                    thumbnail_id,
                    composition,
                )
            )
    except Exception:
        for record in records:
            shutil.rmtree(Path(record["assets"]["16x9"]["png"]).parent, ignore_errors=True)
        raise
    return records


async def render_batch(
    project_id: str,
    template: ThumbnailTemplateConfig,
    suggestions: list[ThumbnailSuggestion],
    composition: dict,
) -> list[dict]:
    """Render all derivatives in a worker thread and return persistence-ready records."""
    try:
        return await asyncio.to_thread(_render_batch_sync, project_id, template, suggestions, composition)
    except ThumbnailGenerationError:
        raise
    except Exception as exc:
        raise ThumbnailGenerationError(f"Thumbnail rendering failed: {exc}") from exc


def _record_revision(record: dict) -> str:
    return Path(record["image_path_16x9"]).parent.name


def _load_suggestion_sync(record: dict) -> ThumbnailSuggestion:
    sidecar_path = Path(record["image_path_16x9"]).parent / "render.json"
    try:
        metadata = json.loads(sidecar_path.read_text("utf-8"))
        for field in ("id", "project_id", "template_name", "variant_index"):
            if metadata[field] != record[field]:
                raise ValueError(f"sidecar {field} does not match its database row")
        return ThumbnailSuggestion.model_validate(metadata["suggestion"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError, PydanticValidationError) as exc:
        raise ThumbnailGenerationError(
            f"Thumbnail render metadata is unavailable: {record['id']}"
        ) from exc


async def load_suggestion(record: dict) -> ThumbnailSuggestion:
    """Load and validate the persisted suggestion for one thumbnail row."""
    return await asyncio.to_thread(_load_suggestion_sync, record)


async def render_edited_thumbnail(record: dict, edit: ThumbnailEditRequest) -> dict:
    """Stage a fresh revision for one row while preserving its non-editable metadata."""
    if _record_revision(record) != str(edit.revision):
        raise ConflictError("Thumbnail was changed by another request; reload and try again.")
    template, current = await asyncio.gather(
        load_template(record["template_name"]),
        load_suggestion(record),
    )
    suggestion = ThumbnailSuggestion.model_validate(
        {
            **current.model_dump(),
            "headline": edit.headline,
            "palette": edit.palette.model_dump(),
        }
    )
    revision = str(uuid.uuid4())
    sidecar_path = Path(record["image_path_16x9"]).parent / "render.json"
    try:
        sidecar = await asyncio.to_thread(lambda: json.loads(sidecar_path.read_text("utf-8")))
    except (OSError, ValueError) as exc:
        raise ThumbnailGenerationError("Thumbnail render metadata is unavailable") from exc
    composition = sidecar.get("composition") or {}
    try:
        return await asyncio.to_thread(
            _render_record_sync,
            record["project_id"],
            record["id"],
            record["variant_index"],
            template,
            suggestion,
            revision,
            composition,
        )
    except ThumbnailGenerationError:
        raise
    except Exception as exc:
        raise ThumbnailGenerationError(f"Thumbnail rendering failed: {exc}") from exc


async def get_thumbnail_rows(db: aiosqlite.Connection, project_id: str) -> list[dict]:
    """Return persisted thumbnail rows ordered by their A/B variant index."""
    cursor = await db.execute(
        "SELECT id, project_id, template_name, variant_index, image_path_16x9, "
        "image_path_9x16, is_selected, created_at FROM thumbnails "
        "WHERE project_id = ? ORDER BY variant_index",
        (project_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def get_thumbnail_row(
    db: aiosqlite.Connection,
    project_id: str,
    thumbnail_id: str,
) -> dict:
    """Return one thumbnail only when it belongs to the requested project."""
    cursor = await db.execute(
        "SELECT id, project_id, template_name, variant_index, image_path_16x9, "
        "image_path_9x16, is_selected, created_at FROM thumbnails "
        "WHERE id = ? AND project_id = ?",
        (thumbnail_id, project_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Thumbnail not found.")
    return dict(row)


async def replace_thumbnail_rows(
    db: aiosqlite.Connection,
    project_id: str,
    records: list[dict],
    commit: bool = True,
) -> list[dict]:
    """Replace one project's thumbnail rows and return the superseded rows for cleanup."""
    old_rows = await get_thumbnail_rows(db, project_id)
    await db.execute("DELETE FROM thumbnails WHERE project_id = ?", (project_id,))
    created_at = _now()
    await db.executemany(
        "INSERT INTO thumbnails "
        "(id, project_id, template_name, variant_index, image_path_16x9, image_path_9x16, "
        "is_selected, created_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
        [
            (
                record["id"],
                project_id,
                record["template_name"],
                record["variant_index"],
                record["assets"]["16x9"]["png"],
                record["assets"]["9x16"]["png"],
                created_at,
            )
            for record in records
        ],
    )
    if commit:
        await db.commit()
    return old_rows


async def update_thumbnail_revision(
    db: aiosqlite.Connection,
    project_id: str,
    thumbnail_id: str,
    expected_revision: str,
    rendered: dict,
    commit: bool = True,
) -> dict:
    """CAS-update one row to a staged revision and return its superseded row."""
    current = await get_thumbnail_row(db, project_id, thumbnail_id)
    if _record_revision(current) != expected_revision:
        raise ConflictError("Thumbnail was changed by another request; reload and try again.")
    cursor = await db.execute(
        "UPDATE thumbnails SET image_path_16x9 = ?, image_path_9x16 = ? "
        "WHERE id = ? AND project_id = ? AND image_path_16x9 = ?",
        (
            rendered["assets"]["16x9"]["png"],
            rendered["assets"]["9x16"]["png"],
            thumbnail_id,
            project_id,
            current["image_path_16x9"],
        ),
    )
    if cursor.rowcount != 1:
        raise ConflictError("Thumbnail was changed by another request; reload and try again.")
    if commit:
        await db.commit()
    return current


async def select_favorite(
    db: aiosqlite.Connection,
    project_id: str,
    thumbnail_id: str,
    commit: bool = True,
) -> dict:
    """Idempotently select exactly one favorite thumbnail for a project."""
    selected = await get_thumbnail_row(db, project_id, thumbnail_id)
    await db.execute(
        "UPDATE thumbnails SET is_selected = CASE WHEN id = ? THEN 1 ELSE 0 END "
        "WHERE project_id = ?",
        (thumbnail_id, project_id),
    )
    if commit:
        await db.commit()
    selected["is_selected"] = 1
    return selected


def _public_record(record: dict) -> dict:
    thumbnail_id = record["id"]
    project_id = record["project_id"]
    suggestion = _load_suggestion_sync(record).model_dump()
    revision = _record_revision(record)
    encoded_revision = quote(revision, safe="")
    base_url = f"/api/projects/{project_id}/thumbnails/{thumbnail_id}"
    return {
        "id": thumbnail_id,
        "project_id": project_id,
        "template_name": record["template_name"],
        "variant_index": record["variant_index"],
        "is_selected": bool(record["is_selected"]),
        "created_at": record["created_at"],
        "revision": revision,
        "suggestion": suggestion,
        "assets": {
            aspect: {
                image_format: (
                    f"{base_url}/{aspect}.{image_format}?revision={encoded_revision}"
                )
                for image_format in ("png", "jpg")
            }
            for aspect in ASPECT_SIZES
        },
    }


async def public_records(records: list[dict]) -> list[dict]:
    """Hydrate DB rows with render metadata and safe API content URLs."""
    return await asyncio.to_thread(lambda: [_public_record(record) for record in records])


def _cleanup_rows_sync(rows: list[dict]) -> None:
    for row in rows:
        path_value = row.get("image_path_16x9") or row.get("assets", {}).get("16x9", {}).get("png")
        if path_value:
            shutil.rmtree(Path(path_value).parent, ignore_errors=True)


async def cleanup_rows(rows: list[dict]) -> None:
    """Remove derivative directories belonging only to the supplied thumbnail rows."""
    await asyncio.to_thread(_cleanup_rows_sync, rows)


def _resolve_content_sync(
    row: dict,
    aspect: ThumbnailAspect,
    image_format: ThumbnailFormat,
) -> Path:
    canonical = Path(row["image_path_16x9"] if aspect == "16x9" else row["image_path_9x16"])
    candidate = canonical.with_suffix(f".{image_format}").resolve()
    project_root = (settings.DATA_DIR / "thumbnails" / row["project_id"]).resolve()
    if project_root not in candidate.parents or not candidate.is_file():
        raise NotFoundError("Thumbnail image not found.")
    return candidate


async def resolve_content_path(
    db: aiosqlite.Connection,
    project_id: str,
    thumbnail_id: str,
    aspect: ThumbnailAspect,
    image_format: ThumbnailFormat,
) -> Path:
    """Resolve one validated derivative path owned by the requested project and thumbnail."""
    cursor = await db.execute(
        "SELECT id, project_id, image_path_16x9, image_path_9x16 FROM thumbnails "
        "WHERE id = ? AND project_id = ?",
        (thumbnail_id, project_id),
    )
    row = await cursor.fetchone()
    if row is None:
        raise NotFoundError("Thumbnail not found.")
    return await asyncio.to_thread(_resolve_content_sync, dict(row), aspect, image_format)
