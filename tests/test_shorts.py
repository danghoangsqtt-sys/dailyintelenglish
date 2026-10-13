"""Phase 37 (D98-D101): highlight clips for Shorts/TikTok -- AI proposal, owner edits, packages, and the vertical renders."""

from __future__ import annotations

import json
import sqlite3

from backend.core.config import settings
from backend.content import shorts_service
from backend.media import video_renderer_remotion, video_service
from backend.ai.llm.contracts import AIMode, GenerationResult
from backend.ai.llm.fake_provider import FakeProvider
from backend.ai.llm.router import AIRouter
from tests.test_storyboard_api import project_with_script
from tests.test_visuals_project_api import client, data  # noqa: F401

# 12 lines of 8 s each: a clip of lines 2..6 lasts 40 s
STAMPS = [{"start_sec": 8.0 * index, "end_sec": 8.0 * index + 7.5, "label": "Lan" if index % 2 == 0 else "Minh",
           "text": f"Line number {index} of the lesson."} for index in range(12)]


def _with_audio(client) -> dict:  # noqa: F811
    project = project_with_script(client, speakers=(0, 1) * 6)
    with sqlite3.connect(settings.db_path) as connection:
        connection.execute("INSERT INTO audio_jobs (id, project_id, status, mp3_path, duration_seconds, timestamps_json) "
                           "VALUES ('a1', ?, 'complete', 'x.mp3', 96.0, ?)", (project["id"], json.dumps(STAMPS)))
    return project


def _router(monkeypatch, payload: dict) -> FakeProvider:
    provider = FakeProvider("fake-local", [GenerationResult(text=json.dumps(payload), provider="fake", model="fake",
                                                            latency_ms=1.0, attempt=1, prompt_hash="x")])
    monkeypatch.setattr(shorts_service, "build_ai_router_from_settings",
                        lambda: AIRouter(primary=None, fallback=provider, mode=AIMode.LOCAL))
    return provider


def test_the_ai_clips_are_kept_only_when_complete_and_30_to_90_seconds(client, monkeypatch):  # noqa: F811
    project = _with_audio(client)
    provider = _router(monkeypatch, {"clips": [
        {"start_line": 2, "end_line": 6, "title": "Don't say this to a new neighbor!", "reason": "Small talk."},
        {"line_from": 4, "line_to": 8, "hook": "Overlaps the first", "reason": ""},   # overlaps: dropped
        {"line_from": 9, "line_to": 9, "hook": "Too short", "reason": ""},            # 7.5 s: dropped
        {"line_from": 7, "line_to": 11, "hook": "3 ways to ask for help", "reason": "Requests."},
    ]})
    clips = data(client.post(f"/api/projects/{project['id']}/shorts/propose", json={"count": 3}))
    assert [(clip["line_from"], clip["line_to"], clip["hook"]) for clip in clips] == [
        (2, 6, "Don't say this to a new neighbor!"), (7, 11, "3 ways to ask for help")]
    assert clips[0]["seconds"] == 39.5 and clips[0]["status"] == "proposed"
    assert "[2] 16.0-23.5" in provider.calls[0].prompt and "between\n   30 and 90 seconds" in provider.calls[0].prompt


def test_the_owner_edits_approves_and_cannot_render_a_proposed_clip(client):  # noqa: F811
    project = _with_audio(client)
    url = f"/api/projects/{project['id']}/shorts"
    clip = data(client.post(url, json={"line_from": 0, "line_to": 4, "hook": "Meet Lan and Minh"}))
    assert client.post(url, json={"line_from": 0, "line_to": 1, "hook": "Too short"}).status_code == 422
    assert client.patch(f"{url}/{clip['id']}", json={"line_to": 20}).status_code == 422
    assert client.post(f"{url}/{clip['id']}/render", json={}).status_code == 422  # approve first
    approved = data(client.patch(f"{url}/{clip['id']}", json={"status": "approved", "hook": "  Meet the neighbours  "}))
    assert approved["status"] == "approved" and approved["hook"] == "Meet the neighbours"
    moved = data(client.patch(f"{url}/{clip['id']}", json={"line_to": 5}))
    assert moved["status"] == "proposed"  # a changed passage is approved again


def test_the_shorts_and_tiktok_texts():
    project = {"cefr_level": "b1"}
    clip = {"hook": "Don't say this to a new neighbor!"}
    learning = {"vocabulary": [{"word": "acquaintance", "definition_vi": "người quen"}],
                "idioms": [{"phrase": "break the ice", "meaning_vi": "phá băng"}]}
    texts = shorts_service.packages(project, clip, learning, ["LearnEnglish", "DailyBeyondEnglish"], "https://youtu.be/full")
    assert texts["shorts"]["title"] == "Don't say this to a new neighbor! #Shorts"
    description = texts["shorts"]["description"]
    assert "• acquaintance — người quen" in description and "▶️ Full episode: https://youtu.be/full" in description
    assert description.endswith("#Shorts #LearnEnglish #DailyBeyondEnglish")
    caption = texts["tiktok"]["caption"]
    assert caption.startswith("Don't say this to a new neighbor! 🎧") and caption.count("#") <= 5
    long = shorts_service.packages(project, {"hook": "x" * 120}, None, [], "")
    assert len(long["shorts"]["title"]) <= shorts_service.SHORTS_TITLE_LIMIT and "Full episode on our channel" in \
        long["shorts"]["description"]


def test_a_clip_is_a_frame_range_of_the_vertical_episode():
    props = {"fps": 30, "introSec": 4.0, "outroSec": 5.0,
             "lines": [{"startSec": 8.0 * i, "endSec": 8.0 * i + 7.5} for i in range(12)]}
    assert video_renderer_remotion.clip_frames(props, 2, 6) == (round((4 + 16 - 0.6) * 30), round((4 + 55.5 + 0.8) * 30))
    first, last = video_renderer_remotion.clip_frames(props, 0, 11)
    assert first == round(3.4 * 30) and last <= round((4 + 95.5 + 5) * 30)


async def test_the_vertical_render_asks_remotion_for_1080x1920(monkeypatch, tmp_path):
    seen = {}

    async def fake(db, project, audio_job, learning, output_path, **kwargs):
        seen.update(kwargs)
        return {"mp4_path": str(output_path), "mode": "remotion"}

    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(video_service, "renderer_problem", lambda: None)
    monkeypatch.setattr(video_renderer_remotion, "render_via_remotion", fake)
    result = await video_service.render_vertical("p1", {"status": "complete"}, db=None, project={"id": "p1"},
                                                 clip={"line_from": 1, "line_to": 3, "hook": "Hi"})
    assert seen["layout"] == "vertical" and seen["clip"]["hook"] == "Hi" and result["mp4_path"].endswith("video_vertical.mp4")
