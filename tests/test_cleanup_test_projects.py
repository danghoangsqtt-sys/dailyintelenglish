"""Tests for scripts/cleanup_test_projects.py, plus the real-DB guard installed
in tests/conftest.py (Task 16.3, BUG-023 -- both are this task's deliverables,
and this is the one new test file its card allows).

Runs entirely against a tmp, file-based SQLite database with real migrations
applied -- never the real data/app.db. `--db`/`--data-dir` exist on the script
specifically so its own tests can target a throwaway copy like this one.
"""

from pathlib import Path

import aiosqlite
import pytest

from app.models.project import ScriptConfig, SpeakerConfig
from app.services import project_service
from tests.conftest import MIGRATIONS_DIR

import scripts.cleanup_test_projects as cleanup


def _config(name: str) -> ScriptConfig:
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


async def _make_file_db(path: Path) -> aiosqlite.Connection:
    connection = await aiosqlite.connect(path)
    connection.row_factory = aiosqlite.Row
    await connection.execute("PRAGMA foreign_keys = ON")
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        await connection.executescript(migration_file.read_text(encoding="utf-8"))
    await connection.commit()
    return connection


async def _speaker_count(db_path: Path, project_id: str) -> int:
    db = await aiosqlite.connect(db_path)
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM speakers WHERE project_id = ?", (project_id,))
        return (await cursor.fetchone())[0]
    finally:
        await db.close()


async def _project_exists(db_path: Path, project_id: str) -> bool:
    db = await aiosqlite.connect(db_path)
    try:
        cursor = await db.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,))
        return await cursor.fetchone() is not None
    finally:
        await db.close()


async def _seed(db_path: Path, data_dir: Path) -> dict:
    """Seed a real project, a near-miss name, and the 4 fixture names, each with a
    per-project audio directory -- proving deletion is exact-name and that both
    cascaded DB rows and on-disk directories are cleaned up, only for real matches."""
    db = await _make_file_db(db_path)
    ids = {}
    try:
        real = await project_service.create_project(db, _config("A Real Customer Project"))
        ids["real"] = real["id"]
        near_miss = await project_service.create_project(db, _config("Learning API Test Episode 2"))
        ids["near_miss"] = near_miss["id"]
        for name in cleanup.FIXTURE_PROJECT_NAMES:
            project = await project_service.create_project(db, _config(name))
            ids[name] = project["id"]
        for project_id in ids.values():
            directory = data_dir / "audio" / project_id
            directory.mkdir(parents=True)
            (directory / "mix.mp3").write_bytes(b"data")
    finally:
        await db.close()
    return ids


async def test_dry_run_reports_counts_and_ids_and_writes_nothing(tmp_path):
    db_path = tmp_path / "app.db"
    data_dir = tmp_path
    ids = await _seed(db_path, data_dir)
    size_before = db_path.stat().st_size
    mtime_before = db_path.stat().st_mtime

    report = await cleanup.run(db_path, data_dir, apply=False)

    for name in cleanup.FIXTURE_PROJECT_NAMES:
        assert f"{name}: 1" in report
        assert ids[name] in report
    assert "A Real Customer Project" not in report
    assert "dry run" in report
    assert db_path.stat().st_size == size_before
    assert db_path.stat().st_mtime == mtime_before
    assert not (data_dir / "backups").exists()
    # Nothing was actually deleted.
    for project_id in ids.values():
        assert await _project_exists(db_path, project_id)


async def test_apply_deletes_only_exact_name_matches_backs_up_and_cascades(tmp_path):
    db_path = tmp_path / "app.db"
    data_dir = tmp_path
    ids = await _seed(db_path, data_dir)

    report = await cleanup.run(db_path, data_dir, apply=True)

    assert "apply complete" in report
    backups = list((data_dir / "backups").glob("app-before-cleanup-*.db"))
    assert len(backups) == 1
    assert backups[0].stat().st_size > 0

    for name in cleanup.FIXTURE_PROJECT_NAMES:
        project_id = ids[name]
        assert not await _project_exists(db_path, project_id)
        assert await _speaker_count(db_path, project_id) == 0
        assert not (data_dir / "audio" / project_id).exists()

    for key in ("real", "near_miss"):
        project_id = ids[key]
        assert await _project_exists(db_path, project_id)
        assert await _speaker_count(db_path, project_id) == 1
        assert (data_dir / "audio" / project_id).exists()


async def test_apply_backup_is_a_snapshot_of_the_pre_deletion_database(tmp_path):
    """The backup must reflect the database *before* deletion, not after."""
    db_path = tmp_path / "app.db"
    data_dir = tmp_path
    ids = await _seed(db_path, data_dir)

    await cleanup.run(db_path, data_dir, apply=True)

    backup_path = next((data_dir / "backups").glob("app-before-cleanup-*.db"))
    assert await _project_exists(backup_path, ids[cleanup.FIXTURE_PROJECT_NAMES[0]])


async def test_find_matches_is_exact_name_only(tmp_path):
    db_path = tmp_path / "app.db"
    db = await _make_file_db(db_path)
    try:
        near_miss = await project_service.create_project(db, _config("learning api test episode"))  # lowercase
        exact = await project_service.create_project(db, _config(cleanup.FIXTURE_PROJECT_NAMES[0]))
        matches = await cleanup.find_matches(db)
    finally:
        await db.close()

    assert matches[cleanup.FIXTURE_PROJECT_NAMES[0]] == [exact["id"]]
    assert near_miss["id"] not in [pid for ids in matches.values() for pid in ids]


def test_default_db_path_and_data_dir_come_from_settings(monkeypatch, tmp_path):
    """Confirms the script's defaults are the real, configured settings -- callers
    (tests, the PM) must pass --db/--data-dir explicitly to target anything else,
    which is exactly what every other test in this file does."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    assert cleanup._default_data_dir() == tmp_path
    assert cleanup._default_db_path() == tmp_path / "app.db"


def test_cli_requires_no_flags_to_dry_run_and_apply_is_opt_in():
    args = cleanup.build_parser().parse_args([])
    assert args.apply is False
    assert args.db is None
    assert args.data_dir is None

    args = cleanup.build_parser().parse_args(["--apply"])
    assert args.apply is True


def test_main_cli_wiring_runs_a_dry_run_against_explicit_paths(tmp_path, capsys):
    """Sync test: `main()` calls `asyncio.run()` itself, which cannot be called
    from inside an already-running event loop (i.e. from within an async test)."""
    import asyncio

    db_path = tmp_path / "app.db"
    data_dir = tmp_path
    asyncio.run(_seed(db_path, data_dir))

    cleanup.main(["--db", str(db_path), "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert "dry run" in captured.out
    assert not (data_dir / "backups").exists()


# --- Task 16.3's other deliverable: the real-DB guard in tests/conftest.py ----------
#
# Both tests below use a *fresh* `Database()` instance, never
# `Database.instance()` -- the process-wide singleton every other test in the
# suite (via the `client` fixture) also relies on. Mutating the singleton's
# connection state here would be order-dependent and could break unrelated
# tests; a fresh instance exercises the exact same guarded `connect()` method
# (the guard patches the class, not one instance) in complete isolation.


async def test_database_connect_guard_rejects_the_real_db_path(monkeypatch):
    """Check (a): a connection attempt straight against the literal real
    data/app.db is rejected before it's ever opened -- the original `connect()`
    body (and so the real file) is never reached."""
    from app.core.config import settings
    from app.db.database import Database
    from tests.conftest import _REAL_DB_PATH

    monkeypatch.setattr(settings, "DATA_DIR", _REAL_DB_PATH.parent)
    db = Database()
    with pytest.raises(RuntimeError, match="tried to open the real database"):
        await db.connect()


async def test_database_connect_guard_rejects_stale_reuse_against_a_different_data_dir(tmp_path, monkeypatch):
    """Check (b), BUG-023's actual leak mechanism: a second `connect()` call
    that would otherwise silently reuse an already-open connection is rejected
    once `settings.DATA_DIR` no longer matches the path that connection was
    actually opened against."""
    from app.core.config import settings
    from app.db.database import Database

    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    db = Database()
    monkeypatch.setattr(settings, "DATA_DIR", dir_a)
    await db.connect()
    try:
        monkeypatch.setattr(settings, "DATA_DIR", dir_b)
        with pytest.raises(RuntimeError, match="reusing a connection opened against"):
            await db.connect()
    finally:
        await db.close()
