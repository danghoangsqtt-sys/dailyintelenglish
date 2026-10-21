"""Project management routes."""

import time

import aiosqlite
from fastapi import APIRouter, Depends

from backend.core.responses import ok
from backend.core.exceptions import ConflictError, NotFoundError, ValidationError
from backend.core.voice import profile_voice_settings, resolve_voice_id, voice_revision
from backend.ai.tts import voice_catalog_service
from backend.db.database import get_db
from backend.db.transactions import read_transaction, write_transaction
from backend.schemas.project import ProjectUpdate, ScriptConfig, SpeakerUpdate
from backend.schemas.script import RegenerateLineRequest, ScriptUpdate
from backend.channel import dashboard_service
from backend.content import export_service, project_service, script_service

router = APIRouter(prefix="/api/projects", tags=["projects"])

# The shared connection-wide write lock/transaction helpers live in
# backend/db/transactions.py (Task 13.3) -- moved out of this router since 7 other
# routers and backend/ai/llm/ai_worker.py all need them too, and importing them
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
    for speaker in config.speakers:
        if speaker.voice_id:
            await voice_catalog_service.require_voice(speaker.voice_id)
    async with write_transaction(db):
        project = await project_service.create_project(db, config, commit=False)
    return ok(project, started_at=started_at)


@router.post("/{project_id}/copy-settings")
async def copy_project_settings(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Start a new draft from pinned configuration without copying media or approvals."""
    async with write_transaction(db):
        project = await project_service.copy_settings(db, project_id)
    return ok(project)


@router.get("/{project_id}")
async def get_project(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch full project detail, including speakers."""
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
    return ok(project, started_at=started_at)


@router.get("/{project_id}/progress")
async def get_project_progress(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Phase 56 (ENH-038): which of the seven steps the project has done, for the step pages' next-step bar."""
    async with read_transaction():
        progress = await dashboard_service.project_progress(db, project_id)
    if progress is None:
        raise NotFoundError(f"Project {project_id} not found")
    return ok(progress)


@router.put("/{project_id}")
async def update_project(
    project_id: str, patch: ProjectUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Apply a partial update to a project — also used as the auto-save endpoint."""
    started_at = time.perf_counter()
    for speaker in patch.speakers or []:
        if speaker.voice_id:
            await voice_catalog_service.require_voice(speaker.voice_id)
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
    async with read_transaction():
        snapshot = await project_service.get_project(db, project_id)
        speaker = next((s for s in snapshot["speakers"] if s["id"] == speaker_id), None)
        if speaker is None:
            raise NotFoundError("Speaker not found in this project.")
        expected = patch.expected_voice_revision or speaker["voice_revision"]
        profile_id, profile_revision, profile_row = None, None, None
        if patch.apply_profile_voice:
            cursor = await db.execute(
                "SELECT c.* FROM project_cast pc JOIN characters c ON c.id = pc.character_id "
                "WHERE pc.project_id = ? AND pc.speaker_index = ?", (project_id, speaker["speaker_index"]),
            )
            row = await cursor.fetchone()
            if row is None:
                raise ValidationError("Choose a character for this speaker before applying its profile voice.")
            profile_row = dict(row)
            profile_id = profile_row["id"]
            profile_revision = voice_revision(profile_voice_settings(profile_row))
    fields = patch.model_dump(exclude_unset=True, exclude_none=True,
                              exclude={"expected_voice_revision", "apply_profile_voice", "name"})
    if patch.apply_profile_voice:
        if patch.voice_id is not None:
            raise ValidationError("Choose either a project voice or apply the profile voice.")
        fields["voice_id"] = profile_row.get("default_voice_id") or resolve_voice_id(profile_voice_settings(profile_row))
        fields["tts_engine"] = "edge_tts"
    if fields.get("voice_id"):
        await voice_catalog_service.require_voice(fields["voice_id"])  # network outside shared transaction
    rename = None
    async with write_transaction(db):
        current = await project_service.get_project(db, project_id)
        actual = next((s for s in current["speakers"] if s["id"] == speaker_id), None)
        if actual is None or actual["voice_revision"] != expected:
            raise ConflictError("Speaker voice settings changed. Reload before applying this selection.")
        if profile_id:
            cursor = await db.execute("SELECT * FROM characters WHERE id = ?", (profile_id,))
            row = await cursor.fetchone()
            if row is None or voice_revision(profile_voice_settings(dict(row))) != profile_revision:
                raise ConflictError("The character profile voice changed. Reload before applying it.")
            cursor = await db.execute(
                "SELECT character_id FROM project_cast WHERE project_id = ? AND speaker_index = ?",
                (project_id, actual["speaker_index"]),
            )
            cast = await cursor.fetchone()
            if cast is None or cast["character_id"] != profile_id:
                raise ConflictError("The speaker's character changed. Reload before applying its voice.")
        if patch.name is not None:
            rename = await project_service.rename_speaker(db, project_id, speaker_id, patch.name, commit=False)
        changed = any(value != actual.get(key) for key, value in fields.items())
        if changed:
            await project_service.mark_speaker_voice_changed(db, project_id, commit=False, speaker_id=speaker_id)
        project = await project_service.update_speaker(
            db, project_id, speaker_id, SpeakerUpdate(**fields), commit=False)
    if rename and rename["changed"]:
        await export_service.sync_quietly(db, project_id)
    return ok({**project, "renamed": rename} if rename else project, started_at=started_at)


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


@router.post("/{project_id}/script/generate", deprecated=True)
async def generate_script(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Generate a full script for a project and persist it (synchronous, one request).

    Deprecated (Phase 13, Task 13.7): kept for one compatibility release with an
    unchanged response contract. The durable-job path (`POST
    /api/projects/{project_id}/ai-jobs` with `operation: "script"`, Task 13.3+) is the
    production route -- it survives browser navigation/restart and does not hold one
    HTTP request open for the whole generation.
    """
    started_at = time.perf_counter()
    async with read_transaction():
        project = await project_service.get_project(db, project_id)
    lines = await script_service.generate_script(project_id, project)  # no lock held — provider gateway call
    saved = await _save_script_and_advance(
        db, project_id, project, [line.model_dump() for line in lines]
    )
    await export_service.sync_quietly(db, project_id)
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
    new_line = await script_service.regenerate_line(  # no lock held — provider gateway call
        project_id, project, payload.line_id, current_line["text"], current_line["speaker_id"]
    )
    async with write_transaction(db):
        updated = await script_service.update_script_line(
            db, project_id, payload.line_id, new_line.text, new_line.language_notes.model_dump(),
            commit=False,
        )
        await _sync_status_after_script_change(db, project_id)
    await export_service.sync_quietly(db, project_id)
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
    await export_service.sync_quietly(db, project_id)
    return ok(saved, started_at=started_at)
