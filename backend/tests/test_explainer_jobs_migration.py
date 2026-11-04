"""028 rebuild preserves durable jobs and their checkpoints, including after rollback/restart."""
import shutil
import sqlite3

import pytest

from backend.core.config import settings
from backend.db import database

SOURCE = database.MIGRATIONS_DIR
MIGRATION = "028_explainer_jobs_assets.sql"


@pytest.fixture
def migrations(tmp_path, monkeypatch):
    target = tmp_path / "migrations"
    target.mkdir()
    for path in SOURCE.glob("*.sql"):
        if path.name < "028":
            shutil.copyfile(path, target / path.name)
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(database, "MIGRATIONS_DIR", target)
    return target


async def seed(db):
    await db.execute("INSERT INTO projects(id,name,created_at,updated_at) VALUES('p','Old project','then','then')")
    for index, operation in enumerate(("script", "learning")):
        await db.execute("INSERT INTO ai_generation_jobs(id,project_id,operation,status,stage,input_snapshot_json,input_hash,"
                         "config_hash,pipeline_version,idempotency_key,created_at,updated_at) VALUES(?, 'p', ?, 'running',"
                         "'section_2','{\"old\":true}','hash','config','13.3',?,'then','now')",
                         (f"j{index}", operation, f"key{index}"))
        await db.execute("INSERT INTO ai_generation_checkpoints(id,job_id,section_index,stage,status,input_hash,result_json,"
                         "created_at,updated_at) VALUES(?,?,1,'section','valid','hash','{\"saved\":true}','then','now')",
                         (f"c{index}", f"j{index}"))
    await db.commit()


async def snapshots(db):
    return {table: [tuple(row) for row in await (await db.execute(f"SELECT * FROM {table} ORDER BY id")).fetchall()]
            for table in ("projects", "ai_generation_jobs", "ai_generation_checkpoints")}


@pytest.mark.parametrize("fail_first", [False, True])
async def test_populated_rebuild_is_atomic_preserves_children_and_restarts(migrations, fail_first):
    try:
        await database.init_db()
        db = database.Database.instance().connection
        await seed(db)
        before = await snapshots(db)
        sql = (SOURCE / MIGRATION).read_text(encoding="utf-8")
        if fail_first:
            # Failure after both old tables have been dropped and replacement tables renamed.
            (migrations / MIGRATION).write_text(sql.replace("CREATE TABLE project_explainer_assets", "INSERT INTO absent_table VALUES (1);\nCREATE TABLE project_explainer_assets"), encoding="utf-8")
            with pytest.raises(sqlite3.OperationalError, match="absent_table"):
                await database.init_db()
            assert await snapshots(db) == before
            assert not await (await db.execute("SELECT 1 FROM schema_migrations WHERE filename=?", (MIGRATION,))).fetchone()
            assert not await (await db.execute("PRAGMA foreign_key_check")).fetchall()
        (migrations / MIGRATION).write_text(sql, encoding="utf-8")
        await database.init_db()
        assert await snapshots(db) == before, "DROP parent must not cascade-delete the old child rows"
        await db.execute("UPDATE ai_generation_jobs SET operation='propose_explainer' WHERE id='j0'")
        with pytest.raises(sqlite3.IntegrityError):
            await db.execute("UPDATE ai_generation_jobs SET operation='unsupported' WHERE id='j1'")
        await db.commit()
        await database.close_db()
        await database.init_db()
        await database.init_db()
        db = database.Database.instance().connection
        assert len((await snapshots(db))["ai_generation_checkpoints"]) == 2
        assert (await (await db.execute("SELECT COUNT(*) FROM schema_migrations WHERE filename=?", (MIGRATION,))).fetchone())[0] == 1
        assert not await (await db.execute("PRAGMA foreign_key_check")).fetchall()
        await db.execute("DELETE FROM projects WHERE id='p'")
        assert not await (await db.execute("SELECT 1 FROM ai_generation_checkpoints")).fetchone()
        assert not await (await db.execute("SELECT 1 FROM ai_generation_jobs")).fetchone()
    finally:
        await database.close_db()
