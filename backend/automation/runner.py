"""Phase 62 (ENH-044): the background runner of automatic production.

Once in a while it looks whether it may work (enabled and inside the night window, or a "Run now"), then makes the due
Channel plan episodes one at a time -- through the app's own HTTP API, in process, so every step does exactly what its
step page does (same validation, locks and jobs). Each step starts from where the project is, so a stop, a crash or a
restart repeats nothing that is done, and hand-made work is never redone. An episode whose step fails, or whose Solo plan
has an issue or a fact to check, stops at that step with the reason; the runner goes on with the next episode.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx

from backend.automation import automation_service as service
from backend.automation import rules
from backend.core.config import settings
from backend.core.constants import THUMBNAIL_MIN_VARIANTS
from backend.db.transactions import read_transaction, write_transaction

logger = logging.getLogger(__name__)

TICK_SECONDS = 30
JOB_POLL_SECONDS = 3
JOB_TIMEOUT_SECONDS = 1800
MIN_FREE_BYTES = 3 * 1024 ** 3
KEEP_BACKUPS = 7
# Phase 66 (owner 2026-10-22): the English-teaching Shorts whose generic "review its knowledge claims" flag the night run
# may accept (their content is English, not facts or numbers); news, VOX and Solo presenter videos still wait for a person,
# and any specific issue (numbers not said, a missing picture...) always stops the episode.
GENERIC_REVIEW = "review its knowledge claims and illustration text"
SELF_REVIEW_STYLES = ("mistakes", "wordday", "top5", "quiz", "listen", "blur")
THUMBNAIL_VARIANTS = THUMBNAIL_MIN_VARIANTS  # the composed template's smallest batch
AI_ATTEMPTS = 2


class StepError(Exception):
    """A step that cannot go on by itself: the item stops with this message for the owner."""


class StepClient:
    """The app's own API, called in process (no network, no port)."""

    def __init__(self, app: Any) -> None:
        self._client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://automation",
                                         timeout=httpx.Timeout(None))

    async def call(self, method: str, path: str, body: Any = None) -> Any:
        response = await self._client.request(method, path, json=body)
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400:
            raise StepError(str(payload.get("error") or payload.get("detail") or f"{method} {path} failed ({response.status_code})"))
        return payload.get("data")

    async def close(self) -> None:
        await self._client.aclose()


class Producer:
    """Makes one project step by step through a `StepClient` (kept apart from the loop so the tests drive it)."""

    def __init__(self, client: Any, sleep: Callable[[float], Any] = asyncio.sleep) -> None:
        self.client = client
        self.sleep = sleep

    async def wait_job(self, project_id: str, job: dict) -> None:
        waited = 0.0
        while True:
            current = await self.client.call("GET", f"/api/projects/{project_id}/ai-jobs/{job['id']}")
            if current["status"] == "complete":
                return
            if current["status"] in ("error", "stale", "cancelled"):
                raise StepError(current.get("error_message") or f"The AI job ended: {current['status']}")
            if waited >= JOB_TIMEOUT_SECONDS:
                raise StepError("The AI job took too long")
            await self.sleep(JOB_POLL_SECONDS)
            waited += JOB_POLL_SECONDS

    async def progress(self, project_id: str) -> dict[str, bool]:
        data = await self.client.call("GET", f"/api/projects/{project_id}/progress")
        return {step["key"]: bool(step["done"]) for step in data["steps"]}

    async def solo_plan(self, project_id: str) -> dict:
        return await self.client.call("GET", f"/api/projects/{project_id}/explainer-plan")

    async def has_visual_plan(self, project_id: str, solo: bool, style: str | None = None) -> bool:
        if not solo and style in ("chat", "wyr"):  # Phase 65: drawn from the script lines, no storyboard
            return True
        if solo:
            plan = (await self.solo_plan(project_id)).get("plan")
            return bool(plan and plan.get("status") == "approved")
        board = await self.client.call("GET", f"/api/projects/{project_id}/storyboard")
        return bool(board.get("beats"))

    async def run_step(self, step: str, project_id: str, solo: bool, style: str | None = None) -> None:
        call = self.client.call
        base = f"/api/projects/{project_id}"
        if step in ("script", "learning"):
            # nobody is at the computer: an AI answer that fails a check (length, format) is asked once more
            for attempt in range(AI_ATTEMPTS):
                try:
                    await self.wait_job(project_id, await call("POST", f"{base}/ai-jobs", {"operation": step}))
                    return
                except StepError:
                    if attempt == AI_ATTEMPTS - 1:
                        raise
        elif step == "audio":
            for line in await call("GET", f"{base}/script"):
                await call("POST", f"{base}/tts/preview", {"line_id": line["id"], "reuse_cached": True})
            await call("POST", f"{base}/audio/generate", {"background_music": None})
        elif step == "visual_plan":
            await (self.approve_solo(project_id, style) if solo else call("POST", f"{base}/storyboard/propose"))
        elif step == "video":
            await call("POST", f"{base}/video/generate", {})
        elif step == "thumbnail":
            await self.thumbnail(project_id)
        elif step == "youtube":
            await call("POST", f"{base}/youtube/generate")
        else:
            raise StepError(f"Unknown step {step}")

    async def approve_solo(self, project_id: str, style: str | None = None) -> None:
        """Propose a plan when there is none (or it went stale), then approve it -- only with no issue and no fact to check,
        exactly what a person could approve; otherwise stop for the owner. A plan the owner edited is kept, not redone."""
        view = await self.solo_plan(project_id)
        plan = view.get("plan")
        if not plan or plan.get("status") == "stale":
            job = await self.client.call("POST", f"/api/projects/{project_id}/explainer-plan/propose",
                                         {"expected_revision": plan["revision"] if plan else 0})
            await self.wait_job(project_id, job)
            view = await self.solo_plan(project_id)
            plan = view.get("plan")
        if not plan:
            raise StepError("The AI did not propose a visual plan")
        if style in SELF_REVIEW_STYLES and plan.get("status") != "approved":
            view, plan = await self.accept_generic_review(project_id, view)
        if view.get("issues"):
            raise StepError("Review the visual plan: " + "; ".join(map(str, view["issues"])))
        flagged = [segment.get("id") for segment in plan.get("segments", []) if segment.get("needs_fact_review")]
        if flagged:
            raise StepError(f"Check the facts of {len(flagged)} segment(s) on Step 5, then approve the plan")
        await self.client.call("POST", f"/api/projects/{project_id}/explainer-plan/approve",
                               {"expected_revision": plan["revision"], "source_fingerprint": plan["source_fingerprint"]})

    async def accept_generic_review(self, project_id: str, view: dict) -> tuple[dict, dict]:
        """Save the plan with the generic fact-review flag cleared (as the owner would on Step 5), when that flag is the only
        issue kind; any other issue is left for `approve_solo` to stop on."""
        plan = view["plan"]
        issues = [str(issue) for issue in view.get("issues") or []]
        if not any(GENERIC_REVIEW in issue for issue in issues) and not any(s.get("needs_fact_review") for s in plan.get("segments", [])):
            return view, plan
        if any(GENERIC_REVIEW not in issue for issue in issues):
            return view, plan
        segments = [{**segment, "needs_fact_review": False} for segment in plan.get("segments", [])]
        saved = await self.client.call("PATCH", f"/api/projects/{project_id}/explainer-plan", {
            "expected_revision": plan["revision"], "expected_source_fingerprint": view["current_source_fingerprint"],
            "segments": segments, "aspects": plan["aspects"]})
        return saved, saved["plan"]

    async def thumbnail(self, project_id: str) -> None:
        base = f"/api/projects/{project_id}/thumbnails"
        existing = await self.client.call("GET", base)
        items = existing if isinstance(existing, list) else (existing or {}).get("thumbnails", [])
        if not items:
            made = await self.client.call("POST", f"{base}/generate",
                                          {"template_name": "composed", "variant_count": THUMBNAIL_VARIANTS})
            items = made if isinstance(made, list) else (made or {}).get("thumbnails", [])
        if not items:
            raise StepError("No thumbnail was made")
        await self.client.call("PUT", f"{base}/{items[0]['id']}/favorite")

    async def produce(self, episode: dict, on_step: Callable[[str, str | None], Any]) -> str:
        """Make an episode up to "waiting for review". Returns the project id. Raises StepError to stop the episode."""
        solo = episode.get("presentation_mode") == "solo_explainer"
        project_id = episode.get("project_id")
        if not project_id:
            await on_step("project", None)
            created = await self.client.call("POST", f"/api/channel/series/{episode['series_id']}/projects")
            project_id = next((item["project_id"] for item in created.get("created", []) if item["episode_id"] == episode["id"]), None)
            if not project_id:
                raise StepError("The project for this episode could not be created")
        for _attempt in range(len(rules.STEPS) + 2):
            progress = await self.progress(project_id)
            step = rules.next_step(progress, has_visual_plan=progress.get("video") or await self.has_visual_plan(
                project_id, solo, episode.get("explainer_style")))
            if step is None:
                return project_id
            await on_step(step, project_id)
            await self.run_step(step, project_id, solo, episode.get("explainer_style"))
        raise StepError("A step did not finish")


_runner: "AutomationRunner | None" = None


def get_runner() -> "AutomationRunner | None":
    return _runner


def set_runner(runner: "AutomationRunner | None") -> None:
    global _runner
    _runner = runner


class AutomationRunner:
    """The loop: started in the app lifespan, one tick every 30 s."""

    def __init__(self, app: Any, db_provider: Callable[[], Any], clock: Callable[[], datetime] = datetime.now) -> None:
        self.app = app
        self.db_provider = db_provider
        self.clock = clock
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()  # Run now / Stop act at once, not at the next tick
        self.manual = False
        self.stop_requested = False
        self.current: dict | None = None  # the episode being made, for the page
        self.run_id: str | None = None
        self._window_key: str | None = None
        self._awake = False

    async def start(self) -> None:
        async with write_transaction(self.db_provider()):
            for run in await service.running_runs(self.db_provider()):  # a run cut by a crash or a restart
                await service.finish_run(self.db_provider(), run["id"], "stopped", "The app was closed during the run.")
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        self._keep_awake(False)

    def request_run_now(self) -> None:
        self.manual = True
        self.stop_requested = False
        self._wake.set()

    def request_stop(self) -> None:
        self.stop_requested = True
        self.manual = False
        self._wake.set()

    @property
    def busy(self) -> bool:
        return self.current is not None

    async def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:  # never let one bad tick end the loop
                logger.exception("automation tick failed")
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=TICK_SECONDS if not self.manual else 1)
            except asyncio.TimeoutError:
                pass
            self._wake.clear()

    async def tick(self) -> None:
        db = self.db_provider()
        async with read_transaction():
            config = await service.get_settings(db)
        now = self.clock()
        inside = config["enabled"] and rules.in_window(now, config["window_start"], config["window_end"])
        working = (inside or self.manual) and not self.stop_requested
        self._keep_awake(working and config["keep_awake"])
        if not working:
            if self.run_id:
                await self._finish("stopped" if self.stop_requested else "done")
            if not inside:
                self.stop_requested = False
            return
        key = "manual" if self.manual else rules.window_started(now, config["window_start"], config["window_end"]).isoformat()
        if self.run_id and key != self._window_key:
            await self._finish("done")
        if not self.run_id:
            if key == self._window_key and not self.manual:
                return  # this night's run is over (limit reached or nothing to do)
            await self._begin(key)
            if not self.run_id:
                return
        async with read_transaction():
            # the whole night counts (a restart inside the window does not reset the limit); "Run now" counts itself
            items = (await service.run_items(db, self.run_id) if key == "manual" else await service.items_since(
                db, rules.window_started(now, config["window_start"], config["window_end"]).astimezone(timezone.utc).isoformat()))
            queue = await service.due(db, now.date(), int(config["days_ahead"]))
        made = sum(1 for item in items if item["status"] == "waiting_review")
        tried = {item["episode_id"] for item in items}
        todo = [episode for episode in queue if episode["id"] not in tried]
        if made >= int(config["max_per_night"]) or not todo:
            await self._finish("done", "" if todo else "Nothing more is due.")
            return
        await self._make(todo[0])

    async def _begin(self, key: str) -> None:
        db = self.db_provider()
        problem = self._space_problem()
        async with write_transaction(db):
            run = await service.create_run(db, "manual" if self.manual else "schedule",
                                           self.clock().astimezone(timezone.utc).isoformat())
            if problem:
                await service.finish_run(db, run["id"], "error", problem)
        self._window_key = key
        if problem:
            self.manual = False
            return
        self.run_id = run["id"]
        await asyncio.to_thread(self._backup)

    async def _finish(self, status: str, message: str = "") -> None:
        db = self.db_provider()
        async with write_transaction(db):
            await service.finish_run(db, self.run_id, status, message)
            items = await service.run_items(db, self.run_id)
        self.run_id = None
        if self.manual:
            self._window_key = None
        self.manual = False
        self._keep_awake(False)
        if items:
            self._notify(items)

    async def _make(self, episode: dict) -> None:
        db = self.db_provider()
        async with write_transaction(db):
            item_id = await service.start_item(db, self.run_id, episode)
        self.current = {**episode, "step": ""}

        async def on_step(step: str, project_id: str | None) -> None:
            if self.stop_requested:
                raise StepError("Stopped by you; it goes on from this step next time.")
            self.current = {**episode, "step": step, "project_id": project_id}
            async with write_transaction(db):
                await service.update_item(db, item_id, step=step, project_id=project_id)

        client = StepClient(self.app)
        try:
            project_id = await Producer(client).produce(episode, on_step)
            status, message, project = "waiting_review", "Ready: watch it and publish it on YouTube.", project_id
        except StepError as exc:
            status, message, project = "needs_attention", str(exc), (self.current or {}).get("project_id")
        except Exception as exc:  # an unexpected failure stops this episode only
            logger.exception("automation item failed")
            status, message, project = "error", str(exc) or exc.__class__.__name__, (self.current or {}).get("project_id")
        finally:
            await client.close()
            self.current = None
        async with write_transaction(db):
            await service.update_item(db, item_id, status=status, message=message[:1000], project_id=project)

    def _space_problem(self) -> str:
        try:
            free = shutil.disk_usage(settings.DATA_DIR).free
        except OSError:
            return ""
        return "" if free >= MIN_FREE_BYTES else f"Only {free / 1024 ** 3:.1f} GB free on the data drive; free some space first."

    def _backup(self) -> None:
        """A consistent copy of the database before the run; the last 7 are kept."""
        folder = Path(settings.DATA_DIR) / "backups" / "automation"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"app-{self.clock().strftime('%Y%m%d-%H%M%S')}.db"
        with sqlite3.connect(settings.db_path) as source, sqlite3.connect(target) as copy:
            source.backup(copy)
        for old in sorted(folder.glob("app-*.db"))[:-KEEP_BACKUPS]:
            old.unlink(missing_ok=True)

    def _keep_awake(self, wanted: bool) -> None:
        """Windows: keep the computer from sleeping while the runner works (released otherwise)."""
        if wanted == self._awake or sys.platform != "win32":
            self._awake = wanted if sys.platform == "win32" else False
            return
        import ctypes

        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if wanted else 0))
        self._awake = wanted

    def _notify(self, items: list[dict]) -> None:
        """A Windows notification with the run's result (best effort; nothing happens elsewhere or on failure)."""
        if sys.platform != "win32" or getattr(settings, "TESTING", False):
            return
        ready = sum(item["status"] == "waiting_review" for item in items)
        stuck = len(items) - ready
        text = f"{ready} video(s) ready for review" + (f", {stuck} need your attention" if stuck else "")
        script = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;"
            "$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
            "$n = $t.GetElementsByTagName('text'); $n.Item(0).AppendChild($t.CreateTextNode('Daily Beyond English')) | Out-Null;"
            f"$n.Item(1).AppendChild($t.CreateTextNode('{text}')) | Out-Null;"
            "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
            "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app).Show([Windows.UI.Notifications.ToastNotification]::new($t))"
        )
        try:
            subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError:
            pass

    def status(self) -> dict:
        return {"running": self.run_id is not None, "manual": self.manual, "stop_requested": self.stop_requested,
                "current": self.current}
