"""Phase 41 (D120): each project's own output folder; only the ticked components are written, automatically."""

from __future__ import annotations

import json
import sqlite3
import threading

from backend.content import export_service
from backend.core.config import settings
from tests.test_phase40_character_names import _project
from tests.test_visuals_project_api import client, data  # noqa: F401


def _video(project_id: str, tmp) -> None:
    video, srt = tmp / "v.mp4", tmp / "s.srt"
    video.write_bytes(b"mp4-bytes")
    srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nHi\n", encoding="utf-8")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("INSERT INTO video_jobs (id, project_id, status, mode, mp4_path, srt_path) "
                           "VALUES ('vj1', ?, 'complete', 'remotion', ?, ?)", (project_id, str(video), str(srt)))


def test_the_folder_gets_only_the_ticked_components(client, tmp_path):  # noqa: F811
    project = _project(client, names=("Mia", "Tom"))
    _video(project["id"], tmp_path)
    folder = tmp_path / "My episode"
    view = data(client.put(f"/api/projects/{project['id']}/export",
                           json={"output_dir": str(folder), "items": ["script", "video"]}))
    assert view["settings"]["items"] == ["video", "script"]  # stable order
    assert sorted(view["sync"]["written"]) == ["script.txt", "subtitles.srt", "video.mp4"]
    assert (folder / "video.mp4").read_bytes() == b"mp4-bytes"
    assert (folder / "script.txt").read_text(encoding="utf-8").startswith("Mia: Hi Tom!")
    assert not (folder / "thumbnail.png").exists() and not (folder / "youtube").exists()
    again = data(client.post(f"/api/projects/{project['id']}/export/sync"))
    assert again["written"] == []  # nothing changed: nothing rewritten


def test_a_new_audio_is_exported_automatically(client, tmp_path, monkeypatch):  # noqa: F811
    project = _project(client, names=("Mia", "Tom"))
    folder = tmp_path / "out"
    data(client.put(f"/api/projects/{project['id']}/export", json={"output_dir": str(folder), "items": ["audio"]}))
    mp3 = tmp_path / "mix.mp3"
    mp3.write_bytes(b"ID3-audio")
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("INSERT INTO audio_jobs (id, project_id, status, mp3_path, duration_seconds, timestamps_json) "
                           "VALUES ('a1', ?, 'complete', ?, 3.0, ?)", (project["id"], str(mp3), json.dumps([])))

    import asyncio

    import aiosqlite

    async def hook() -> None:
        async with aiosqlite.connect(settings.db_path) as db:
            db.row_factory = aiosqlite.Row
            await export_service.sync_quietly(db, project["id"])

    asyncio.run(hook())
    assert (folder / "audio.mp3").read_bytes() == b"ID3-audio"


def test_bad_folders_and_components_are_refused(client):  # noqa: F811
    project = _project(client, names=("Mia", "Tom"))
    url = f"/api/projects/{project['id']}/export"
    assert client.put(url, json={"output_dir": "relative/folder", "items": ["video"]}).status_code == 422
    assert client.put(url, json={"output_dir": "C:\\x", "items": ["everything"]}).status_code == 422
    view = data(client.get(url))
    assert view["settings"] is None and [item["key"] for item in view["components"]][:3] == ["video", "video_vertical",
                                                                                            "thumbnail"]
    assert client.post(f"{url}/sync").status_code == 422  # no folder yet


def test_stopping_the_export_keeps_the_files(client, tmp_path):  # noqa: F811
    project = _project(client, names=("Mia", "Tom"))
    folder = tmp_path / "keep"
    data(client.put(f"/api/projects/{project['id']}/export", json={"output_dir": str(folder), "items": ["script"]}))
    assert (folder / "script.txt").is_file()
    data(client.delete(f"/api/projects/{project['id']}/export"))
    assert (folder / "script.txt").is_file() and data(client.get(f"/api/projects/{project['id']}/export"))["settings"] is None


def test_script_and_learning_edits_refresh_selected_files(client, tmp_path, monkeypatch):  # noqa: F811
    from backend.content import learning_service
    from tests.test_learning_api import VALID_PACK

    project = _project(client, names=("Mia", "Tom"))
    project_id = project["id"]
    folder = tmp_path / "edited"
    monkeypatch.setattr(learning_service, "generate_learning_pack", lambda *args: _pack_result(VALID_PACK))
    data(client.post(f"/api/projects/{project_id}/learning/generate"))
    data(client.put(f"/api/projects/{project_id}/export", json={
        "output_dir": str(folder), "items": ["script", "learning"],
    }))
    assert "Hi Tom!" in (folder / "script.txt").read_text(encoding="utf-8")

    data(client.put(f"/api/projects/{project_id}/script", json={"lines": [
        {"speaker_id": project["ids"][0], "text": "A fresh edited line."},
        {"speaker_id": project["ids"][1], "text": "And a second line."},
    ]}))
    assert "A fresh edited line." in (folder / "script.txt").read_text(encoding="utf-8")
    assert "Hi Tom!" not in (folder / "script.txt").read_text(encoding="utf-8")
    assert "A fresh edited line." in (folder / "learning_pack.txt").read_text(encoding="utf-8")

    vocabulary = [{**VALID_PACK.vocabulary[0].model_dump(), "definition_en": "edited definition"}]
    data(client.put(f"/api/projects/{project_id}/learning", json={"vocabulary": vocabulary}))
    assert "edited definition" in (folder / "learning_pack.txt").read_text(encoding="utf-8")

    data(client.patch(f"/api/projects/{project_id}/speakers/{project['ids'][0]}", json={"name": "Maya"}))
    assert "Maya: A fresh edited line." in (folder / "script.txt").read_text(encoding="utf-8")


async def _pack_result(pack):
    return pack


def test_slow_export_copy_does_not_hold_the_database_lock(client, tmp_path, monkeypatch):  # noqa: F811
    project = _project(client)
    folder = tmp_path / "slow"
    data(client.put(f"/api/projects/{project['id']}/export", json={
        "output_dir": str(folder), "items": ["script"],
    }))
    started, release, read_done = threading.Event(), threading.Event(), threading.Event()
    original_write = export_service._write

    def slow_write(path, plan):
        started.set()
        assert release.wait(5), "test did not release the slow copy"
        return original_write(path, plan)

    monkeypatch.setattr(export_service, "_write", slow_write)
    copying = threading.Thread(target=lambda: client.post(f"/api/projects/{project['id']}/export/sync"), daemon=True)
    reading = threading.Thread(target=lambda: (client.get("/api/projects"), read_done.set()), daemon=True)
    copying.start()
    try:
        assert started.wait(5), "export copy did not start"
        reading.start()
        assert read_done.wait(2), "unrelated DB read waited behind filesystem copy"
    finally:
        release.set()
        copying.join(5)
        if reading.ident is not None:
            reading.join(5)


def test_old_copy_cannot_mark_a_new_folder_as_synced(client, tmp_path, monkeypatch):  # noqa: F811
    project = _project(client)
    old_folder, new_folder = tmp_path / "old", tmp_path / "new"
    data(client.put(f"/api/projects/{project['id']}/export", json={
        "output_dir": str(old_folder), "items": ["script"],
    }))
    started, release = threading.Event(), threading.Event()
    original_write = export_service._write

    def slow_write(path, plan):
        started.set()
        assert release.wait(5)
        return original_write(path, plan)

    monkeypatch.setattr(export_service, "_write", slow_write)
    copying = threading.Thread(target=lambda: client.post(f"/api/projects/{project['id']}/export/sync"), daemon=True)
    copying.start()
    try:
        assert started.wait(5)
        with sqlite3.connect(settings.db_path) as connection:
            connection.execute(
                "UPDATE project_exports SET output_dir = ?, updated_at = ?, last_sync_at = NULL WHERE project_id = ?",
                (str(new_folder), "new-settings-version", project["id"]),
            )
    finally:
        release.set()
        copying.join(5)
    current = data(client.get(f"/api/projects/{project['id']}/export"))["settings"]
    assert current["output_dir"] == str(new_folder) and current["last_sync_at"] is None
