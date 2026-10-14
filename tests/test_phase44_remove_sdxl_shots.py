"""Phase 44 (D123): RealVisXL/SDXL, the two-person shots and the "with characters" video are removed; the old shot
pictures are archived first."""

from __future__ import annotations

import importlib.util
import sqlite3
import zipfile

from backend.core.paths import PROJECT_ROOT


def _archiver():
    spec = importlib.util.spec_from_file_location("archive_old_shots", PROJECT_ROOT / "scripts" / "archive_old_shots.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_old_shot_pictures_are_backed_up_zipped_then_removed(tmp_path):
    data = tmp_path / "data"
    (data / "visuals" / "p1" / "shots" / "s1").mkdir(parents=True)
    (data / "visuals" / "p1" / "shots" / "s1" / "final.png").write_bytes(b"shot")
    (data / "visuals" / "p1" / "plates").mkdir()
    (data / "visuals" / "p1" / "plates" / "keep.png").write_bytes(b"plate")
    (data / "library" / "shots").mkdir(parents=True)
    (data / "library" / "shots" / "a.png").write_bytes(b"library shot")
    (data / "video").mkdir()
    (data / "video" / "keep.mp4").write_bytes(b"video")
    db = tmp_path / "app.db"
    sqlite3.connect(db).close()
    archiver = _archiver()

    dry = archiver.archive(data, db, data / "backups", apply=False)
    assert dry["files"] == 2 and dry["zip"] is None and (data / "library" / "shots" / "a.png").exists()

    done = archiver.archive(data, db, data / "backups", apply=True)
    with zipfile.ZipFile(done["zip"]) as bundle:
        assert sorted(bundle.namelist()) == ["data/library/shots/a.png", "data/visuals/p1/shots/s1/final.png"]
    assert not (data / "visuals" / "p1" / "shots").exists() and not (data / "library" / "shots").exists()
    assert (data / "visuals" / "p1" / "plates" / "keep.png").exists() and (data / "video" / "keep.mp4").exists()
    assert (data / "backups").joinpath(done["db_backup"].split("\\")[-1].split("/")[-1]).exists()
