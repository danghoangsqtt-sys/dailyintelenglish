"""Generate, render, persist, and safely resolve thumbnail variants."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import httpx
from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.constants import (
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_RETRY_BASE_DELAY,
    THUMBNAIL_ACCENT_HEIGHT_RATIO,
    THUMBNAIL_FONT_SIZE_STEP,
    THUMBNAIL_HEIGHT_16X9,
    THUMBNAIL_HEIGHT_9X16,
    THUMBNAIL_JPEG_QUALITY,
    THUMBNAIL_LINE_SPACING_RATIO,
    THUMBNAIL_MIN_LINE_SPACING,
    THUMBNAIL_TEMPLATE_IDS,
    THUMBNAIL_WIDTH_16X9,
    THUMBNAIL_WIDTH_9X16,
)
from app.core.exceptions import NotFoundError, ThumbnailGenerationError
from app.core.prompt_loader import render_thumbnail_prompt
from app.models.thumbnail import (
    TextZone,
    ThumbnailAspect,
    ThumbnailFormat,
    ThumbnailSuggestion,
    ThumbnailSuggestionPack,
    ThumbnailTemplateConfig,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_DIR = PROJECT_ROOT / "frontend" / "static" / "thumbnail_templates"
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ASPECT_SIZES: dict[ThumbnailAspect, tuple[int, int]] = {
    "16x9": (THUMBNAIL_WIDTH_16X9, THUMBNAIL_HEIGHT_16X9),
    "9x16": (THUMBNAIL_WIDTH_9X16, THUMBNAIL_HEIGHT_9X16),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _call_gemini(prompt: str, schema: dict) -> tuple[httpx.Response, float]:
    """Make one async Gemini request with JSON Schema enforced at the network layer."""
    url = GEMINI_ENDPOINT.format(model=GEMINI_MODEL)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        },
    }
    started_at = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload)
    return response, (time.perf_counter() - started_at) * 1000


async def _generate_with_retry(prompt: str, schema: dict) -> str:
    """Return Gemini text, retrying only rate-limit responses with exponential backoff."""
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    delay = GEMINI_RETRY_BASE_DELAY
    for attempt in range(1, GEMINI_MAX_RETRIES + 1):
        try:
            response, latency_ms = await _call_gemini(prompt, schema)
        except httpx.RequestError as exc:
            raise ThumbnailGenerationError(f"Gemini API request failed: {exc}") from exc

        if response.status_code == 200:
            data = response.json()
            logger.info(
                "gemini_thumbnail_call model=%s prompt_hash=%s latency_ms=%.1f "
                "tokens_used=%s attempt=%d",
                GEMINI_MODEL,
                prompt_hash,
                latency_ms,
                data.get("usageMetadata", {}).get("totalTokenCount"),
                attempt,
            )
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as exc:
                raise ThumbnailGenerationError(
                    f"Unexpected Gemini response shape: {exc}"
                ) from exc

        if response.status_code == 429 and attempt < GEMINI_MAX_RETRIES:
            logger.warning(
                "gemini_thumbnail_rate_limited prompt_hash=%s attempt=%d retry_in_s=%.1f",
                prompt_hash,
                attempt,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2
            continue

        raise ThumbnailGenerationError(
            f"Gemini API returned HTTP {response.status_code} after {attempt} attempt(s): "
            f"{response.text[:200]}"
        )
    raise ThumbnailGenerationError("Gemini API retry loop ended unexpectedly")


def _load_template_sync(template_name: str) -> ThumbnailTemplateConfig:
    """Load one approved template config and verify its paired PNG asset."""
    if template_name not in THUMBNAIL_TEMPLATE_IDS:
        raise ThumbnailGenerationError(f"Unknown thumbnail template: {template_name!r}")
    config_path = TEMPLATE_DIR / f"{template_name}.json"
    try:
        config = ThumbnailTemplateConfig.model_validate_json(config_path.read_text("utf-8"))
    except (OSError, PydanticValidationError) as exc:
        raise ThumbnailGenerationError(
            f"Thumbnail template config is unavailable or invalid: {template_name}"
        ) from exc
    if config.id != template_name:
        raise ThumbnailGenerationError("Thumbnail template config id does not match its filename")
    if not (TEMPLATE_DIR / config.base_image).is_file():
        raise ThumbnailGenerationError(f"Thumbnail base image is missing: {config.base_image}")
    return config


async def load_template(template_name: str) -> ThumbnailTemplateConfig:
    """Load and validate one approved thumbnail template without blocking the event loop."""
    return await asyncio.to_thread(_load_template_sync, template_name)


def _list_templates_sync() -> list[dict]:
    return [
        {
            **_load_template_sync(template_id).model_dump(),
            "preview_url": f"/static/thumbnail_templates/{template_id}.png",
        }
        for template_id in THUMBNAIL_TEMPLATE_IDS
    ]


async def list_templates() -> list[dict]:
    """Return public metadata for all five validated template assets."""
    return await asyncio.to_thread(_list_templates_sync)


async def generate_suggestions(
    project: dict,
    template: ThumbnailTemplateConfig,
    variant_count: int,
) -> ThumbnailSuggestionPack:
    """Generate and semantically validate one Gemini text/palette suggestion pack."""
    if not settings.GEMINI_API_KEY:
        raise ThumbnailGenerationError("DIE_GEMINI_API_KEY is not configured")
    prompt = await render_thumbnail_prompt(
        project_name=project["name"],
        topic=project["topic"],
        genre=project["genre"],
        cefr_level=project["cefr_level"],
        template_name=template.id,
        template_description=template.description,
        variant_count=variant_count,
    )
    raw_text = await _generate_with_retry(prompt, ThumbnailSuggestionPack.model_json_schema())
    try:
        pack = ThumbnailSuggestionPack.model_validate_json(raw_text)
    except PydanticValidationError as exc:
        raise ThumbnailGenerationError(
            f"Gemini response failed thumbnail schema validation: {exc}"
        ) from exc
    if len(pack.variants) != variant_count:
        raise ThumbnailGenerationError(
            f"Gemini returned {len(pack.variants)} variants; expected exactly {variant_count}"
        )
    return pack


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load Pillow's scalable embedded font without consulting operating-system paths."""
    return ImageFont.load_default(size=size)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, width: int) -> str:
    words = text.split()
    if not words:
        return ""
    lines = [words[0]]
    for word in words[1:]:
        candidate = f"{lines[-1]} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return "\n".join(lines)


def _zone_pixels(zone: TextZone, size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = size
    return (
        round(zone.x * width),
        round(zone.y * height),
        round(zone.width * width),
        round(zone.height * height),
    )


def _draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    zone: TextZone,
    canvas_size: tuple[int, int],
    color: str,
) -> None:
    """Wrap and shrink text until it fits completely inside a normalized template zone."""
    if not text:
        return
    x, y, max_width, max_height = _zone_pixels(zone, canvas_size)
    for font_size in range(zone.max_font_size, zone.min_font_size - 1, -THUMBNAIL_FONT_SIZE_STEP):
        font = _font(font_size)
        wrapped = _wrap_text(draw, text, font, max_width)
        spacing = max(
            THUMBNAIL_MIN_LINE_SPACING,
            round(font_size * THUMBNAIL_LINE_SPACING_RATIO),
        )
        bounds = draw.multiline_textbbox(
            (0, 0), wrapped, font=font, spacing=spacing, align=zone.align
        )
        text_width = bounds[2] - bounds[0]
        text_height = bounds[3] - bounds[1]
        if text_width <= max_width and text_height <= max_height:
            if zone.align == "center":
                draw_x = x + (max_width - text_width) / 2
            elif zone.align == "right":
                draw_x = x + max_width - text_width
            else:
                draw_x = x
            draw.multiline_text(
                (draw_x, y), wrapped, fill=color, font=font, spacing=spacing, align=zone.align
            )
            return
    raise ThumbnailGenerationError("Thumbnail text does not fit within its template zone")


def _render_image(
    template: ThumbnailTemplateConfig,
    suggestion: ThumbnailSuggestion,
    aspect: ThumbnailAspect,
) -> Image.Image:
    """Render one suggestion/template pairing at one target aspect ratio."""
    size = ASPECT_SIZES[aspect]
    with Image.open(TEMPLATE_DIR / template.base_image) as source:
        base = ImageOps.fit(source.convert("L"), size, method=Image.Resampling.LANCZOS)
    image = ImageOps.colorize(
        base,
        black=ImageColor.getrgb(suggestion.palette.primary),
        white=ImageColor.getrgb(suggestion.palette.secondary),
    ).convert("RGB")
    draw = ImageDraw.Draw(image)
    accent_height = max(
        THUMBNAIL_MIN_LINE_SPACING,
        round(size[1] * THUMBNAIL_ACCENT_HEIGHT_RATIO),
    )
    draw.rectangle((0, size[1] - accent_height, size[0], size[1]), fill=suggestion.palette.accent)
    headline = suggestion.headline.upper() if template.uppercase_headline else suggestion.headline
    _draw_fitted_text(draw, headline, template.headline_zone, size, suggestion.palette.text)
    _draw_fitted_text(
        draw,
        suggestion.supporting_text,
        template.supporting_zone,
        size,
        suggestion.palette.text,
    )
    return image


def _render_batch_sync(
    project_id: str,
    template: ThumbnailTemplateConfig,
    suggestions: list[ThumbnailSuggestion],
) -> list[dict]:
    """Render one selected template once per suggestion, producing four derivatives per row."""
    project_dir = settings.DATA_DIR / "thumbnails" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    created_dirs: list[Path] = []
    try:
        for variant_index, suggestion in enumerate(suggestions):
            thumbnail_id = str(uuid.uuid4())
            variant_dir = project_dir / thumbnail_id
            variant_dir.mkdir()
            created_dirs.append(variant_dir)
            assets: dict[str, dict[str, str]] = {}
            for aspect in ASPECT_SIZES:
                image = _render_image(template, suggestion, aspect)
                png_path = variant_dir / f"{aspect}.png"
                jpg_path = variant_dir / f"{aspect}.jpg"
                image.save(png_path, format="PNG", optimize=True)
                image.save(jpg_path, format="JPEG", quality=THUMBNAIL_JPEG_QUALITY)
                assets[aspect] = {"png": str(png_path), "jpg": str(jpg_path)}
            sidecar = {
                "id": thumbnail_id,
                "project_id": project_id,
                "template_name": template.id,
                "variant_index": variant_index,
                "suggestion": suggestion.model_dump(),
                "assets": assets,
            }
            (variant_dir / "render.json").write_text(
                json.dumps(sidecar, indent=2), encoding="utf-8"
            )
            records.append(sidecar)
    except Exception:
        for variant_dir in created_dirs:
            shutil.rmtree(variant_dir, ignore_errors=True)
        raise
    return records


async def render_batch(
    project_id: str,
    template: ThumbnailTemplateConfig,
    suggestions: list[ThumbnailSuggestion],
) -> list[dict]:
    """Render all derivatives in a worker thread and return persistence-ready records."""
    try:
        return await asyncio.to_thread(_render_batch_sync, project_id, template, suggestions)
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


def _public_record(record: dict) -> dict:
    thumbnail_id = record["id"]
    project_id = record["project_id"]
    sidecar_path = Path(record["image_path_16x9"]).parent / "render.json"
    try:
        suggestion = json.loads(sidecar_path.read_text("utf-8"))["suggestion"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise ThumbnailGenerationError(
            f"Thumbnail render metadata is unavailable: {thumbnail_id}"
        ) from exc
    base_url = f"/api/projects/{project_id}/thumbnails/{thumbnail_id}"
    return {
        "id": thumbnail_id,
        "project_id": project_id,
        "template_name": record["template_name"],
        "variant_index": record["variant_index"],
        "is_selected": bool(record["is_selected"]),
        "created_at": record["created_at"],
        "suggestion": suggestion,
        "assets": {
            aspect: {
                image_format: f"{base_url}/{aspect}.{image_format}"
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
