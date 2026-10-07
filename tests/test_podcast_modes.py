"""Phase 30 (ENH-021): the podcast visual modes in the Remotion props and the video API."""

from __future__ import annotations

import sqlite3

import aiosqlite
import pytest
from PIL import Image
from pydantic import ValidationError as PydanticValidationError

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.video import GenerateVideoRequest
from app.services import video_renderer_remotion
from tests.test_visuals_project_api import client, data, setup_project, wait_job  # noqa: F401


def _public(tmp_path, monkeypatch):
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_VISUALS_DIR", tmp_path / "public" / "visuals")
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_AVATARS_DIR", tmp_path / "public" / "avatars")


def _audio_job(project):
    return {"timestamps": [{"start_sec": 0.0, "end_sec": 2.0, "label": "Speaker One",
                            "speaker_id": project["speakers"][0]["id"], "text": "Hello"}], "word_timestamps": []}


def _make_a_plate(scene_id: str) -> None:
    path = settings.DATA_DIR / "library" / "scenes" / scene_id / "preview.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1344, 768), (20, 120, 60)).save(path)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("UPDATE scenes SET preview_path = ? WHERE id = ?", (str(path), scene_id))


# ---- the request model --------------------------------------------------------------------------------------------

def test_request_defaults_keep_the_drawn_story_and_unknown_modes_are_refused():
    request = GenerateVideoRequest(template_id="midnight")
    assert request.visual_mode == "illustrated" and request.still_scene_id is None
    assert GenerateVideoRequest(template_id="midnight", visual_mode="podcast_still",
                                still_scene_id="builtin-cafe").still_scene_id == "builtin-cafe"
    with pytest.raises(PydanticValidationError):
        GenerateVideoRequest(template_id="midnight", visual_mode="podcast_characters")


# ---- the props ----------------------------------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_podcast_black_has_no_pictures_of_anyone_and_no_shots(client, tmp_path, monkeypatch):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots")))
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await video_renderer_remotion._build_input_props(
            db, project, _audio_job(project), None, visual_mode="podcast_black")
    assert props["visualMode"] == "podcast_black"
    assert "visuals" not in props and "stillUrl" not in props
    assert all("avatarUrl" not in s for s in props["speakers"])
    assert not (tmp_path / "public" / "visuals").exists()  # not even copied: nothing to wait for


@pytest.mark.asyncio
async def test_podcast_still_uses_the_chosen_scene_plate(client, tmp_path, monkeypatch):  # noqa: F811
    project, _, scenes = setup_project(client, 2, 2)
    _make_a_plate("builtin-library")
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await video_renderer_remotion._build_input_props(
            db, project, _audio_job(project), None, visual_mode="podcast_still", still_scene_id="builtin-library")
    assert props["visualMode"] == "podcast_still" and "visuals" not in props
    assert props["stillUrl"] == f"remotion-render/visuals/{project['id']}/still.png"
    assert Image.open(tmp_path / "public" / "visuals" / project["id"] / "still.png").size == (1344, 768)
    assert all("avatarUrl" not in s for s in props["speakers"])


@pytest.mark.asyncio
async def test_podcast_still_without_a_choice_takes_the_first_scene_that_has_a_plate(client, tmp_path, monkeypatch):  # noqa: F811
    project, _, scenes = setup_project(client, 2, 2)
    _make_a_plate(scenes[1]["id"])  # the project's second scene is the only one with a plate
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await video_renderer_remotion._build_input_props(
            db, project, _audio_job(project), None, visual_mode="podcast_still")
    assert props["stillUrl"].endswith("still.png")


@pytest.mark.asyncio
async def test_podcast_still_with_no_plate_anywhere_is_refused_with_a_clear_message(client, tmp_path, monkeypatch):  # noqa: F811
    project, _, _ = setup_project(client, 2, 1)
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        with pytest.raises(ValidationError, match="plate"):
            await video_renderer_remotion._build_input_props(
                db, project, _audio_job(project), None, visual_mode="podcast_still")
        with pytest.raises(ValidationError, match="plate"):
            await video_renderer_remotion._build_input_props(
                db, project, _audio_job(project), None, visual_mode="podcast_still", still_scene_id="builtin-cafe")
        with pytest.raises(ValidationError, match="scene"):
            await video_renderer_remotion._build_input_props(
                db, project, _audio_job(project), None, visual_mode="podcast_still", still_scene_id="no-such-scene")


@pytest.mark.asyncio
async def test_the_drawn_story_is_unchanged_and_still_marks_its_mode(client, tmp_path, monkeypatch):  # noqa: F811
    project, _, _ = setup_project(client, 1, 1)
    wait_job(client, data(client.post(f"/api/projects/{project['id']}/visuals/shots")))
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await video_renderer_remotion._build_input_props(db, project, _audio_job(project), None)
    assert props["visualMode"] == "illustrated" and props["visuals"]["lineShots"]
    assert props["speakers"][0]["avatarUrl"].endswith("_cast.png")
