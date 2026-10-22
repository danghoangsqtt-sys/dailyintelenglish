"""Phase 62 (ENH-044): automatic production -- the rules, the API and the runner (with a fake step client)."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from backend.automation import automation_service as service
from backend.automation import rules, runner as runner_module
from backend.automation.runner import AutomationRunner, Producer, StepError
from tests.test_visuals_project_api import client, data  # noqa: F401


# ---------------------------------------------------------------- rules

def test_the_window_runs_across_midnight_and_a_full_day():
    def at(hour, minute=0):
        return datetime(2026, 10, 22, hour, minute)
    assert rules.in_window(at(23, 30), "23:00", "06:00") and rules.in_window(at(5, 59), "23:00", "06:00")
    assert not rules.in_window(at(6), "23:00", "06:00") and not rules.in_window(at(12), "23:00", "06:00")
    assert rules.in_window(at(13), "09:00", "17:00") and not rules.in_window(at(8, 59), "09:00", "17:00")
    assert rules.in_window(at(3), "00:00", "00:00")
    assert rules.window_started(at(2), "23:00", "06:00") == datetime(2026, 10, 21, 23, 0)
    assert rules.window_started(at(23, 10), "23:00", "06:00") == datetime(2026, 10, 22, 23, 0)
    with pytest.raises(ValueError):
        rules.parse_clock("7pm")


def test_due_episodes_are_unpublished_unfinished_and_soonest_first():
    episodes = [
        {"id": "late", "publish_date": "2026-10-20", "status": "created", "finished": False, "number": 2},
        {"id": "soon", "publish_date": "2026-10-24", "status": "planned", "finished": False, "number": 1},
        {"id": "far", "publish_date": "2026-11-30", "status": "planned", "finished": False},
        {"id": "done", "publish_date": "2026-10-23", "status": "created", "finished": True},
        {"id": "published", "publish_date": "2026-10-21", "status": "published", "finished": False},
        {"id": "undated", "publish_date": None, "status": "planned", "finished": False},
    ]
    assert [item["id"] for item in rules.due_episodes(episodes, date(2026, 10, 22), 3)] == ["late", "soon"]


def test_the_next_step_follows_the_production_order():
    flags = dict.fromkeys(("script", "learning", "audio", "video", "thumbnail", "youtube"), False)
    assert rules.next_step(None, has_visual_plan=False) == "project"
    assert rules.next_step(flags, has_visual_plan=False) == "script"
    flags.update(script=True, learning=True, audio=True)
    assert rules.next_step(flags, has_visual_plan=False) == "visual_plan"
    assert rules.next_step(flags, has_visual_plan=True) == "video"
    flags.update(video=True, thumbnail=True)
    assert rules.next_step(flags, has_visual_plan=False) == "youtube"
    flags["youtube"] = True
    assert rules.next_step(flags, has_visual_plan=False) is None


# ---------------------------------------------------------------- API

def test_settings_round_trip_and_validation(client):  # noqa: F811
    view = data(client.get("/api/automation"))
    assert view["settings"] == {"enabled": False, "window_start": "23:00", "window_end": "06:00", "days_ahead": 3,
                                "max_per_night": 2, "start_with_windows": False, "keep_awake": True}
    assert view["queue"] == [] and view["runs"] == [] and view["startup_available"] is False
    saved = data(client.put("/api/automation/settings", json={"enabled": True, "window_start": "22:30", "max_per_night": 4}))
    assert (saved["settings"]["enabled"], saved["settings"]["window_start"], saved["settings"]["max_per_night"]) == (True, "22:30", 4)
    assert client.put("/api/automation/settings", json={"window_end": "25:99"}).status_code == 422
    assert client.put("/api/automation/settings", json={"max_per_night": 0}).status_code == 422
    # the dev app is not the installed app: it cannot open itself with Windows
    response = client.put("/api/automation/settings", json={"start_with_windows": True})
    assert response.status_code == 422 and "installed app" in response.json()["error"]
    assert client.get("/automation").status_code == 200


def test_the_queue_lists_the_due_channel_episodes(client):  # noqa: F811
    topic = data(client.post("/api/channel/topics", json={"name": "Daily Life"}))
    series = data(client.post(f"/api/channel/topics/{topic['id']}/series", json={"name": "Mornings", "genre": "small_talk"}))
    first = data(client.post(f"/api/channel/series/{series['id']}/episodes", json={"title": "Coffee"}))
    second = data(client.post(f"/api/channel/series/{series['id']}/episodes", json={"title": "Bus"}))
    today = date.today().isoformat()
    data(client.patch(f"/api/channel/episodes/{first['id']}", json={"publish_date": today}))
    data(client.patch(f"/api/channel/episodes/{second['id']}", json={"publish_date": "2099-01-01"}))
    queue = data(client.get("/api/automation"))["queue"]
    assert [(item["title"], item["series"]) for item in queue] == [("Coffee", "Mornings")]


# ---------------------------------------------------------------- producer

class FakeClient:
    """The app API as the producer sees it: each step call marks its step done."""

    def __init__(self, solo=False, issues=None, flagged=False, fail_on=None):
        self.calls, self.solo = [], solo
        self.done = dict.fromkeys(("script", "learning", "audio", "video", "thumbnail", "youtube"), False)
        self.plan = None
        self.issues, self.flagged, self.fail_on = issues or [], flagged, fail_on
        self.beats = []

    async def call(self, method, path, body=None):
        self.calls.append((method, path.replace("/api/projects/p1", ""), body))
        tail = path.replace("/api/projects/p1", "")
        if self.fail_on and self.fail_on in tail:
            raise StepError("The render failed")
        if tail == "/progress":
            return {"steps": [{"key": key, "done": value} for key, value in self.done.items()]}
        if tail == "/ai-jobs":
            self.done[body["operation"]] = True
            return {"id": f"job-{body['operation']}"}
        if tail.startswith("/ai-jobs/"):
            return {"status": "complete"}
        if tail == "/script":
            return [{"id": "l1"}, {"id": "l2"}]
        if tail == "/audio/generate":
            self.done["audio"] = True
        if tail == "/storyboard":
            return {"beats": self.beats}
        if tail == "/storyboard/propose":
            self.beats = [{"id": "b"}]
        if tail == "/explainer-plan":
            return {"plan": self.plan, "issues": self.issues}
        if tail == "/explainer-plan/propose":
            self.plan = {"revision": 1, "status": "draft", "source_fingerprint": "f",
                         "segments": [{"id": "s1", "needs_fact_review": self.flagged}]}
            return {"id": "job-plan"}
        if tail == "/explainer-plan/approve":
            self.plan = {**self.plan, "status": "approved"}
        if tail == "/video/generate":
            self.done["video"] = True
        if tail == "/thumbnails":
            return []
        if tail == "/thumbnails/generate":
            return [{"id": "t1"}, {"id": "t2"}]
        if tail.endswith("/favorite"):
            self.done["thumbnail"] = True
        if tail == "/youtube/generate":
            self.done["youtube"] = True
        return {}


async def no_sleep(_seconds):
    return None


async def test_a_conversation_is_made_in_order_up_to_the_youtube_package():
    fake, steps = FakeClient(), []

    async def on_step(step, project_id):
        steps.append(step)

    project = await Producer(fake, sleep=no_sleep).produce({"id": "e1", "project_id": "p1"}, on_step)
    assert project == "p1"
    assert steps == ["script", "learning", "audio", "visual_plan", "video", "thumbnail", "youtube"]
    writes = [path for method, path, _ in fake.calls if method != "GET"]
    assert writes == ["/ai-jobs", "/ai-jobs", "/tts/preview", "/tts/preview", "/audio/generate", "/storyboard/propose",
                      "/video/generate", "/thumbnails/generate", "/thumbnails/t1/favorite", "/youtube/generate"]
    # a second pass finds everything made and does nothing
    fake.calls.clear()
    await Producer(fake, sleep=no_sleep).produce({"id": "e1", "project_id": "p1"}, on_step)
    assert [method for method, *_ in fake.calls] == ["GET"]


async def test_a_solo_plan_is_approved_only_without_issues_or_facts_to_check():
    async def on_step(step, project_id):
        pass

    fake = FakeClient(solo=True)
    await Producer(fake, sleep=no_sleep).produce({"id": "e", "project_id": "p1", "presentation_mode": "solo_explainer"}, on_step)
    assert ("POST", "/explainer-plan/approve", {"expected_revision": 1, "source_fingerprint": "f"}) in fake.calls
    flagged = FakeClient(solo=True, flagged=True)
    with pytest.raises(StepError, match="Check the facts"):
        await Producer(flagged, sleep=no_sleep).produce({"id": "e", "project_id": "p1", "presentation_mode": "solo_explainer"}, on_step)
    assert not any(path == "/explainer-plan/approve" for _, path, _ in flagged.calls)
    troubled = FakeClient(solo=True, issues=["A segment has no anchor"])
    with pytest.raises(StepError, match="no anchor"):
        await Producer(troubled, sleep=no_sleep).produce({"id": "e", "project_id": "p1", "presentation_mode": "solo_explainer"}, on_step)
    assert troubled.done["video"] is False


async def test_a_failed_ai_job_is_asked_once_more_then_stops_the_episode():
    class Flaky(FakeClient):
        failures = 1

        async def call(self, method, path, body=None):
            if path.endswith("/ai-jobs/job-script") and self.failures:
                self.failures -= 1
                self.calls.append((method, path, body))
                return {"status": "error", "error_message": "total word count 135 is outside ±10% of target 111"}
            return await super().call(method, path, body)

    async def on_step(step, project_id):
        pass

    flaky = Flaky()
    await Producer(flaky, sleep=no_sleep).produce({"id": "e", "project_id": "p1"}, on_step)
    assert [path for method, path, _ in flaky.calls if path == "/ai-jobs"].count("/ai-jobs") == 3  # script twice, learning once
    stubborn = Flaky()
    stubborn.failures = 5
    with pytest.raises(StepError, match="word count"):
        await Producer(stubborn, sleep=no_sleep).produce({"id": "e", "project_id": "p1"}, on_step)


async def test_a_language_short_accepts_the_generic_review_flag_but_news_waits():
    async def on_step(step, project_id):
        pass

    class Reviewing(FakeClient):
        async def call(self, method, path, body=None):
            tail = path.replace("/api/projects/p1", "")
            if tail == "/explainer-plan" and method == "GET":
                self.calls.append((method, tail, body))
                flagged = self.plan and any(s["needs_fact_review"] for s in self.plan["segments"])
                return {"plan": self.plan, "current_source_fingerprint": "f", "issues": self.issues + (
                    ["Segment s1: review its knowledge claims and illustration text"] if flagged else [])}
            if tail == "/explainer-plan" and method == "PATCH":
                self.calls.append((method, tail, body))
                self.plan = {**self.plan, "revision": 2, "segments": body["segments"], "aspects": body["aspects"]}
                return {"plan": self.plan, "current_source_fingerprint": "f", "issues": self.issues}
            if tail == "/explainer-plan/propose":
                await super().call(method, path, body)
                self.plan["aspects"] = ["9:16"]
                return {"id": "job-plan"}
            return await super().call(method, path, body)

    mistakes = Reviewing(solo=True, flagged=True)
    await Producer(mistakes, sleep=no_sleep).produce(
        {"id": "e", "project_id": "p1", "presentation_mode": "solo_explainer", "explainer_style": "mistakes"}, on_step)
    patch = next(body for method, path, body in mistakes.calls if method == "PATCH")
    assert all(not segment["needs_fact_review"] for segment in patch["segments"])
    assert ("POST", "/explainer-plan/approve", {"expected_revision": 2, "source_fingerprint": "f"}) in mistakes.calls
    assert mistakes.done["youtube"]
    news = Reviewing(solo=True, flagged=True)
    with pytest.raises(StepError, match="review its knowledge claims"):
        await Producer(news, sleep=no_sleep).produce(
            {"id": "e", "project_id": "p1", "presentation_mode": "solo_explainer", "explainer_style": "news"}, on_step)
    assert not any(method == "PATCH" for method, *_ in news.calls)
    other = Reviewing(solo=True, flagged=True, issues=["Segment s1: import or select its illustration"])
    with pytest.raises(StepError, match="import or select"):
        await Producer(other, sleep=no_sleep).produce(
            {"id": "e", "project_id": "p1", "presentation_mode": "solo_explainer", "explainer_style": "quiz"}, on_step)
    assert not any(method == "PATCH" for method, *_ in other.calls)


# ---------------------------------------------------------------- runner

class FakeProducer:
    outcomes: dict = {}
    made: list = []

    def __init__(self, step_client, sleep=None):
        pass

    async def produce(self, episode, on_step):
        await on_step("script", episode.get("project_id") or "p-" + episode["id"])
        outcome = self.outcomes.get(episode["id"], "ok")
        FakeProducer.made.append(episode["id"])
        if outcome == "attention":
            raise StepError("Check the facts")
        if outcome == "boom":
            raise RuntimeError("disk on fire")
        return "p-" + episode["id"]


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


@pytest.fixture
def episodes(monkeypatch):
    items = [{"id": f"e{n}", "number": n, "title": f"T{n}", "series": "S", "series_id": "s", "publish_date": "2026-10-22",
              "status": "planned", "finished": False, "project_id": None, "presentation_mode": "classic"} for n in (1, 2, 3, 4)]

    async def fake_episodes(db):
        return items

    monkeypatch.setattr(service, "episodes", fake_episodes)
    monkeypatch.setattr(runner_module, "Producer", FakeProducer)
    monkeypatch.setattr(AutomationRunner, "_backup", lambda self: None)
    FakeProducer.made, FakeProducer.outcomes = [], {}
    return items


async def test_the_runner_makes_due_episodes_in_the_window_up_to_the_nightly_limit(db, episodes):
    await service.update_settings(db, {"enabled": True, "max_per_night": 2})
    await db.commit()
    clock = Clock(datetime(2026, 10, 22, 12, 0))
    runner = AutomationRunner(app=None, db_provider=lambda: db, clock=clock)
    await runner.tick()
    assert FakeProducer.made == [] and runner.run_id is None  # outside the window
    FakeProducer.outcomes = {"e1": "attention", "e2": "boom"}
    clock.value = datetime(2026, 10, 22, 23, 30)
    for _ in range(6):
        await runner.tick()
    # e1 needs attention, e2 errors, e3 and e4 are made: the limit counts finished videos only
    assert FakeProducer.made == ["e1", "e2", "e3", "e4"]
    report = await service.report(db)
    assert len(report) == 1 and report[0]["status"] == "done"
    assert [(item["episode_id"], item["status"]) for item in report[0]["items"]] == [
        ("e1", "needs_attention"), ("e2", "error"), ("e3", "waiting_review"), ("e4", "waiting_review")]
    assert report[0]["items"][2]["link"] == "/step7?project_id=p-e3"
    assert "disk on fire" in report[0]["items"][1]["message"]
    # the same night does not start again, even after a restart of the app
    again = AutomationRunner(app=None, db_provider=lambda: db, clock=clock)
    await again.tick()
    assert FakeProducer.made == ["e1", "e2", "e3", "e4"]


async def test_run_now_works_outside_the_window_and_stop_ends_the_run(db, episodes):
    await service.update_settings(db, {"enabled": False, "max_per_night": 1})
    await db.commit()
    runner = AutomationRunner(app=None, db_provider=lambda: db, clock=Clock(datetime(2026, 10, 22, 12, 0)))
    runner.request_run_now()
    for _ in range(3):
        await runner.tick()
    assert FakeProducer.made == ["e1"] and runner.run_id is None and not runner.manual
    runs = await service.report(db)
    assert runs[0]["trigger"] == "manual" and runs[0]["status"] == "done"
    runner.request_run_now()
    await runner.tick()  # begins and makes one
    runner.request_stop()
    await runner.tick()
    assert (await service.report(db))[0]["status"] in ("done", "stopped") and runner.run_id is None


async def test_a_run_cut_by_a_restart_is_closed_on_start(db, episodes):
    run = await service.create_run(db, "schedule")
    await db.commit()
    runner = AutomationRunner(app=None, db_provider=lambda: db)
    await runner.start()
    await runner.stop()
    report = await service.report(db)
    assert report[0]["id"] == run["id"] and report[0]["status"] == "stopped"


def test_the_board_state_and_kind_of_an_episode():
    base = {"status": "created", "review_status": "", "finished": False, "project_id": "p"}
    assert service.state_of({**base, "project_id": None}, None) == "planned"
    assert service.state_of(base, None) == "in_progress"
    assert service.state_of(base, {"status": "running"}) == "making"
    assert service.state_of(base, {"status": "needs_attention"}) == "needs_attention"
    assert service.state_of({**base, "finished": True}, {"status": "waiting_review"}) == "waiting_review"
    assert service.state_of({**base, "finished": True, "review_status": "approved"}, None) == "approved"
    assert service.state_of({**base, "review_status": "changes"}, None) == "changes"
    assert service.state_of({**base, "status": "published", "review_status": "approved"}, None) == "published"
    assert service.kind_of("classic", "presenter") == "Conversation" and service.kind_of("classic", "chat") == "Short · chat"
    assert service.kind_of("solo_explainer", "presenter") == "Solo" and service.kind_of("solo_explainer", "quiz") == "Short · quiz"
