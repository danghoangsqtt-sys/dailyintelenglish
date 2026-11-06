"""Phase 99 (D168-D171): the Doodle story in the Channel plan, the batch and the night runner."""

from __future__ import annotations

from datetime import date

import pytest

from backend.ai.llm.contracts import AIMode, GenerationResult
from backend.ai.llm.fake_provider import FakeProvider
from backend.ai.llm.router import AIRouter
from backend.automation import runner as runner_module
from backend.automation.runner import OwnerStop, Producer
from backend.channel import batch_service
from backend.tests.test_automation import FakeClient, no_sleep
from backend.tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def failed(response, status=422):
    assert response.status_code == status, response.text
    return response.json()["error"]


# ---------------------------------------------------------------- series and projects (99.1)

def test_a_doodle_series_keeps_its_story_type_and_makes_a_doodle_project(client):  # noqa: F811
    narrator = locked_character("Nova", "yellow")
    topic = data(client.post("/api/channel/topics", json={"name": "Stories"}))
    url = f"/api/channel/topics/{topic['id']}/series"
    plain = data(client.post(url, json={"name": "Tales", "presentation_mode": "solo_explainer", "explainer_style": "doodle",
                                        "cast": [narrator]}))
    assert (plain["explainer_subject"], plain["duration_minutes"]) == ("story", 8.0)  # D168 defaults, like Step 1
    history = data(client.post(url, json={"name": "Moments", "presentation_mode": "solo_explainer", "explainer_style": "doodle",
                                          "explainer_subject": "history", "duration_minutes": 5, "cast": [narrator]}))
    assert (history["explainer_subject"], history["duration_minutes"]) == ("history", 5.0)
    assert "3-12 minutes" in failed(client.post(url, json={"name": "Long", "presentation_mode": "solo_explainer",
                                                          "explainer_style": "doodle", "duration_minutes": 15}))
    vox = data(client.post(url, json={"name": "Vox", "presentation_mode": "solo_explainer", "explainer_style": "vox",
                                      "explainer_subject": "myth"}))
    assert vox["explainer_subject"] is None  # another kind has no story type

    data(client.post(f"/api/channel/series/{history['id']}/episodes", json={"title": "The Moon Landing", "brief": "1969"}))
    created = data(client.post(f"/api/channel/series/{history['id']}/projects"))["created"]
    project = data(client.get(f"/api/projects/{created[0]['project_id']}"))
    assert (project["explainer_style"], project["explainer_subject"], project["duration_minutes"]) == ("doodle", "history", 5.0)


def test_a_series_changed_to_or_from_doodle_gets_or_loses_its_story_type(client):  # noqa: F811
    topic = data(client.post("/api/channel/topics", json={"name": "Mixed"}))
    series = data(client.post(f"/api/channel/topics/{topic['id']}/series", json={"name": "S", "duration_minutes": 20}))
    assert series["explainer_subject"] is None
    doodle = data(client.patch(f"/api/channel/series/{series['id']}",
                               json={"presentation_mode": "solo_explainer", "explainer_style": "doodle"}))
    assert (doodle["explainer_subject"], doodle["duration_minutes"]) == ("story", 8.0)  # 20 min is no Doodle length
    myth = data(client.patch(f"/api/channel/series/{series['id']}", json={"explainer_subject": "myth", "duration_minutes": 4}))
    assert (myth["explainer_subject"], myth["duration_minutes"]) == ("myth", 4.0)
    vox = data(client.patch(f"/api/channel/series/{series['id']}", json={"explainer_style": "vox"}))
    assert vox["explainer_subject"] is None


# ---------------------------------------------------------------- the batch (99.2)

async def test_doodle_ideas_ask_for_the_chosen_story_type(client):  # noqa: F811
    from backend.db.database import Database

    answer = '{"ideas": [{"title": "The Lighthouse Keeper", "brief": "A storm night"}, {"title": "Two Keys", "brief": "A door"}]}'
    fake = FakeProvider("fake", [GenerationResult(text=answer, provider="fake", model="m", latency_ms=1, attempt=1,
                                                  prompt_hash="h")])
    request = batch_service.IdeasRequest(topic="the sea", template="doodle", count=5, explainer_subject="myth")
    ideas = await batch_service.propose_ideas(Database.instance().connection, request,
                                              AIRouter(primary=fake, fallback=fake, mode=AIMode.CLOUD))
    assert [idea["title"] for idea in ideas] == ["The Lighthouse Keeper", "Two Keys"]
    assert batch_service.DOODLE_RULES["myth"] in fake.calls[0].prompt and "Doodle story" in fake.calls[0].prompt


def test_a_doodle_batch_is_a_dated_16x9_story_series(client):  # noqa: F811
    narrator = locked_character("Nova", "yellow")
    result = data(client.post("/api/shorts-batch/create", json={
        "topic_name": "Stories", "series_name": "Sea myths", "template": "doodle", "cast": [narrator], "cefr_level": "B1",
        "start_date": date(2026, 11, 10).isoformat(), "every_days": 7, "explainer_subject": "myth", "duration_minutes": 6,
        "items": [{"title": "The Lighthouse Keeper"}, {"title": "Two Keys"}]}))
    assert (result["episodes"], result["first_date"], result["last_date"]) == (2, "2026-11-10", "2026-11-17")
    series = next(s for topic in data(client.get("/api/channel"))["topics"] for s in topic["series"] if s["id"] == result["series_id"])
    assert (series["explainer_style"], series["explainer_subject"], series["duration_minutes"]) == ("doodle", "myth", 6.0)


# ---------------------------------------------------------------- the night runner (99.3)

class DoodleClient(FakeClient):
    """A Doodle project: its plan's picture slots are filled by the picture job unless `drawn` is False."""

    def __init__(self, subject, drawn=True, **kwargs):
        super().__init__(solo=True, flagged=True, **kwargs)
        self.subject, self.drawn, self.waits = subject, drawn, []

    async def call(self, method, path, body=None):
        tail = path.replace("/api/projects/p1", "")
        if tail == "" and method == "GET":
            self.calls.append((method, tail, body))
            return {"explainer_style": "doodle", "explainer_subject": self.subject, "duration_minutes": 3}
        if tail == "/explainer-plan/propose":
            await super().call(method, path, body)
            self.plan["segments"] = [{"id": "s1", "needs_fact_review": True, "visual": {"kind": "photo", "asset": None}}]
            self.plan["aspects"] = ["16:9"]
            return {"id": "job-plan"}
        if tail == "/explainer-plan/illustrate":
            self.calls.append((method, tail, body))
            if self.drawn:
                self.plan["segments"] = [{**s, "visual": {"kind": "photo", "asset": {"asset_id": "a"}}} for s in self.plan["segments"]]
                return {"id": "img", "status": "complete"}
            return {"id": "img", "status": "error", "error": "no image model"}
        if tail == "/explainer-plan" and method == "PATCH":
            self.calls.append((method, tail, body))
            self.plan = {**self.plan, "segments": body["segments"], "revision": 2}
            return {"plan": self.plan, "issues": []}
        if tail == "/explainer-plan":
            self.calls.append((method, tail, body))
            issues = ["Segment s1: review its knowledge claims and illustration text"] if self.plan and self.plan["status"] != "approved" \
                and any(s.get("needs_fact_review") for s in self.plan["segments"]) else []
            return {"plan": self.plan, "issues": issues, "current_source_fingerprint": "f"}
        return await super().call(method, path, body)


async def _solo(fake):
    async def on_step(step, project_id):
        pass

    await Producer(fake, sleep=no_sleep).produce({"id": "e", "project_id": "p1", "presentation_mode": "solo_explainer",
                                                  "explainer_style": "doodle"}, on_step)


async def test_an_original_story_skips_the_fact_check_and_is_approved():
    fake = DoodleClient("story")
    await _solo(fake)
    paths = [path for _method, path, _body in fake.calls]
    assert "/explainer-plan/fact-check" not in paths  # D170: fiction has no facts to check
    assert "/explainer-plan/approve" in paths and fake.done["video"]


async def test_a_myth_or_history_still_goes_through_the_fact_check():
    fake = DoodleClient("myth")
    with pytest.raises(OwnerStop, match="fact check doubts"):
        await _solo(fake)
    assert any(path == "/explainer-plan/fact-check" for _method, path, _body in fake.calls)
    ok = DoodleClient("history", facts="ok")
    await _solo(ok)
    assert ok.done["video"]


async def test_a_doodle_without_its_pictures_stops_for_the_owner():
    fake = DoodleClient("story", drawn=False)
    with pytest.raises(OwnerStop, match="story's pictures"):
        await _solo(fake)
    assert not fake.done["video"]  # D171: never rendered with cards in place of its pictures


async def test_a_doodle_picture_job_may_take_longer(monkeypatch):
    seen = []
    original = Producer.draw

    async def draw(self, project_id, path, timeout=runner_module.JOB_TIMEOUT_SECONDS):
        seen.append(timeout)
        return await original(self, project_id, path, timeout)

    monkeypatch.setattr(Producer, "draw", draw)
    await _solo(DoodleClient("story"))
    assert seen == [runner_module.DOODLE_PICTURE_TIMEOUT_SECONDS] and seen[0] > runner_module.JOB_TIMEOUT_SECONDS
