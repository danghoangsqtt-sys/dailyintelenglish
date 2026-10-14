"""Phase 20.3 migration, prompt, geometry, image engine and job guarantees."""

import asyncio

import aiosqlite
import pytest

from backend.core.config import settings
from backend.core.exceptions import GpuUnavailableError
from backend.db.database import Database, MIGRATIONS_DIR, init_db
from backend.db.transactions import write_transaction
from backend.ai.image import jobs
from backend.ai.image.runner import ImageJobRunner

CHARACTER = {
    "age_group": "middle-aged", "ethnicity": "Vietnamese", "gender": "female",
    "role": "English teacher", "hair": "long wavy black hair", "eyes": "brown eyes",
    "top_color": "light blue", "top_item": "slim-fit shirt",
    "bottom_color": "navy blue", "bottom_item": "slim trousers",
}
SCENE = {"place": "a cozy Vietnamese street cafe", "staging": "seated"}


@pytest.fixture(autouse=True)
def fake_image_engine(monkeypatch):
    monkeypatch.setattr(settings, "IMAGE_ENGINE", "fake")


@pytest.mark.asyncio
@pytest.mark.parametrize("preexisting", [False, True])
async def test_migration_008_and_builtin_seed_once(tmp_path, monkeypatch, preexisting):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    if preexisting:
        connection = await aiosqlite.connect(tmp_path / "app.db")
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration.name.startswith("008"):
                break
            await connection.executescript(migration.read_text(encoding="utf-8"))
        await connection.close()
    old = Database._instance
    Database._instance = None
    try:
        await init_db()
        await init_db()
        db = Database.instance().connection
        cursor = await db.execute("SELECT count(*) FROM scenes WHERE is_builtin = 1")
        assert (await cursor.fetchone())[0] == 55
        cursor = await db.execute("SELECT count(*) FROM schema_migrations WHERE filename = '008_ai_visuals.sql'")
        assert (await cursor.fetchone())[0] == 1
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'image_jobs'")
        assert (await cursor.fetchone())[0] == "image_jobs"
    finally:
        await Database.instance().close()
        Database._instance = old


@pytest.mark.asyncio
async def test_jobs_fifo_duplicate_cancel_recovery(db):
    async with write_transaction(db):
        first = await jobs.create_job(db, "character_candidates", "one")
        duplicate = await jobs.create_job(db, "character_candidates", "one")
        second = await jobs.create_job(db, "scene_preview", "two")
        claimed = await jobs.claim_next(db)
    assert duplicate["id"] == first["id"]
    assert claimed["id"] == first["id"]
    async with write_transaction(db):
        await jobs.request_cancel(db, second["id"])
        assert (await jobs.get_job(db, second["id"]))["status"] == "cancelled"
        assert await jobs.recover_running(db) == 1
    assert (await jobs.get_job(db, first["id"]))["error"] == "interrupted by app restart"


@pytest.mark.asyncio
async def test_runner_cancels_at_boundary_and_gpu_error(db):
    def monkey_db():
        return db
    runner = ImageJobRunner(monkey_db, poll_seconds=0.01)
    events = []

    async def handler(job, active_runner):
        events.append(job["id"])
        if job["target_id"] == "gpu":
            raise GpuUnavailableError("image", "no_nvidia_gpu")
        async with write_transaction(db):
            await jobs.request_cancel(db, job["id"])
        await active_runner.boundary(job["id"], "next image", 50)

    runner.register_handler("project_shots", handler)
    async with write_transaction(db):
        cancel_job = await jobs.create_job(db, "project_shots", "cancel")
        gpu_job = await jobs.create_job(db, "project_shots", "gpu")
    await runner.start()
    try:
        for _ in range(100):
            await asyncio.sleep(0.01)
            if (await jobs.get_job(db, gpu_job["id"]))["status"] == "error":
                break
        assert (await jobs.get_job(db, cancel_job["id"]))["status"] == "cancelled"
        assert "no_nvidia_gpu" in (await jobs.get_job(db, gpu_job["id"]))["error"]
        assert len(events) == 2
    finally:
        await runner.stop()
