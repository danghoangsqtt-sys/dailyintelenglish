"""Migration/schema tests for ai_generation_jobs / ai_generation_checkpoints."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import pytest

from app.models.project import ScriptConfig, SpeakerConfig
from app.services import project_service

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "db" / "migrations"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_config(name: str) -> ScriptConfig:
    return ScriptConfig(
        name=name,
        topic="t",
        cefr_level="B1",
        duration_minutes=5.0,
        num_speakers=1,
        genre="interview",
        accent="american",
        speakers=[SpeakerConfig(name="Alex", gender="male", accent="american")],
    )


async def _insert_job(db: aiosqlite.Connection, project_id: str, **overrides) -> str:
    job_id = str(uuid.uuid4())
    row = {
        "id": job_id,
        "project_id": project_id,
        "operation": "script",
        "status": "pending",
        "stage": "queued",
        "progress": 0,
        "input_snapshot_json": "{}",
        "input_hash": "hash1",
        "config_hash": "hash1",
        "pipeline_version": "test",
        "idempotency_key": str(uuid.uuid4()),
        "created_at": _now(),
        "updated_at": _now(),
    }
    row.update(overrides)
    columns = ", ".join(row.keys())
    placeholders = ", ".join(f":{key}" for key in row)
    await db.execute(
        f"INSERT INTO ai_generation_jobs ({columns}) VALUES ({placeholders})", row
    )
    await db.commit()
    return job_id


async def test_migration_applies_cleanly_on_a_fresh_database():
    """A brand-new in-memory DB applies every migration file (including 006)
    without error -- the same code path a fresh install goes through."""
    connection = await aiosqlite.connect(":memory:")
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON")
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        await connection.executescript(migration_file.read_text(encoding="utf-8"))
    await connection.commit()

    cursor = await connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN "
        "('ai_generation_jobs', 'ai_generation_checkpoints')"
    )
    names = {row["name"] for row in await cursor.fetchall()}
    assert names == {"ai_generation_jobs", "ai_generation_checkpoints"}
    await connection.close()


async def test_migration_is_idempotent_via_init_db_double_apply(tmp_path, monkeypatch):
    """The real app.db.database.init_db() tracks applied migrations by filename in
    schema_migrations -- running it twice against the same real file must not
    re-execute 006 a second time (which would otherwise hit real UNIQUE/CHECK
    constraint machinery harmlessly, but the point is it must not error or
    duplicate rows either way)."""
    from app.core.config import settings
    from app.db import database

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    database.Database._instance = None

    await database.init_db()
    await database.init_db()  # second call: every file already recorded, must be a no-op

    connection = database.Database.instance().connection
    cursor = await connection.execute("SELECT COUNT(*) FROM ai_generation_jobs")
    (count,) = await cursor.fetchone()
    assert count == 0
    cursor = await connection.execute(
        "SELECT COUNT(*) FROM schema_migrations WHERE filename = '006_ai_generation_jobs.sql'"
    )
    (applied_count,) = await cursor.fetchone()
    assert applied_count == 1  # recorded exactly once despite two init_db() calls
    await database.close_db()
    database.Database._instance = None


async def test_partial_unique_index_blocks_a_second_active_job(db):
    """The (project_id, operation) WHERE status IN (...) partial unique index is
    what makes 'one active job per project+operation' a real DB-level guarantee,
    not just an application-level convention."""
    project = await project_service.create_project(
        db,
        make_config("P"),
    )
    await _insert_job(db, project["id"], operation="script", status="pending")
    with pytest.raises(aiosqlite.IntegrityError):
        await _insert_job(db, project["id"], operation="script", status="running")


async def test_partial_unique_index_allows_a_new_job_once_the_old_one_is_terminal(db):
    """A job that reaches a terminal status frees the project+operation slot for a
    genuinely new one -- the partial index only ever covers active statuses."""
    project = await project_service.create_project(
        db,
        make_config("P2"),
    )
    await _insert_job(db, project["id"], operation="script", status="complete")
    # must not raise -- the terminal job above isn't covered by the partial index
    await _insert_job(db, project["id"], operation="script", status="pending")


async def test_idempotency_unique_index_blocks_a_duplicate_key(db):
    project = await project_service.create_project(
        db,
        make_config("P3"),
    )
    await _insert_job(db, project["id"], operation="script", status="complete", idempotency_key="dup-key")
    with pytest.raises(aiosqlite.IntegrityError):
        await _insert_job(db, project["id"], operation="script", status="error", idempotency_key="dup-key")


async def test_check_constraints_reject_invalid_status_and_operation(db):
    project = await project_service.create_project(
        db,
        make_config("P4"),
    )
    with pytest.raises(aiosqlite.IntegrityError):
        await _insert_job(db, project["id"], operation="not_a_real_operation")
    with pytest.raises(aiosqlite.IntegrityError):
        await _insert_job(db, project["id"], status="not_a_real_status")


async def test_cascade_delete_removes_jobs_and_checkpoints(db):
    project = await project_service.create_project(
        db,
        make_config("P5"),
    )
    job_id = await _insert_job(db, project["id"])
    await db.execute(
        "INSERT INTO ai_generation_checkpoints "
        "(id, job_id, section_index, stage, status, input_hash, created_at, updated_at) "
        "VALUES (?, ?, 1, 'outline', 'valid', 'h', ?, ?)",
        (str(uuid.uuid4()), job_id, _now(), _now()),
    )
    await db.commit()

    await db.execute("DELETE FROM projects WHERE id = ?", (project["id"],))
    await db.commit()

    cursor = await db.execute("SELECT COUNT(*) FROM ai_generation_jobs WHERE id = ?", (job_id,))
    (job_count,) = await cursor.fetchone()
    assert job_count == 0
    cursor = await db.execute(
        "SELECT COUNT(*) FROM ai_generation_checkpoints WHERE job_id = ?", (job_id,)
    )
    (checkpoint_count,) = await cursor.fetchone()
    assert checkpoint_count == 0
