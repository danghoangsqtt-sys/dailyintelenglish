"""Thumbnail generation, listing, template discovery, and content routes."""

import time

import aiosqlite
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.api.projects import _read_transaction, _write_transaction
from app.core.responses import ok
from app.db.database import get_db
from app.models.thumbnail import (
    ThumbnailAspect,
    ThumbnailEditRequest,
    ThumbnailFormat,
    ThumbnailGenerateRequest,
)
from app.services import project_service, thumbnail_service

router = APIRouter(tags=["thumbnails"])


@router.get("/api/thumbnails/templates")
async def list_thumbnail_templates() -> dict:
    """List the five validated checked-in thumbnail templates."""
    started_at = time.perf_counter()
    templates = await thumbnail_service.list_templates()
    return ok(templates, started_at=started_at)


@router.post("/api/projects/{project_id}/thumbnails/generate")
async def generate_thumbnails(
    project_id: str,
    payload: ThumbnailGenerateRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Generate and persist exactly N variants for one project and selected template."""
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)

    template = await thumbnail_service.load_template(payload.template_name)
    suggestions = await thumbnail_service.generate_suggestions(
        project,
        template,
        payload.variant_count,
    )
    rendered = await thumbnail_service.render_batch(project_id, template, suggestions.variants)
    try:
        async with _write_transaction(db):
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
    async with _read_transaction():
        rows = await thumbnail_service.get_thumbnail_rows(db, project_id)
    result = await thumbnail_service.public_records(rows)
    return ok(result, started_at=started_at)


@router.get("/api/projects/{project_id}/thumbnails")
async def list_project_thumbnails(
    project_id: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """List the current persisted thumbnail generation batch for a project."""
    started_at = time.perf_counter()
    async with _read_transaction():
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
    async with _write_transaction(db):
        await project_service.get_project(db, project_id)
        await thumbnail_service.select_favorite(
            db,
            project_id,
            thumbnail_id,
            commit=False,
        )
    async with _read_transaction():
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
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        current = await thumbnail_service.get_thumbnail_row(db, project_id, thumbnail_id)

    rendered = await thumbnail_service.render_edited_thumbnail(current, payload)
    try:
        async with _write_transaction(db):
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
    async with _read_transaction():
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
    async with _read_transaction():
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
