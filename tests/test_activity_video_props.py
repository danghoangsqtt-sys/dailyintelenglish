"""Task 32.6d: approved insert images become bounded Remotion cutaway props."""

from __future__ import annotations

import json
import sqlite3

import aiosqlite
import pytest
from PIL import Image

from app.core.config import settings
from app.services import video_renderer_remotion as remotion
from tests.test_podcast_modes import _make_a_plate
from tests.test_sprite_video_props import _give_sprites, _public
from tests.test_visuals_project_api import client, setup_project  # noqa: F401


def _long_audio(project: dict) -> dict:
    first, second = project["speakers"][0]["id"], project["speakers"][1]["id"]
    return {
        "mp3_path": str(settings.DATA_DIR / "not-read-by-props.mp3"),
        "timestamps": [
            {"start_sec": 0.0, "end_sec": 8.0, "label": "One", "speaker_id": first,
             "text": "I am packing my suitcase for the trip."},
            {"start_sec": 8.0, "end_sec": 11.0, "label": "Two", "speaker_id": second,
             "text": "Now cross the street carefully."},
        ],
        "word_timestamps": [{"words": []}, {"words": []}],
    }


@pytest.mark.asyncio
async def test_approved_insert_is_copied_full_frame_for_at_most_six_seconds_and_missing_falls_back(
    client, tmp_path, monkeypatch,  # noqa: F811
):
    project, character_ids, scenes = setup_project(client, 2, 1)
    _give_sprites(character_ids[0])
    _give_sprites(character_ids[1])
    _make_a_plate(scenes[0]["id"])
    _public(tmp_path, monkeypatch)

    source_folder = settings.DATA_DIR / "library" / "activities"
    source_folder.mkdir(parents=True, exist_ok=True)
    approved = source_folder / "packing.png"
    pending = source_folder / "crossing.png"
    Image.new("RGB", (1280, 720), (30, 60, 90)).save(approved)
    Image.new("RGB", (1280, 720), (90, 60, 30)).save(pending)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute(
            "INSERT INTO project_storyboards (project_id, status, source, updated_at) VALUES (?, 'approved', 'owner', 'now')",
            (project["id"],),
        )
        for index, (action, speaker) in enumerate((("packing suitcase", 0), ("cross the street", 1))):
            connection.execute(
                "INSERT INTO project_beats (id, project_id, position, line_from, line_to, kind, speakers_json, action, "
                "expression, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'insert', ?, ?, 'calm', 'now', 'now')",
                (f"insert-{index}", project["id"], index, index, index, json.dumps([speaker]), action),
            )
        connection.execute(
            "INSERT INTO activity_library (id, character_id, activity, aliases_json, path, content_sha, review_state, "
            "created_at, updated_at) VALUES ('packing-approved', ?, 'packing', '[\"packing suitcase\"]', ?, "
            "'sha-packing', 'approved', 'now', 'now')",
            (character_ids[0], str(approved)),
        )
        connection.execute(
            "INSERT INTO activity_library (id, activity, path, content_sha, review_state, created_at, updated_at) "
            "VALUES ('crossing-pending', 'cross the street', ?, 'sha-crossing', 'pending', 'now', 'now')",
            (str(pending),),
        )

    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await remotion._build_input_props(
            db, project, _long_audio(project), None, visual_mode="podcast_sprites",
        )

    sprites = props["sprites"]
    assert sprites["cutaways"] == [{
        "startSec": 0.0,
        "endSec": 6.0,
        "url": f"remotion-render/sprites/{project['id']}/activities/packing-approved.png",
    }]
    assert sprites["_activityUses"] == [{"activity_id": "packing-approved", "beat_id": "insert-0"}]
    assert (tmp_path / "public" / "sprites" / project["id"] / "activities" / "packing-approved.png").is_file()
    assert sprites["lineBackgrounds"] == ["still", "still"]


@pytest.mark.asyncio
async def test_backend_usage_metadata_is_not_sent_to_remotion_but_returns_after_success(tmp_path, monkeypatch):
    seen: dict = {}

    async def fake_props(*_args, **_kwargs):
        return {"sprites": {"cutaways": [], "_activityUses": [
            {"activity_id": "activity-1", "beat_id": "beat-1"},
        ]}}

    async def no_brand(*_args, **_kwargs):
        return []

    async def no_soundtrack(*_args, **_kwargs):
        return None

    def fake_render(props, output_path):
        seen["props"] = props
        return {"mp4_path": str(output_path), "srt_path": None, "background_image": None,
                "mode": "remotion", "fallback_used": False, "wall_time_seconds": 0.1}

    monkeypatch.setattr(remotion, "_build_input_props", fake_props)
    monkeypatch.setattr(remotion, "_copy_audio_into_public", lambda *_args: None)
    monkeypatch.setattr(remotion, "_add_brand", no_brand)
    monkeypatch.setattr(remotion, "_build_soundtrack", no_soundtrack)
    monkeypatch.setattr(remotion, "_render_via_remotion_sync", fake_render)

    result = await remotion.render_via_remotion(
        None, {"id": "project-1"}, {"mp3_path": "unused.mp3"}, None, tmp_path / "video.mp4",
        visual_mode="podcast_sprites",
    )

    assert "_activityUses" not in seen["props"]["sprites"]
    assert result["activity_uses"] == [{"activity_id": "activity-1", "beat_id": "beat-1"}]
