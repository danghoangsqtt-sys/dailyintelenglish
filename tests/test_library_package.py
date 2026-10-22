"""Phase 70 (ENH-052): the library package -- export, then import on a machine that has nothing, merge rules, safety."""

from __future__ import annotations

import io
import json
import os
import sqlite3
import time
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from scripts import cleanup_workspace


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    (tmp_path / "data").mkdir()
    with TestClient(app) as test_client:
        yield test_client


def data(response, status=200):
    assert response.status_code == status, response.text
    return response.json()["data"]


def seed(updated_at="2026-10-20T00:00:00+00:00", name="Lina") -> Path:
    picture = settings.DATA_DIR / "library" / "characters" / "char-lina" / "v1" / "native" / "calm__closed.png"
    picture.parent.mkdir(parents=True, exist_ok=True)
    picture.write_bytes(b"png-lina")
    (settings.DATA_DIR / "music_library").mkdir(exist_ok=True)
    (settings.DATA_DIR / "music_library" / "song.mp3").write_bytes(b"mp3")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO characters (id, name, gender, age_group, role, hair, eyes, top_color, top_item, bottom_color, "
            "bottom_item, status, base_seed, created_at, updated_at) VALUES ('char-lina', ?, 'female', 'young', 'teacher', 'brown', "
            "'brown', 'white', 'dress', 'white', 'dress', 'locked', 1, 'then', ?)", (name, updated_at))
        connection.execute(
            "INSERT OR REPLACE INTO character_assets (id, character_id, kind, path, seed, created_at, updated_at) "
            "VALUES ('asset-1', 'char-lina', 'slot', ?, 1, 'then', ?)", (str(picture), updated_at))
        connection.execute("INSERT OR REPLACE INTO music_tracks (filename, title, created_at, updated_at) VALUES ('song.mp3', 'Song', 'then', ?)",
                           (updated_at,))
        connection.execute("INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES ('gemini_api_key', 'SECRET-KEY', 'then')")
    return picture


def export(client) -> Path:
    result = data(client.post("/api/library-package/export"), 201)
    return Path(result["path"])


def wipe_library():
    """The other machine: no characters, no music, no files."""
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("DELETE FROM character_assets")
        connection.execute("DELETE FROM characters")
        connection.execute("DELETE FROM music_tracks")
    for folder in ("library", "music_library"):
        for path in sorted((settings.DATA_DIR / folder).rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()


def upload(client, package: Path, status=200):
    with package.open("rb") as stream:
        return data(client.post("/api/library-package/import", files={"file": ("library.zip", stream, "application/zip")}), status)


def test_a_package_carries_the_characters_and_files_but_never_the_keys(client):
    seed()
    summary = data(client.get("/api/library-package"))
    assert summary["counts"]["characters"] == 1 and summary["files"] == 2
    package = export(client)
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("manifest.json"))
        assert "files/library/characters/char-lina/v1/native/calm__closed.png" in names and "files/music_library/song.mp3" in names
        assert not any("app_settings" in name for name in names)
        assert b"SECRET-KEY" not in b"".join(archive.read(name) for name in names)
        asset = json.loads(archive.read("db/character_assets.json"))[0]
        assert asset["path"] == "@data/library/characters/char-lina/v1/native/calm__closed.png"
    assert manifest["format"] == "dbe-library-package" and manifest["counts"]["characters"] == 1
    assert package.name in data(client.get("/api/library-package"))["exports"]
    download = client.get(f"/api/library-package/download/{package.name}")
    assert download.status_code == 200 and download.content[:2] == b"PK"


def test_import_on_an_empty_machine_brings_everything_back(client):
    picture = seed()
    package = export(client)
    wipe_library()
    result = upload(client, package)
    assert result["tables"]["characters"]["added"] == 1 and result["tables"]["music_tracks"]["added"] == 1
    assert result["files"]["added"] == 2 and Path(result["backup"]).is_file()
    assert picture.read_bytes() == b"png-lina"
    with sqlite3.connect(settings.db_path) as connection:
        assert connection.execute("SELECT name FROM characters").fetchone() == ("Lina",)
        stored = connection.execute("SELECT path FROM character_assets").fetchone()[0]
    assert Path(stored).resolve() == picture.resolve()


def test_import_merges_newer_wins_older_is_kept_and_nothing_is_deleted(client):
    seed(updated_at="2026-10-20T00:00:00+00:00", name="Lina")
    old_package = export(client)
    seed(updated_at="2026-10-21T00:00:00+00:00", name="Lina (edited here)")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO characters (id, name, gender, age_group, role, hair, eyes, top_color, top_item, bottom_color, bottom_item, "
            "status, base_seed, created_at, updated_at) VALUES ('char-only-here', 'Kim', 'female', 'adult', 'host', 'b', 'b', 'w', "
            "'t', 'w', 'b', 'locked', 1, 'then', 'then')")
    result = upload(client, old_package)
    assert result["tables"]["characters"] == {"added": 0, "updated": 0, "kept": 1, "filled": 0}
    with sqlite3.connect(settings.db_path) as connection:
        names = dict(connection.execute("SELECT id, name FROM characters"))
    assert names == {"char-lina": "Lina (edited here)", "char-only-here": "Kim"}
    # and a newer package does replace the older row here
    newer = export(client)
    seed(updated_at="2026-10-19T00:00:00+00:00", name="Lina (old here)")
    assert upload(client, newer)["tables"]["characters"]["updated"] == 1


def test_a_newer_file_replaces_an_older_one_and_an_older_file_is_kept(client):
    picture = seed()
    package = export(client)
    picture.write_bytes(b"edited later here")
    upload(client, package)
    assert picture.read_bytes() == b"edited later here"  # this machine's copy is newer
    old = time.time() - 86400 * 30
    os.utime(picture, (old, old))
    assert upload(client, package)["files"]["updated"] == 1
    assert picture.read_bytes() == b"png-lina"


def _crafted(entries: dict[str, bytes]) -> Path:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"format": "dbe-library-package", "format_version": 1}))
        for name, content in entries.items():
            archive.writestr(name, content)
    path = settings.DATA_DIR / "crafted.zip"
    path.write_bytes(buffer.getvalue())
    return path


def test_unsafe_or_foreign_packages_are_refused(client):
    response = client.post("/api/library-package/import", files={"file": ("x.zip", _crafted({"files/../outside.txt": b"x"}).read_bytes())})
    assert response.status_code == 422 and not (settings.DATA_DIR.parent / "outside.txt").exists()
    response = client.post("/api/library-package/import", files={"file": ("x.zip", _crafted({"files/app.db": b"x"}).read_bytes())})
    assert response.status_code == 422
    response = client.post("/api/library-package/import", files={"file": ("x.zip", b"not a zip")})
    assert response.status_code == 422 and "not a library package" in response.text
    assert client.get("/api/library-package/download/..%5Capp.db").status_code in (404, 422)


def test_import_waits_for_running_jobs(client):
    seed()
    package = export(client)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("INSERT INTO audio_jobs (id, project_id, status) VALUES ('job-1', 'p1', 'processing')")
    response = client.post("/api/library-package/import", files={"file": ("l.zip", package.read_bytes())})
    assert response.status_code == 422 and "job is running" in response.text


def test_workspace_cleanup_lists_leftovers_and_keeps_the_newest_backup(tmp_path):
    data_dir = tmp_path / "data"
    (data_dir / "tmp" / "phase-old-stage").mkdir(parents=True)
    (data_dir / "tmp" / "phase-old-stage" / "big.bin").write_bytes(b"0" * 10)
    (data_dir / "tmp" / "worktree").mkdir()
    (data_dir / "tmp" / "worktree" / ".git").write_text("gitdir: elsewhere")
    (data_dir / "tmp" / "nested" / "docs").mkdir(parents=True)
    (data_dir / "tmp" / "nested" / "docs" / ".git").write_text("gitdir: elsewhere")
    for name in ("desktop-20261001-000000-000", "desktop-20261022-000000-000"):
        (data_dir / "backups" / name).mkdir(parents=True)
    (data_dir / "library" / "characters" / "keep").mkdir(parents=True)
    (tmp_path / "build").mkdir()
    found = {path.relative_to(tmp_path).as_posix(): label for label, path in cleanup_workspace.targets(tmp_path)}
    assert found == {"data/tmp/phase-old-stage": "temporary", "data/backups/desktop-20261001-000000-000": "older app backup",
                     "build": "build work folder"}


def test_a_row_kept_here_still_takes_the_picture_it_lacks(client):
    plate = settings.DATA_DIR / "library" / "scenes" / "builtin-classroom" / "preview.png"
    plate.parent.mkdir(parents=True, exist_ok=True)
    plate.write_bytes(b"plate")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE scenes SET preview_path = ?, updated_at = '2026-10-01' WHERE id = 'builtin-classroom'", (str(plate),))
    package = export(client)
    # a new machine: the built-in scene was just seeded (newer), with no picture
    plate.unlink()
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE scenes SET preview_path = NULL, updated_at = '2026-10-22' WHERE id = 'builtin-classroom'")
    result = upload(client, package)
    assert result["tables"]["scenes"]["filled"] == 1 and plate.read_bytes() == b"plate"
    with sqlite3.connect(settings.db_path) as connection:
        stored = connection.execute("SELECT preview_path FROM scenes WHERE id = 'builtin-classroom'").fetchone()[0]
    assert Path(stored).resolve() == plate.resolve()

# ---------------------------------------------------------------- Settings -> Data & sync (browser)

@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory):
    from tests.conftest import live_server

    with live_server(tmp_path_factory, "library_package_browser") as url:
        yield url


@pytest.mark.asyncio
async def test_settings_exports_a_package_from_the_data_and_sync_section(live_server_url):
    from playwright.async_api import async_playwright

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"{live_server_url}/settings#data")
        await page.locator("#package-counts .kpi").first.wait_for()
        assert await page.locator("#settings-data").is_visible() and not await page.locator("#settings-general").is_visible()
        assert "characters" in await page.locator("#package-counts").text_content()
        assert await page.locator("#package-import").is_disabled()
        await page.locator("#package-export").click()
        await page.wait_for_function("document.getElementById('package-export-status').textContent.startsWith('Saved library-')")
        await page.locator("#package-exports a").first.wait_for()  # the list reloads after the status line
        assert await page.locator("#package-exports a").count() == 1
        assert (await page.locator("#package-exports a").get_attribute("href")).startswith("/api/library-package/download/library-")
        await browser.close()

