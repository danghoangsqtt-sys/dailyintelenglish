"""Thumbnail generation, listing, template discovery, and content routes."""

import asyncio
import io
import time

import aiosqlite
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.core.exceptions import NotFoundError, ValidationError

from app.db.transactions import read_transaction, write_transaction
from app.core.responses import ok
from app.db.database import get_db
from app.models.thumbnail import (
    ThumbnailAspect,
    ThumbnailEditRequest,
    ThumbnailFormat,
    ThumbnailGenerateRequest,
)
from app.services import project_service, thumbnail_compose, thumbnail_service

router = APIRouter(tags=["thumbnails"])


@router.get("/api/thumbnails/templates")
async def list_thumbnail_templates(
    project_id: str | None = None, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """The two thumbnail kinds (Task 36.3/36.4): composed, and the owner's outside-AI picture once uploaded."""
    started_at = time.perf_counter()
    if project_id:
        async with read_transaction():
            await project_service.get_project(db, project_id)
    templates = await thumbnail_service.list_templates(project_id)
    return ok(templates, started_at=started_at)


@router.post("/api/projects/{project_id}/thumbnails/generate")
async def generate_thumbnails(
    project_id: str,
    payload: ThumbnailGenerateRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Generate and persist exactly N variants for one project and selected template."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)

    template = await thumbnail_service.load_template(payload.template_name)
    async with read_transaction():
        composition = await thumbnail_compose.composition_inputs(db, project)
    if template.id == "outside_ai" and not composition["outside_image"]:
        raise ValidationError("Upload your outside-AI picture first")
    suggestions = await thumbnail_service.generate_suggestions(
        project,
        template,
        payload.variant_count,
    )
    rendered = await thumbnail_service.render_batch(
        project_id, template, suggestions.variants, composition,
    )
    try:
        async with write_transaction(db):
            old_rows = await thumbnail_service.replace_thumbnail_rows(
                db,
                project_id,
                rendered,
                commit=False,
            )
    except Exception:
        await thumbnail_service.cleanup_rows(rendered)
        raise

    await thumbnail_service.cleanup_rows(old_rows)
    async with read_transaction():
        rows = await thumbnail_service.get_thumbnail_rows(db, project_id)
    result = await thumbnail_service.public_records(rows)
    return ok(result, started_at=started_at)


def _store_outside_image(project_id: str, content: bytes) -> None:
    try:
        with Image.open(io.BytesIO(content)) as opened:
            opened.verify()
        with Image.open(io.BytesIO(content)) as opened:
            picture = opened.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError("The file is not a readable picture (PNG, JPEG or WebP)") from exc
    if picture.width < 640 or picture.height < 360:
        raise ValidationError("The picture is too small: at least 640 x 360 (1280 x 720 recommended)")
    target = thumbnail_service.outside_image_path(project_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".upload")
    picture.save(temporary, format="PNG")
    temporary.replace(target)


@router.post("/api/projects/{project_id}/thumbnails/outside-image", status_code=201)
async def upload_outside_image(
    project_id: str, file: UploadFile = File(...), db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Task 36.4 (D90): the owner's thumbnail picture made with an outside AI; the `outside_ai` thumbnail draws on it."""
    async with read_transaction():
        await project_service.get_project(db, project_id)
    content = await file.read()
    if not content or len(content) > 20 * 1024 * 1024:
        raise ValidationError("The picture must be between 1 byte and 20 MB")
    await asyncio.to_thread(_store_outside_image, project_id, content)
    return ok({"preview_url": f"/api/projects/{project_id}/thumbnails/outside-image"})


@router.get("/api/projects/{project_id}/thumbnails/outside-image")
async def get_outside_image(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        await project_service.get_project(db, project_id)
    path = thumbnail_service.outside_image_path(project_id)
    if not await asyncio.to_thread(path.is_file):
        raise NotFoundError("No outside-AI picture yet")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/api/projects/{project_id}/thumbnails/outside-prompt")
async def get_outside_prompt(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Task 36.4 (D90): the prompt to paste into an outside AI and the character pictures to attach with it."""
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        composition = await thumbnail_compose.composition_inputs(db, project)
        beats = await thumbnail_service.storyboard_actions(db, project_id)
    return ok(thumbnail_service.outside_prompt(project, composition, beats))


@router.get("/api/projects/{project_id}/thumbnails")
async def list_project_thumbnails(
    project_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """List the current persisted thumbnail generation batch for a project."""
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        rows = await thumbnail_service.get_thumbnail_rows(db, project_id)
    result = await thumbnail_service.public_records(rows)
    return ok(result, started_at=started_at)


@router.put("/api/projects/{project_id}/thumbnails/{thumbnail_id}/favorite")
async def select_thumbnail_favorite(
    project_id: str,
    thumbnail_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Idempotently select one project thumbnail as its exclusive favorite."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        await project_service.get_project(db, project_id)
        await thumbnail_service.select_favorite(
            db,
            project_id,
            thumbnail_id,
            commit=False,
        )
    async with read_transaction():
        selected = await thumbnail_service.get_thumbnail_row(db, project_id, thumbnail_id)
        result = (await thumbnail_service.public_records([selected]))[0]
    return ok(result, started_at=started_at)


@router.patch("/api/projects/{project_id}/thumbnails/{thumbnail_id}")
async def edit_thumbnail(
    project_id: str,
    thumbnail_id: str,
    payload: ThumbnailEditRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Persist one optimistic headline/palette edit and its fresh image revision."""
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        current = await thumbnail_service.get_thumbnail_row(db, project_id, thumbnail_id)

    rendered = await thumbnail_service.render_edited_thumbnail(current, payload)
    try:
        async with write_transaction(db):
            old_row = await thumbnail_service.update_thumbnail_revision(
                db,
                project_id,
                thumbnail_id,
                str(payload.revision),
                rendered,
                commit=False,
            )
    except Exception:
        await thumbnail_service.cleanup_rows([rendered])
        raise

    await thumbnail_service.cleanup_rows([old_row])
    async with read_transaction():
        updated = await thumbnail_service.get_thumbnail_row(db, project_id, thumbnail_id)
        result = (await thumbnail_service.public_records([updated]))[0]
    return ok(result, started_at=started_at)


@router.get(
    "/api/projects/{project_id}/thumbnails/{thumbnail_id}/{aspect}.{image_format}"
)
async def get_thumbnail_content(
    project_id: str,
    thumbnail_id: str,
    aspect: ThumbnailAspect,
    image_format: ThumbnailFormat,
    db: aiosqlite.Connection = Depends(get_db),
) -> FileResponse:
    """Serve one validated thumbnail derivative without exposing the runtime data tree."""
    async with read_transaction():
        await project_service.get_project(db, project_id)
        path = await thumbnail_service.resolve_content_path(
            db,
            project_id,
            thumbnail_id,
            aspect,
            image_format,
        )
    media_type = "image/png" if image_format == "png" else "image/jpeg"
    return FileResponse(path, media_type=media_type)
