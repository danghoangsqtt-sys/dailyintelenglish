"""Desktop upgrades retain committed WAL edits and refuse unfinished work."""

import sqlite3

import pytest

from scripts.desktop_upgrade import backup_database


def test_backup_includes_committed_wal_and_leaves_live_database_untouched(tmp_path):
    source = tmp_path / "app.db"
    with sqlite3.connect(source) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("CREATE TABLE characters(id TEXT PRIMARY KEY, name TEXT)")
        live.execute("INSERT INTO characters VALUES ('old-profile', 'Hoang')")
        live.commit()
        before = source.read_bytes()
        target = tmp_path / "backup.db"
        assert backup_database(source, target) == {"characters": 1}
        assert source.read_bytes() == before
        with sqlite3.connect(target) as restored:
            assert restored.execute("SELECT * FROM characters").fetchall() == [("old-profile", "Hoang")]
            assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)


@pytest.mark.parametrize("status", ["pending", "running", "validating", "processing", "unknown"])
def test_preflight_refuses_active_or_unknown_jobs(tmp_path, status):
    path = tmp_path / "app.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE video_jobs(status TEXT)")
        db.execute("INSERT INTO video_jobs VALUES (?)", (status,))
    with pytest.raises(RuntimeError, match="no process was stopped"):
        backup_database(path)


def test_backup_rejects_overwrite_and_invalid_foreign_keys(tmp_path):
    path = tmp_path / "app.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE characters(id INTEGER PRIMARY KEY)")
    with pytest.raises(ValueError):
        backup_database(path, path)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE assets(character_id REFERENCES characters(id))")
        db.execute("INSERT INTO assets VALUES (123)")
    with pytest.raises(RuntimeError, match="foreign key"):
        backup_database(path)
