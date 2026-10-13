"""Phase 32 (Task 32.4): the props of the "podcast_sprites" video mode and its refusal without sprite sets."""

from __future__ import annotations

import sqlite3

import aiosqlite
import pytest

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.video import GenerateVideoRequest
from app.services import video_renderer_remotion as remotion
from app.services.visuals import library_service, sprite_service
from tests.test_podcast_modes import _make_a_plate
from tests.test_sprite_service import _figure
from tests.test_visuals_project_api import client, data, setup_project  # noqa: F401


def _public(tmp_path, monkeypatch):
    monkeypatch.setattr(remotion, "REMOTION_VISUALS_DIR", tmp_path / "public" / "visuals")
    monkeypatch.setattr(remotion, "REMOTION_SPRITES_DIR", tmp_path / "public" / "sprites")


def _audio_job(project):
    first, second = project["speakers"][0]["id"], project["speakers"][1]["id"]
    return {
        "mp3_path": str(settings.DATA_DIR / "no-such-audio.mp3"),  # no audio: the mouths follow the words
        "timestamps": [
            {"start_sec": 0.0, "end_sec": 1.5, "label": "One", "speaker_id": first, "text": "Hello there!"},
            {"start_sec": 2.0, "end_sec": 3.0, "label": "Two", "speaker_id": second, "text": "Hi."},
        ],
        "word_timestamps": [
            {"words": [{"text": "Hello", "start_sec": 0.1, "end_sec": 0.5}, {"text": "there", "start_sec": 0.5, "end_sec": 1.0}]},
            {"words": [{"text": "Hi", "start_sec": 2.1, "end_sec": 2.6}]},
        ],
    }


def _give_sprites(character_id: str, names=("calm__closed", "calm__open", "smile__closed", "smile__open", "gesture-wave")) -> None:
    folder = settings.DATA_DIR / "sprite-source" / character_id
    files = {}
    for name in names:
        _figure(folder / f"{name}.png")
        files[name] = folder / f"{name}.png"
    accepted, refused = sprite_service.check_folder(files)
    assert not refused
    sprite_service._write_set(character_id, files, accepted, lambda _path: [0.5, 0.22, 0.08, 0.07])


def test_the_request_accepts_the_new_mode():
    assert GenerateVideoRequest(template_id="midnight", visual_mode="podcast_sprites").visual_mode == "podcast_sprites"


@pytest.mark.asyncio
async def test_a_cast_character_without_sprites_is_refused_by_name(client, tmp_path, monkeypatch):  # noqa: F811
    project, ids, _ = setup_project(client, 2, 1)
    _give_sprites(ids[0])
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        with pytest.raises(ValidationError, match="Mira has no talking sprites"):
            await remotion._build_input_props(db, project, _audio_job(project), None, visual_mode="podcast_sprites")


@pytest.mark.asyncio
async def test_the_sprite_props_carry_both_sets_the_plan_and_one_plate(client, tmp_path, monkeypatch):  # noqa: F811
    project, ids, scenes = setup_project(client, 2, 1)
    _give_sprites(ids[0])
    _give_sprites(ids[1], names=("calm__closed", "calm__open"))
    _make_a_plate(scenes[0]["id"])
    _public(tmp_path, monkeypatch)
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await remotion._build_input_props(db, project, _audio_job(project), None, visual_mode="podcast_sprites")
    assert props["visualMode"] == "podcast_sprites" and "visuals" not in props
    assert all("avatarUrl" not in speaker for speaker in props["speakers"])
    sprites = props["sprites"]
    left, right = sprites["characters"]
    assert (left["slot"], left["name"], right["slot"], right["name"]) == (0, "Nova", 1, "Mira")
    # Task 33.8: copied per character (one character can stand in different slots in different segments)
    assert left["pictures"]["gesture-wave"] == f"remotion-render/sprites/{project['id']}/{ids[0]}/gesture-wave.png"
    assert (tmp_path / "public" / "sprites" / project["id"] / ids[1] / "calm__open.png").is_file()
    assert (left["fromSec"], left["toSec"]) == (0.0, None)  # two speakers: one segment for the whole video
    assert left["faceEllipse"] == [0.5, 0.22, 0.08, 0.07] and 0.1 < left["topFraction"] < 0.2
    assert left["offsets"]["calm__closed"] == [0.0, 0]
    first, second = sprites["lines"]
    assert (first["slot"], first["expression"], first["gesture"]) == (0, "smile", "wave")
    assert first["mouth"] == [[0.1, 0.44], [0.5, 0.94]]  # from the words: no audio file
    assert (second["slot"], second["expression"], second["listenerExpression"]) == (1, "calm", "calm")
    assert sprites["backgrounds"] == {"still": f"remotion-render/sprites/{project['id']}/bg/still.png"}
    assert sprites["lineBackgrounds"] == ["still", "still"]


def test_each_line_takes_the_place_of_its_beat_and_an_insert_keeps_the_place_before():
    beats = [
        {"line_from": 0, "line_to": 0, "kind": "insert", "scene_id": None},
        {"line_from": 1, "line_to": 2, "kind": "scene", "scene_id": "cafe"},
        {"line_from": 3, "line_to": 3, "kind": "insert", "scene_id": None},
        {"line_from": 4, "line_to": 5, "kind": "scene", "scene_id": "park"},
    ]
    assert remotion._beat_scene_per_line(beats, 6) == ["cafe", "cafe", "cafe", "cafe", "park", "park"]


# BUG-025: a missing scene or plate falls back (and is logged); a database or disk failure is not hidden.
async def test_a_missing_scene_plate_falls_back_and_is_logged(monkeypatch, caplog):
    async def missing(_db, _scene_id):
        raise NotFoundError("Scene not found")

    monkeypatch.setattr(library_service, "get_scene_row", missing)
    with caplog.at_level("WARNING"):
        assert await remotion._scene_plate(None, "scene-9", "proj-1") is None
    assert "sprite_scene_plate_missing project_id=proj-1 scene_id=scene-9" in caplog.text


async def test_a_database_failure_in_the_scene_lookup_is_raised(monkeypatch):
    async def broken(_db, _scene_id):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(library_service, "get_scene_row", broken)
    with pytest.raises(sqlite3.OperationalError):
        await remotion._scene_plate(None, "scene-9", "proj-1")
