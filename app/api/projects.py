"""Project management routes."""

import time
from asyncio import Lock
from contextlib import asynccontextmanager

import aiosqlite
from fastapi import APIRouter, Depends

from app.core.responses import ok
from app.db.database import get_db
from app.models.project import ProjectUpdate, ScriptConfig, SpeakerUpdate
from app.models.script import RegenerateLineRequest, ScriptUpdate
from app.services import project_service, script_service

router = APIRouter(prefix="/api/projects", tags=["projects"])

# The whole app shares one aiosqlite connection (app.db.database.Database), which has
# exactly one implicit transaction active at a time — SQLite doesn't support nested
# transactions on a single connection. Without a lock, two concurrent requests can
# interleave their statements inside that one shared transaction: a rollback
# triggered by one write wipes out *both* requests' uncommitted work, and a plain
# read running alongside an uncommitted write sees that write's data early (a dirty
# read) and — if the write then rolls back — data that never really existed (a
# phantom read). So every route that touches `db` below, reads included, serializes
# on this single connection-wide lock — never a per-project lock, which only
# protects same-project races and leaves this cross-request corruption open.
#
# The lock is never held across a Gemini call: those are slow (network + retries),
# and holding a connection-wide lock across one would stall every other request —
# even an unrelated dashboard GET — for the duration. So generate/regenerate first
# take a short `_read_transaction` to snapshot what they need, call Gemini with no
# lock held, then take a separate `_write_transaction` to persist the result.
_write_lock = Lock()


@asynccontextmanager
async def _read_transaction():
    """Serialize one read-only section against the shared connection.

    Guarantees a read never observes another request's not-yet-committed write
    (a dirty read), and never observes a write that later rolls back (a phantom
    read) — the read simply waits its turn behind whichever write holds the lock.
    """
    async with _write_lock:
        yield


@asynccontextmanager
async def _write_transaction(db: aiosqlite.Connection):
    """Serialize one write transaction on the shared connection.

    The commit itself runs inside the try, so a commit failure (not just a
    failure in the wrapped writes) also triggers a rollback rather than
    leaving the connection in a half-committed, unknown state.

    Note for tests: asyncio.Lock binds to whichever event loop first calls
    acquire() on it. Since the app has exactly one event loop for its whole
    lifetime, that's a non-issue in production — but a test runner that hands
    each test its own loop needs `_write_lock` reset between tests (see the
    autouse `_reset_write_lock` fixture in tests/conftest.py), or the second
    test to touch it fails with "bound to a different event loop".
    """
    async with _write_lock:
        try:
            yield
            await db.commit()
        except Exception:
            await db.rollback()
            raise


async def _advance_to_script_generated(
    db: aiosqlite.Connection, project_id: str, project: dict
) -> None:
    """Move a draft project to script_generated once it has a persisted script.

    Always called from inside a `_write_transaction` block, so it never commits itself.
    """
    if project["status"] == "draft":
        await project_service.update_project(
            db, project_id, ProjectUpdate(status="script_generated"), commit=False
        )


async def _save_script_and_advance(
    db: aiosqlite.Connection, project_id: str, project: dict, lines: list[dict], known_speaker_ids=None
) -> list[dict]:
    """Persist script lines and advance status in one write transaction."""
    async with _write_transaction(db):
        saved = await script_service.save_script(
            db, project_id, lines, known_speaker_ids, commit=False
        )
        await _advance_to_script_generated(db, project_id, project)
    return saved


@router.get("")
async def list_projects(db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """List all projects for the dashboard grid."""
    started_at = time.perf_counter()
    async with _read_transaction():
        projects = await project_service.list_projects(db)
    return ok(projects, started_at=started_at)


@router.post("")
async def create_project(
    config: ScriptConfig, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Create a new project from the Step 1 wizard config."""
    started_at = time.perf_counter()
    async with _write_transaction(db):
        project = await project_service.create_project(db, config, commit=False)
    return ok(project, started_at=started_at)


@router.get("/{project_id}")
async def get_project(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch full project detail, including speakers."""
    started_at = time.perf_counter()
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
    return ok(project, started_at=started_at)


@router.put("/{project_id}")
async def update_project(
    project_id: str, patch: ProjectUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Apply a partial update to a project — also used as the auto-save endpoint."""
    started_at = time.perf_counter()
    async with _write_transaction(db):
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
    async with _write_transaction(db):
        project = await project_service.update_speaker(db, project_id, speaker_id, patch, commit=False)
    return ok(project, started_at=started_at)


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Delete a project."""
    started_at = time.perf_counter()
    async with _write_transaction(db):
        await project_service.delete_project(db, project_id, commit=False)
    return ok(None, started_at=started_at)


@router.get("/{project_id}/script")
async def get_script(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Fetch the current script for a project (empty list if not generated yet)."""
    started_at = time.perf_counter()
    async with _read_transaction():
        await project_service.get_project(db, project_id)
        lines = await script_service.get_script(db, project_id)
    return ok(lines, started_at=started_at)


@router.post("/{project_id}/script/generate")
async def generate_script(project_id: str, db: aiosqlite.Connection = Depends(get_db)) -> dict:
    """Generate a full script for a project via Gemini and persist it."""
    started_at = time.perf_counter()
    async with _read_transaction():
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
    async with _read_transaction():
        project = await project_service.get_project(db, project_id)
        current_line = await script_service.get_script_line(db, project_id, payload.line_id)
    new_line = await script_service.regenerate_line(  # no lock held — Gemini call
        project_id, project, payload.line_id, current_line["text"], current_line["speaker_id"]
    )
    async with _write_transaction(db):
        updated = await script_service.update_script_line(
            db, project_id, payload.line_id, new_line.text, new_line.language_notes.model_dump(),
            commit=False,
        )
    return ok(updated, started_at=started_at)


@router.put("/{project_id}/script")
async def save_script(
    project_id: str, payload: ScriptUpdate, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    """Save a user-edited script, replacing the project's current lines."""
    started_at = time.perf_counter()
    async with _read_transaction():
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
