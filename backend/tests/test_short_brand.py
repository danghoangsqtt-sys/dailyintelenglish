"""Phase 80 (owner 2026-10-26): a Short opens on its content (no intro slide, no greeting voice) and ends on a ~2 s card."""

import asyncio

import pytest

from backend.media import video_renderer_remotion as remotion
from backend.schemas.project import is_short_video


@pytest.mark.parametrize("project,short", [
    ({"explainer_style": "wordday", "duration_minutes": 0.75}, True),
    ({"explainer_style": "chat", "duration_minutes": 0.75}, True),
    ({"explainer_style": None, "duration_minutes": 0.75}, True),          # a 2-character conversation Short
    ({"explainer_style": "presenter", "duration_minutes": 1.0}, True),
    ({"explainer_style": "vox", "duration_minutes": 0.75}, True),
    ({"explainer_style": None, "duration_minutes": 5.0}, False),          # every existing long episode
    ({"explainer_style": "presenter", "duration_minutes": 8.0}, False),
    ({"explainer_style": "vox"}, False),
])
def test_which_projects_are_shorts(project, short):
    assert is_short_video(project) is short


def test_a_short_gets_no_intro_and_a_two_second_end_card(monkeypatch):
    async def must_not_voice(project_id):
        raise AssertionError("a Short has no greeting/farewell voices")

    monkeypatch.setattr(remotion.brand_service, "brand_audio", must_not_voice)
    props = {"introSec": 2.5, "outroSec": 5.0, "fps": 30, "lines": []}
    voices = asyncio.run(remotion._add_brand("project-1", props, short=True))
    assert voices == [] and props["introSec"] == 0.0 and props["outroSec"] == remotion.SHORT_END_CARD_S == 2.0
    assert props["brand"]["short"] is True and props["brand"]["wish"]
