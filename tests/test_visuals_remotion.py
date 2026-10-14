"""Remotion props without drawn shots (Phase 44, D123: the two-person shot track is gone)."""

import pytest

from backend.media import video_renderer_remotion
from tests.test_visuals_project_api import client, data  # noqa: F401


@pytest.mark.asyncio
async def test_remotion_props_never_carry_a_drawn_shot_track(db):
    project = {"id": "no-shots", "name": "Quiet lesson", "topic": "Greetings", "cefr_level": "A2",
               "speakers": [{"id": "speaker-1", "speaker_index": 0, "name": "Nova",
                             "gender": "female", "avatar_image_path": None}]}
    audio_job = {"timestamps": [{"start_sec": 0.0, "end_sec": 1.0, "label": "Nova",
                                 "speaker_id": "speaker-1", "text": "Hello"}], "word_timestamps": []}
    props = await video_renderer_remotion._build_input_props(db, project, audio_job, None, visual_mode="podcast_black")
    assert "visuals" not in props and props["visualMode"] == "podcast_black"
    assert props["speakers"] == [{"id": "speaker-1", "name": "Nova", "gender": "female"}]  # no avatar picture
