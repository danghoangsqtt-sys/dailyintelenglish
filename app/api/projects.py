"""Project management routes."""

import time

import aiosqlite
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.core.responses import ok
from app.db.database import get_db
from app.db.transactions import read_transaction, write_transaction
from app.models.project import ProjectUpdate, ScriptConfig, SpeakerUpdate
from app.models.script import RegenerateLineRequest, ScriptUpdate
from app.services import avatar_service, project_service, script_service
from app.services.avatar_service import AVATAR_MEDIA_TYPES

router = APIRouter(prefix="/api/projects", tags=["projects"])

# The shared connection-wide write lock/transaction helpers live in
# app/db/transactions.py (Task 13.3) -- moved out of this router since 7 other
# routers and app/services/ai_worker.py all need them too, and importing them
# from another router (as every one of those files used to) was the wrong shape.


async def _sync_status_after_script_change(
    db: aiosqlite.Connection, project_id: str
) -> None:
    """Set the truthful project status after a script mutation.

    Always called from inside a `write_transaction` block, so it never commits itself.
    """
    await project_service.mark_script_changed(db, project_id, commit=False)


async def _save_script_and_advance(
    db: aiosqlite.Connection,
    project_id: str,
    project: dict,
    lines: list[dict],
    known_speaker_ids=None,
) -> list[dict]:
    """Persist script lines and synchronize status in one write transaction.

    The legacy name and `project` argument remain because the write-lock regression
    suite exercises this transaction helper directly. Status synchronization itself
    always re-reads the live row; it never trusts the pre-Gemini project snapshot.
    """
    async with write_transaction(db):
        saved = await script_service.save_script(
            db, project_id, lines, known_speaker_ids, commit=False
        )
        await _sync_status_after_script_change(db, project_id)
    return saved


@router.get("")
async def list_projects(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """List all projects for the dashboard grid."""
    started_at = time.perf_counter()
    async with read_transaction():
        projects = await project_service.list_projects(db)
    return ok(projects, started_at=started_at)


@router.post("")
async def create_project(
    config: ScriptConfig, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Create a new project from the Step 1 wizard config."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        project = await project_service.create_project(db, config, commit=False)
    return ok(project, started_at=started_at)


@router.get("/{project_id}")
async def get_project(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch full project detail, including speakers."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
    return ok(project, started_at=started_at)


@router.put("/{project_id}")
async def update_project(
    project_id: str, patch: ProjectUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Apply a partial update to a project — also used as the auto-save endpoint."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        project = await project_service.update_project(db, project_id, patch, commit=False)
    return ok(project, started_at=started_at)


@router.patch("/{project_id}/speakers/{speaker_id}")
async def update_speaker(
    project_id: str, speaker_id: str, patch: SpeakerUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Update one speaker's TTS engine/speed/pitch/volume in place (Step 4 Audio Studio).

    Deliberately separate from `PUT /{project_id}` — see SpeakerUpdate's docstring for why
    the full-replace `speakers` path on that route is unsafe to reuse here.
    """
    started_at = time.perf_counter()
    async with write_transaction(db):
        if patch.model_dump(exclude_unset=True):
            await project_service.mark_speaker_voice_changed(db, project_id, commit=False)
        project = await project_service.update_speaker(db, project_id, speaker_id, patch, commit=False)
    return ok(project, started_at=started_at)


@router.post("/{project_id}/speakers/{speaker_id}/avatar")
async def upload_speaker_avatar(
    project_id: str,
    speaker_id: str,
    file: UploadFile = File(...),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """Upload (or replace) one speaker's avatar image (Task 1.7c — upload only, no lip-sync).

    The previous avatar file (if any) is only deleted after this block's commit has
    durably succeeded — see `avatar_service.cleanup_previous_avatar_file` for why.
    """
    started_at = time.perf_counter()
    async with write_transaction(db):
        project, previous_avatar_path = await avatar_service.upload_avatar(
            db, project_id, speaker_id, file, commit=False
        )
    await avatar_service.cleanup_previous_avatar_file(previous_avatar_path)
    return ok(project, started_at=started_at)


@router.get("/{project_id}/speakers/{speaker_id}/avatar")
async def get_speaker_avatar(
    project_id: str, speaker_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> FileResponse:
    """Serve one speaker's stored avatar image."""
    async with read_transaction():
        path = await avatar_service.resolve_avatar_path(db, project_id, speaker_id)
    return FileResponse(path, media_type=AVATAR_MEDIA_TYPES[path.suffix.lower()])


@router.delete("/{project_id}/speakers/{speaker_id}/avatar")
async def delete_speaker_avatar(
    project_id: str, speaker_id: str, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Remove one speaker's avatar image.

    The file itself is only deleted after this block's commit has durably
    succeeded — see `avatar_service.delete_avatar`'s docstring for why.
    """
    started_at = time.perf_counter()
    async with write_transaction(db):
        project, files_to_remove = await avatar_service.delete_avatar(db, project_id, speaker_id, commit=False)
    for path in files_to_remove:
        await avatar_service.cleanup_previous_avatar_file(str(path))
    return ok(project, started_at=started_at)


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Delete a project."""
    started_at = time.perf_counter()
    async with write_transaction(db):
        await project_service.delete_project(db, project_id, commit=False)
    # Only after the transaction above has durably committed -- filesystem cleanup is
    # best-effort and must never run before the DB delete is confirmed (see
    # cleanup_project_artifacts docstring).
    await project_service.cleanup_project_artifacts(project_id)
    return ok(None, started_at=started_at)


@router.get("/{project_id}/script")
async def get_script(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch the current script for a project (empty list if not generated yet)."""
    started_at = time.perf_counter()
    async with read_transaction():
        await project_service.get_project(db, project_id)
        lines = await script_service.get_script(db, project_id)
    return ok(lines, started_at=started_at)


@router.post("/{project_id}/script/generate")
async def generate_script(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Generate a full script for a project via Gemini and persist it."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
    lines = await script_service.generate_script(project_id, project)  # no lock held — Gemini call
    saved = await _save_script_and_advance(
        db, project_id, project, [line.model_dump() for line in lines]
    )
    return ok(saved, started_at=started_at)


@router.post("/{project_id}/script/regenerate")
async def regenerate_script_line(
    project_id: str, payload: RegenerateLineRequest, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Regenerate a single script line via Gemini, keeping its speaker and position."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
        current_line = await script_service.get_script_line(db, project_id, payload.line_id)
    new_line = await script_service.regenerate_line(  # no lock held — Gemini call
        project_id, project, payload.line_id, current_line["text"], current_line["speaker_id"]
    )
    async with write_transaction(db):
        updated = await script_service.update_script_line(
            db, project_id, payload.line_id, new_line.text, new_line.language_notes.model_dump(),
            commit=False,
        )
        await _sync_status_after_script_change(db, project_id)
    return ok(updated, started_at=started_at)


@router.put("/{project_id}/script")
async def save_script(
    project_id: str, payload: ScriptUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Save a user-edited script, replacing the project's current lines."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
    known_speaker_ids = {speaker["id"] for speaker in project["speakers"]}
    saved = await _save_script_and_advance(
        db,
        project_id,
        project,
        [line.model_dump() for line in payload.lines],
        known_speaker_ids,
    )
    return ok(saved, started_at=started_at)
