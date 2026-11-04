"""Phase 80 (owner 2026-10-26): "Make videos now" for a Shorts batch -- one after another, with progress and results that say
where each video is saved. The production steps are stubbed: the Producer itself is covered by test_automation."""

import time

from backend.automation import runner
from backend.automation.runner import StepError
from backend.tests.test_visuals_project_api import client, data, locked_character  # noqa: F401


def _batch(client, titles):  # noqa: F811
    narrator = locked_character("Narrator", "red")
    body = {"topic_name": "Shorts", "series_name": "Office words", "template": "wordday", "cast": [narrator], "cefr_level": "B1",
            "start_date": "2026-10-27", "every_days": 1, "make_projects": False,
            "items": [{"title": title, "brief": ""} for title in titles]}
    return data(client.post("/api/shorts-batch/create", json=body))["series_id"]


def _wait(client, series_id, seconds=20):  # noqa: F811
    deadline = time.time() + seconds
    while time.time() < deadline:
        view = data(client.get(f"/api/shorts-batch/series/{series_id}/results"))
        if not view["running"]:
            return view
        time.sleep(0.1)
    raise AssertionError("the batch did not finish")


def test_make_now_makes_every_short_and_one_failure_does_not_stop_the_rest(client, monkeypatch):  # noqa: F811
    series_id = _batch(client, ["Follow up", "Circle back", "ASAP"])
    seen = []

    async def produce(self, episode, on_step):
        seen.append(episode["title"])
        created = await self.client.call("POST", f"/api/channel/series/{episode['series_id']}/projects")
        project_id = next(item["project_id"] for item in created["created"] if item["episode_id"] == episode["id"]) \
            if created["created"] else None
        await on_step("script", project_id)
        if episode["title"] == "Circle back":
            raise StepError("The AI job ended: error")
        await on_step("video", project_id)
        return project_id

    monkeypatch.setattr(runner.Producer, "produce", produce)
    started = data(client.post(f"/api/shorts-batch/series/{series_id}/make"))
    assert started["started"] and started["videos"] == 3
    view = _wait(client, series_id)
    assert seen == ["Follow up", "Circle back", "ASAP"]
    by_title = {item["title"]: item for item in view["items"]}
    assert by_title["Follow up"]["status"] == "waiting_review" and by_title["ASAP"]["status"] == "waiting_review"
    assert by_title["Circle back"]["status"] == "needs_attention" and "AI job" in by_title["Circle back"]["message"]
    assert all(item["project_id"] for item in view["items"])
    batches = data(client.get("/api/shorts-batch/series"))["series"]
    assert any(batch["id"] == series_id and batch["episodes"] == 3 for batch in batches)


def test_results_show_the_folder_under_the_main_folder(client, monkeypatch, tmp_path):  # noqa: F811
    data(client.put("/api/settings/main-folder", json={"output_dir": str(tmp_path / "Videos")}))
    series_id = _batch(client, ["Pivot"])

    async def produce(self, episode, on_step):
        created = await self.client.call("POST", f"/api/channel/series/{episode['series_id']}/projects")
        return created["created"][0]["project_id"]

    monkeypatch.setattr(runner.Producer, "produce", produce)
    data(client.post(f"/api/shorts-batch/series/{series_id}/make"))
    item = _wait(client, series_id)["items"][0]
    assert item["folder"].startswith(str(tmp_path / "Videos")) and "Pivot" in item["folder"]
    assert item["video_url"] is None  # nothing rendered by the stub


def test_an_unknown_batch_is_404(client):  # noqa: F811
    assert client.get("/api/shorts-batch/series/nope/results").status_code == 404
