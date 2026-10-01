"""Task 20.7 deterministic shot assignment and Remotion prop copying."""

import aiosqlite
import pytest

from app.core.config import settings
from app.services import video_renderer_remotion
from app.services.visuals.project_visuals_service import assign_line_shots
from tests.test_visuals_project_api import client, setup_project, wait_job, data  # noqa: F401


def _shot(shot_id, scene_id, kind, indexes):
    return {"id": shot_id, "scene_id": scene_id, "kind": kind, "speaker_indexes": indexes,
            "status": "complete", "final_path": "somewhere.png"}


def test_assign_line_shots_chapters_position_speaker_and_fallbacks():
    scenes = [{"id": "cafe"}, {"id": "classroom"}]
    chapters = [{"startSec": 0}, {"startSec": 4}]
    lines = [{"startSec": i, "speaker_index": i % 2} for i in range(8)]
    shots = [
        _shot("wide", "cafe", "duo_wide", [0, 1]),
        _shot("close", "cafe", "duo_close", [0, 1]),
        _shot("solo0", "cafe", "single", [0]),
        _shot("solo1", "cafe", "single", [1]),
        _shot("school-solo", "classroom", "single", [0]),
    ]
    assert assign_line_shots(lines, chapters, scenes, shots) == [
        "wide", "solo1", "solo0", "close", "school-solo", "school-solo", "school-solo", "school-solo",
    ]
    assert assign_line_shots([lines[0]], chapters[:1], scenes[:1], shots[1:3]) == ["solo0"]
    assert assign_line_shots([lines[0]], chapters[:1], scenes[:1], shots[1:2]) == ["close"]
    assert assign_line_shots(lines[:2], chapters[:1], scenes[:1], shots[:1]) == ["wide", "wide"]
    unknown = _shot("other", "cafe", "other", [0])
    assert assign_line_shots([lines[0]], chapters[:1], scenes[:1], [unknown]) == ["other"]
    assert assign_line_shots([lines[0]], chapters[:1], scenes[:1], []) == [None]
    assert assign_line_shots(lines, chapters, [], shots) == [None] * 8


@pytest.mark.asyncio
async def test_remotion_props_copy_complete_shot_and_cast_face(client, tmp_path, monkeypatch):  # noqa: F811
    project, _, _ = setup_project(client, 1, 1)
    base = f"/api/projects/{project['id']}/visuals"
    wait_job(client, data(client.post(f"{base}/shots")))
    visuals = data(client.get(base))
    shot = visuals["shots"][0]
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_VISUALS_DIR", tmp_path / "public" / "visuals")
    monkeypatch.setattr(video_renderer_remotion, "REMOTION_AVATARS_DIR", tmp_path / "public" / "avatars")
    audio_job = {"timestamps": [{"start_sec": 0.0, "end_sec": 2.0, "label": "Speaker One",
                                 "speaker_id": project["speakers"][0]["id"], "text": "Hello"}],
                 "word_timestamps": []}
    async with aiosqlite.connect(settings.db_path) as db:
        db.row_factory = aiosqlite.Row
        props = await video_renderer_remotion._build_input_props(db, project, audio_job, None)
    assert props["visuals"]["lineShots"] == [shot["id"]]
    assert props["visuals"]["shots"][shot["id"]]["kind"] == "single"
    assert (tmp_path / "public" / "visuals" / project["id"] / f"{shot['id']}.png").is_file()
    assert props["speakers"][0]["avatarUrl"].endswith("_cast.png")
    assert list((tmp_path / "public" / "avatars").glob("*_cast.png"))


@pytest.mark.asyncio
async def test_remotion_props_without_shots_keep_visuals_optional(db):
    project = {"id": "no-shots", "name": "Quiet lesson", "topic": "Greetings", "cefr_level": "A2",
               "speakers": [{"id": "speaker-1", "speaker_index": 0, "name": "Nova",
                             "gender": "female", "avatar_image_path": None}]}
    audio_job = {"timestamps": [{"start_sec": 0.0, "end_sec": 1.0, "label": "Nova",
                                 "speaker_id": "speaker-1", "text": "Hello"}], "word_timestamps": []}
    props = await video_renderer_remotion._build_input_props(db, project, audio_job, None)
    assert "visuals" not in props
