"""In-process worker for durable AI generation jobs (Phase 13, Task 13.3).

Provides claim/heartbeat/cancel-aware processing lifecycle and a startup recovery
sweep. No content pipeline is registered yet -- Task 13.4/13.5 call
`register_handler("script", ...)`/`register_handler("learning", ...)`. A claimed
job whose operation has no registered handler is safely returned to `pending`
rather than silently dropped or endlessly reprocessed, and the worker never even
attempts a claim while its handler map is empty (see `_claim_next`).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from app.core.constants import AI_WORKER_SHUTDOWN_GRACE_SECONDS
from app.db.transactions import write_transaction
from app.services import ai_job_service

if TYPE_CHECKING:
    import aiosqlite

logger = logging.getLogger(__name__)

JobHandler = Callable[[dict, "AIWorker"], Awaitable[None]]


class AIWorker:
    """Polls for pending AI generation jobs and dispatches them to registered handlers.

    `db_getter` is a zero-arg callable returning the shared `aiosqlite.Connection`
    (not the connection itself), so the worker always uses the live connection even
    if it's constructed before `init_db()` has run.
    """

    def __init__(
        self,
        db_getter: Callable[[], "aiosqlite.Connection"],
        worker_id: str | None = None,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self._db_getter = db_getter
        self._worker_id = worker_id or str(uuid.uuid4())
        self._poll_interval_seconds = poll_interval_seconds
        self._stop_event: asyncio.Event | None = None
        self._task: asyncio.Task | None = None
        self._handlers: dict[str, JobHandler] = {}

    def register_handler(self, operation: str, handler: JobHandler) -> None:
        """Register the pipeline that processes claimed jobs for `operation`."""
        self._handlers[operation] = handler

    async def start(self) -> None:
        """Recover any abandoned jobs from a prior run, then start the poll loop.

        Creates a fresh `asyncio.Event` on every call rather than reusing one
        across calls: `asyncio.Event` binds to whichever event loop is running
        when it's first awaited, and a long-lived singleton worker (see
        `app/main.py`) can genuinely be started under a different loop than a
        previous run -- most visibly in tests, where each `TestClient(app)` gets
        its own loop, but a real process restart is the same class of event.
        """
        db = self._db_getter()
        async with write_transaction(db):
            recovered = await ai_job_service.recover_abandoned_jobs(db, commit=False)
        if recovered:
            logger.info("ai_worker_recovered_jobs count=%d", len(recovered))
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Signal the loop to stop and wait a bounded grace period for it to finish.

        Never awaits indefinitely -- a job stuck past the grace period is cancelled
        outright; its lease will simply expire and a future `start()` (this run or
        a fresh one) reclaims it via `recover_abandoned_jobs`.
        """
        if self._task is None:
            return
        if self._stop_event is not None:
            self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=AI_WORKER_SHUTDOWN_GRACE_SECONDS)
        except TimeoutError:
            self._task.cancel()
        finally:
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            job = await self._claim_next()
            if job is None:
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self._poll_interval_seconds)
                except TimeoutError:
                    pass
                continue
            await self._process(job)

    async def _claim_next(self) -> dict | None:
        if not self._handlers:
            return None
        db = self._db_getter()
        async with write_transaction(db):
            pending = await ai_job_service.find_next_pending_job(db, list(self._handlers.keys()))
            if pending is None:
                return None
            return await ai_job_service.claim_job(db, pending["id"], self._worker_id, commit=False)

    async def _process(self, job: dict) -> None:
        handler = self._handlers.get(job["operation"])
        db = self._db_getter()
        if handler is None:
            # Registered set changed between find_next_pending_job and claim_job
            # (extremely unlikely, but never leave a claimed job stuck) -- release it.
            async with write_transaction(db):
                await ai_job_service.release_claim(db, job["id"], commit=False)
            return
        try:
            await handler(job, self)
        except Exception as exc:  # noqa: BLE001 -- a handler bug must not crash the worker loop
            logger.exception("ai_worker_handler_failed job_id=%s operation=%s", job["id"], job["operation"])
            async with write_transaction(db):
                await ai_job_service.transition_status(
                    db,
                    job["id"],
                    "error",
                    error_code="handler_exception",
                    error_message=f"{type(exc).__name__}: {exc}"[:200],
                    commit=False,
                )

    async def heartbeat(self, job_id: str) -> None:
        """Refresh a job's lease. Called by a handler while it's actively processing."""
        db = self._db_getter()
        async with write_transaction(db):
            await ai_job_service.heartbeat(db, job_id, self._worker_id, commit=False)

    def get_db(self) -> "aiosqlite.Connection":
        """Return the shared connection. Lets a handler (which only receives
        `(job, worker)`) reach the DB without importing `app.db.database` itself."""
        return self._db_getter()

    @property
    def worker_id(self) -> str:
        return self._worker_id
