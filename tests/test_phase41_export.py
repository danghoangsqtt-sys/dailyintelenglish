"""Phase 41 (D120): each project's own output folder; only the ticked components are written, automatically."""

from __future__ import annotations

import json
import sqlite3

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
