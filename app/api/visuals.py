"""Character, scene, and project visuals API."""

import asyncio
import json
import logging
import time
from typing import Literal

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.visuals import (
    AGE_GROUPS, BOTTOMS, COLORS, GENDERS, SCENE_CATEGORIES, TIMES_OF_DAY, TOPS, ActivityApproveBatchInput,
    ActivityMetadataInput, ActivityMetadataPatch, ActivityReviewInput, ApprovalInput, CastMemberInput, CharacterInput,
    CharacterPatch, ReferenceInput, SceneInput, ScenePatch, SheetItemInput, ShotReviewInput,
)
from app.services import project_service
from app.services.visuals import jobs
from app.services.visuals import activity_library_service as activity_library
from app.services.visuals import activity_matcher
from app.services.visuals import library_service as library
from app.services.visuals import project_visuals_service as project_visuals
from app.services.visuals import shot_library_service as shot_library
from app.services.visuals import sprite_service
from app.services.visuals import storyboard_service
from app.services.visuals.engine import IMAGE_PYTHON, require_generation

router = APIRouter(prefix="/api/visuals", tags=["visuals"])
project_router = APIRouter(prefix="/api/projects/{project_id}/visuals", tags=["visuals"])
logger = logging.getLogger(__name__)


def _form_labels(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("/health")
async def visuals_health(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    started_at = time.perf_counter()
    async with read_transaction():
        queue = await jobs.queue_counts(db)
    return ok({"enabled": settings.AI_VISUALS_ENABLED, "engine": settings.IMAGE_ENGINE,
               "venv_image_present": IMAGE_PYTHON.is_file(), "queue": queue}, started_at=started_at)


@router.get("/options")
async def visuals_options() -> dict:
    return ok({"colors": COLORS, "tops": TOPS, "bottoms": BOTTOMS,
               "age_groups": AGE_GROUPS, "genders": GENDERS, "style_id": "editorial_photo",
               "scene_categories": SCENE_CATEGORIES, "times_of_day": TIMES_OF_DAY})


@router.get("/characters")
async def list_characters(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        rows = await library.list_characters(db)
    return ok(rows)


@router.post("/characters")
async def create_character(body: CharacterInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await library.create_character(db, body)
    return ok(row)


@router.get("/characters/{character_id}")
async def get_character(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        row = await library.character_view(db, character_id)
    return ok(row)


@router.patch("/characters/{character_id}")
async def edit_character(
    character_id: str, body: CharacterPatch, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        row = await library.edit_character(db, character_id, body)
    return ok(row)


@router.delete("/characters/{character_id}")
async def delete_character(
    character_id: str, force: bool = False, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        await library.delete_character(db, character_id, force)
    await library.remove_character_files(character_id)
    return ok({"deleted": character_id})


async def _enqueue(db: aiosqlite.Connection, kind: str, target_id: str, payload: dict | None = None) -> dict:
    require_generation()
    async with write_transaction(db):
        job = await jobs.create_job(db, kind, target_id, payload)
    from app.main import image_job_runner  # lifespan singleton; avoid router import cycle

    image_job_runner.wake()
    return ok(job)


@router.post("/characters/{character_id}/candidates")
async def generate_candidates(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        character = await library.get_character_row(db, character_id)
    if character["status"] == "locked":
        raise ConflictError("Unlock the character before generating candidates")
    return await _enqueue(db, "character_candidates", character_id)


@router.put("/characters/{character_id}/reference")
async def pick_reference(
    character_id: str, body: ReferenceInput, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        row = await library.pick_reference(db, character_id, body.asset_id)
    return ok(row)


@router.post("/characters/{character_id}/sheet")
async def generate_sheet(
    character_id: str, body: list[SheetItemInput] | None = None,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with read_transaction():
        character = await library.get_character_row(db, character_id)
    if character["status"] == "locked":
        raise ConflictError("Unlock the character before generating a sheet")
    if not character["reference_asset_id"]:
        raise ConflictError("Pick a candidate before generating a sheet")
    if body and len(body) != 1:
        raise ValidationError("Request all sheet assets or exactly one kind")
    return await _enqueue(db, "character_sheet", character_id, {"kind": body[0].kind} if body else {})


@router.put("/characters/{character_id}/assets/{asset_id}/approve")
async def approve_asset(
    character_id: str, asset_id: str, body: ApprovalInput, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        row = await library.approve_asset(db, character_id, asset_id, body.approved)
    return ok(row)


@router.post("/characters/{character_id}/lock")
async def lock_character(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await library.lock_character(db, character_id)
    return ok(row)


@router.post("/characters/{character_id}/unlock")
async def unlock_character(character_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await library.unlock_character(db, character_id)
    return ok(row)


@router.get("/assets/{asset_id}/content")
async def asset_content(asset_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        asset = await library.get_asset_row(db, asset_id)
    path = await asyncio.to_thread(library.resolve_library_content, asset["path"], "library/characters")
    return FileResponse(path, media_type="image/png")


@router.get("/scenes")
async def list_scenes(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        rows = await library.list_scenes(db)
    return ok(rows)


@router.post("/scenes")
async def create_scene(body: SceneInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await library.create_scene(db, body)
    return ok(row)


@router.patch("/scenes/{scene_id}")
async def edit_scene(
    scene_id: str, body: ScenePatch, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        row = await library.edit_scene(db, scene_id, body)
    return ok(row)


@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await library.delete_scene(db, scene_id)
    return ok({"deleted": scene_id})


@router.post("/scenes/{scene_id}/duplicate")
async def duplicate_scene(scene_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await library.duplicate_scene(db, scene_id)
    return ok(row)


@router.post("/scenes/{scene_id}/preview")
async def generate_scene_preview(scene_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        await library.get_scene_row(db, scene_id)
    return await _enqueue(db, "scene_preview", scene_id)


@router.get("/scenes/{scene_id}/preview")
async def scene_preview_content(scene_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        scene = await library.get_scene_row(db, scene_id)
    if not scene["preview_path"]:
        raise NotFoundError("Scene preview not found")
    path = await asyncio.to_thread(library.resolve_library_content, scene["preview_path"], "library/scenes")
    return FileResponse(path, media_type="image/png")


@router.get("/jobs/{job_id}")
async def get_image_job(job_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        job = await jobs.get_job(db, job_id)
    return ok(job)


@router.post("/jobs/{job_id}/cancel")
async def cancel_image_job(job_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        job = await jobs.request_cancel(db, job_id)
    return ok(job)


@router.get("/library/shots")
async def list_library_shots(
    scene_id: str | None = None, kind: str | None = None, review_state: str | None = None,
    character_id: str | None = None, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        await shot_library.refresh_stale(db)  # a regenerated character's shots show as stale
    async with read_transaction():
        rows = await shot_library.list_shots(db, scene_id, kind, review_state, character_id)
    return ok(rows)


@router.get("/library/activities")
async def list_library_activities(
    review_state: str | None = None, character_id: str | None = None, activity: str | None = None,
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with read_transaction():
        rows = await activity_library.list_activities(db, review_state, character_id, activity)
    return ok(rows)


@router.post("/library/activities/import")
async def import_library_activities(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await activity_library.import_inbox(db)
    return ok(result)


@router.post("/library/activities/upload", status_code=201)
async def upload_library_activity(
    file: UploadFile = File(...),
    activity: str = Form(...),
    character_id: str = Form(""),
    context_tags: str = Form(""),
    aliases: str = Form(""),
    variant: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Upload one activity picture directly; it always starts pending review."""
    metadata = ActivityMetadataInput(
        character_id=character_id or None,
        activity=activity,
        context_tags=_form_labels(context_tags),
        aliases=_form_labels(aliases),
        variant=variant,
    )
    async with write_transaction(db):
        row = await activity_library.upload_activity(db, file, metadata.model_dump())
    return ok(row)


@router.post("/library/activities/upload-batch", status_code=201)
async def upload_library_activities_batch(
    files: list[UploadFile] = File(...),
    metadata_json: str = Form(...),
    character_id: str = Form(""),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Add up to 20 pictures with one owner-entered activity name per file."""
    if not files or len(files) > 20:
        raise ValidationError("choose between 1 and 20 activity images")
    try:
        raw_metadata = json.loads(metadata_json)
    except (TypeError, ValueError) as exc:
        raise ValidationError("picture metadata must be a JSON list") from exc
    if not isinstance(raw_metadata, list) or len(raw_metadata) != len(files):
        raise ValidationError("provide one activity name for each picture")
    selected_character = character_id or None
    if selected_character:
        async with read_transaction():
            await library.get_character_row(db, selected_character)
    metadata_items = []
    for entry in raw_metadata:
        if not isinstance(entry, dict):
            raise ValidationError("each picture needs an activity name")
        if not isinstance(entry.get("activity"), str) or not entry["activity"].strip():
            raise ValidationError("each picture needs an activity name")
        try:
            metadata_items.append(ActivityMetadataInput.model_validate({
                "character_id": selected_character,
                "activity": entry.get("activity"),
                "context_tags": entry.get("context_tags", []),
                "aliases": entry.get("aliases", []),
            }))
        except PydanticValidationError as exc:
            raise ValidationError("each picture needs a valid activity name and optional tags/aliases") from exc

    items, rejected = [], []
    for file, metadata in zip(files, metadata_items):
        filename = file.filename or "activity.png"
        try:
            content = await activity_library.read_upload(file)
            async with write_transaction(db):
                variant = await activity_library.next_variant(db, selected_character, metadata.activity)
                row = await activity_library.upload_activity_bytes(
                    db, filename, content, {**metadata.model_dump(), "variant": variant},
                )
            items.append(row)
        except (ConflictError, ValidationError) as exc:
            rejected.append({"file": filename, "reason": str(exc)})
    return ok({"items": items, "rejected": rejected})


@router.post("/library/activities/approve-batch")
async def approve_library_activities_batch(
    body: ActivityApproveBatchInput, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Approve only the pending activity pictures explicitly selected in the UI."""
    async with write_transaction(db):
        approved = await activity_library.approve_pending_batch(db, body.ids)
    return ok({"approved": approved})


@router.get("/library/activities/{activity_id}/content")
async def activity_content(activity_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        path = await activity_library.content_path(db, activity_id)
    return FileResponse(path)


@router.patch("/library/activities/{activity_id}")
async def edit_library_activity(
    activity_id: str, body: ActivityMetadataPatch, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        row = await activity_library.update_metadata(activity_id=activity_id, db=db,
                                                     changes=body.model_dump(exclude_unset=True))
    return ok(row)


@router.delete("/library/activities/{activity_id}")
async def delete_library_activity(activity_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Delete one library image after its database removal commits."""
    async with write_transaction(db):
        path = await activity_library.delete_activity(db, activity_id)
    try:
        await asyncio.to_thread(path.unlink, missing_ok=True)
    except OSError as exc:
        logger.warning("activity_file_cleanup_failed activity_id=%s error=%s", activity_id, type(exc).__name__)
        return ok({"deleted": activity_id, "file_removed": False})
    return ok({"deleted": activity_id, "file_removed": True})


@router.patch("/library/activities/{activity_id}/review")
async def review_library_activity(
    activity_id: str, body: ActivityReviewInput, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        row = await activity_library.set_review(db, activity_id, body.review_state)
    return ok(row)


@router.get("/library/activities/{activity_id}/history")
async def activity_history(activity_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        return ok(await activity_library.history(db, activity_id))


@router.get("/library/backgrounds")
async def library_backgrounds() -> dict:
    return ok(shot_library.backgrounds_status())


@router.post("/library/backgrounds/import")
async def import_library_backgrounds(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await shot_library.import_backgrounds(db)
    return ok(result)


@router.get("/library/inbox")
async def library_inbox() -> dict:
    return ok({"folder": str(shot_library.inbox_dir()), "files": shot_library.list_inbox()})


@router.post("/library/inbox/import")
async def import_library_inbox(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        result = await shot_library.import_inbox(db)
    return ok(result)


@router.get("/library/sprites/{character_id}/{name}/content")
async def library_sprite_content(character_id: str, name: str) -> FileResponse:
    if name not in sprite_service.ALL_NAMES:
        raise NotFoundError("Sprite picture not found")
    path = sprite_service.sprite_dir(character_id) / f"{name}.png"
    if "/" in character_id or "\\" in character_id or ".." in character_id or not path.is_file():
        raise NotFoundError("Sprite picture not found")
    return FileResponse(path, media_type="image/png")


@router.patch("/library/shots/{shot_id}")
async def review_library_shot(shot_id: str, body: ShotReviewInput, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await shot_library.set_review(db, shot_id, body.review_state)
    return ok(row)


@router.delete("/library/shots/{shot_id}")
async def delete_library_shot(shot_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        await shot_library.delete_shot(db, shot_id)
    return ok({"deleted": shot_id})


@router.get("/library/shots/{shot_id}/content")
async def library_shot_content(shot_id: str, db: aiosqlite.Connection = Depends(get_db)) -> FileResponse:
    async with read_transaction():
        path = await shot_library.content_path(db, shot_id)
    return FileResponse(path, media_type="image/png")


@project_router.post("/shots/{shot_id}/to-library")
async def add_project_shot_to_library(project_id: str, shot_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with write_transaction(db):
        row = await shot_library.add_from_project_shot(db, project_id, shot_id)
    return ok(row)


@project_router.get("/library-coverage")
async def library_coverage(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        await project_service.get_project(db, project_id)
        result = await shot_library.coverage(db, project_id)
    return ok(result)


@project_router.get("/activity-coverage")
async def activity_coverage(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Explain selected/missing reusable activity illustrations before a talking-sprites render."""
    async with read_transaction():
        await project_service.get_project(db, project_id)
        beats = await storyboard_service.approved_beats(db, project_id) or []
        cursor = await db.execute(
            "SELECT sl.line_index, sl.text, sp.speaker_index FROM script_lines sl JOIN speakers sp ON sp.id = sl.speaker_id "
            "WHERE sl.project_id = ? ORDER BY sl.line_index", (project_id,),
        )
        lines = [dict(row) for row in await cursor.fetchall()]
        cast = {row["speaker_index"]: row["character_id"] for row in await project_visuals.cast_rows(db, project_id)}
        candidates = await activity_library.approved_candidates(db)
    items = []
    size = max((line["line_index"] for line in lines), default=-1) + 1
    line_speakers: list[int | None] = [None] * size
    line_texts = [""] * size
    for line in lines:
        line_speakers[line["line_index"]], line_texts[line["line_index"]] = line["speaker_index"], line["text"]
    for beat in beats:
        if beat["kind"] != "insert":
            continue
        speaker = activity_matcher.beat_speaker_index(beat, line_speakers, line_texts) if size else None
        character_id = cast.get(speaker) if speaker is not None else None
        dialogue = " ".join(line["text"] for line in lines if beat["line_from"] <= line["line_index"] <= beat["line_to"])
        found = activity_matcher.match_activity(candidates, character_id, beat.get("action") or "", dialogue)
        items.append({"beat_id": beat["id"], "position": beat["position"], "action": beat.get("action") or "",
                      "status": found["match_type"] if found else "missing",
                      "fallback": None if found else "sprites",
                      "suggestions": [] if found else activity_matcher.suggest(
                          candidates, f"{beat.get('action') or ''} {beat.get('new_place') or ''} {dialogue}"),
                      "match": {key: value for key, value in found.items() if key != "asset"} if found else None})
    character = sum(item["status"] == "character" for item in items)
    generic = sum(item["status"] == "generic" for item in items)
    missing = sum(item["status"] == "missing" for item in items)
    return ok({"items": items, "matched": character + generic, "character": character,
               "generic": generic, "missing": missing, "sprite_fallback": missing})


@project_router.get("")
async def get_project_visuals(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        result = await project_visuals.project_visuals(db, project_id)
    return ok(result)


@project_router.put("/cast")
async def set_project_cast(
    project_id: str, body: list[CastMemberInput], db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        result = await project_visuals.set_cast(db, project_id, [member.model_dump() for member in body])
    return ok(result)


@project_router.put("/scenes")
async def set_project_scenes(
    project_id: str, body: list[str], db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with write_transaction(db):
        result = await project_visuals.set_scenes(db, project_id, body)
    return ok(result)


@project_router.post("/shots")
async def generate_project_shots(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    async with read_transaction():
        await project_service.get_project(db, project_id)
        cast = await project_visuals.cast_rows(db, project_id)
        scenes = await project_visuals.scene_rows(db, project_id)
        storyboard_beats = await storyboard_service.approved_beats(db, project_id)
    if not cast:
        raise ValidationError("Assign at least one character before generating shots")
    if not scenes and storyboard_beats is None:  # Task 24.5a: an approved storyboard brings its own places
        raise ValidationError("Assign at least one character and one scene, or approve a storyboard, "
                              "before generating shots")
    return await _enqueue(db, "project_shots", project_id)


@project_router.post("/shots/{shot_id}/regenerate")
async def regenerate_project_shot(
    project_id: str, shot_id: str, db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    async with read_transaction():
        await project_visuals.get_shot_row(db, project_id, shot_id)
    return await _enqueue(db, "shot_regenerate", shot_id, {"project_id": project_id})


@project_router.get("/shots/{shot_id}/content")
async def project_shot_content(
    project_id: str, shot_id: str, variant: Literal["final", "raw"] = "final",
    db: aiosqlite.Connection = Depends(get_db),
) -> FileResponse:
    async with read_transaction():
        shot = await project_visuals.get_shot_row(db, project_id, shot_id)
    stored = shot[f"{variant}_path"]
    if not stored:
        raise NotFoundError("Shot image not found")
    path = await asyncio.to_thread(project_visuals.resolve_shot_content, project_id, stored)
    return FileResponse(path, media_type="image/png")
