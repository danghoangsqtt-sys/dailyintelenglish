"""Tests for AIWorker's claim/process lifecycle, no-handler safety, and shutdown."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import pytest

from app.db import transactions
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import ai_job_service, project_service
from app.services.ai_worker import AIWorker


def make_config(name: str) -> ScriptConfig:
    return ScriptConfig(
        name=name,
        topic="t",
        cefr_level="B1",
        duration_minutes=5.0,
        num_speakers=1,
        genre="interview",
        accent="american",
        speakers=[SpeakerConfig(name="Alex", gender="male", accent="american")],
    )


async def _project(db) -> dict:
    return await project_service.create_project(db, make_config("Worker test"))


async def _wait_until(predicate, timeout: float = 2.0, interval: float = 0.02) -> None:
    async def _poll():
        while not await predicate():
            await asyncio.sleep(interval)

    await asyncio.wait_for(_poll(), timeout=timeout)


async def test_worker_claims_and_processes_a_pending_job(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})

    processed = []

    async def handler(claimed_job, worker):
        # claim_job() already moved the job pending -> running before this runs.
        processed.append(claimed_job["id"])
        async with transactions.write_transaction(db):
            await ai_job_service.transition_status(db, claimed_job["id"], "validating", commit=False)
            await ai_job_service.transition_status(db, claimed_job["id"], "complete", commit=False)

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    worker.register_handler("script", handler)
    await worker.start()
    try:
        await _wait_until(lambda: _job_status_is(db, job["id"], project["id"], "complete"))
    finally:
        await worker.stop()

    assert processed == [job["id"]]


async def _job_status_is(db, job_id, project_id, status) -> bool:
    current = await ai_job_service.get_job(db, job_id, project_id)
    return current["status"] == status


async def test_worker_with_no_handler_never_touches_a_pending_job(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    await worker.start()
    await asyncio.sleep(0.1)  # a few poll cycles
    await worker.stop()

    unchanged = await ai_job_service.get_job(db, job["id"], project["id"])
    assert unchanged["status"] == "pending"
    assert unchanged["lease_owner"] is None


async def test_worker_transitions_job_to_error_when_handler_raises(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})

    async def failing_handler(claimed_job, worker):
        raise RuntimeError("simulated pipeline failure")

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    worker.register_handler("script", failing_handler)
    await worker.start()
    try:
        await _wait_until(lambda: _job_status_is(db, job["id"], project["id"], "error"))
    finally:
        await worker.stop()

    failed = await ai_job_service.get_job(db, job["id"], project["id"])
    assert failed["error_code"] == "handler_exception"
    assert "simulated pipeline failure" in failed["error_message"]


async def test_worker_does_not_hold_the_write_lock_during_handler_execution(db):
    """The whole point of processing outside a transaction: a slow handler (real
    provider call in Task 13.4/13.5) must never stall an unrelated request."""
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})

    handler_started = asyncio.Event()
    release_handler = asyncio.Event()

    async def slow_handler(claimed_job, worker):
        handler_started.set()
        await release_handler.wait()

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    worker.register_handler("script", slow_handler)
    await worker.start()
    try:
        await asyncio.wait_for(handler_started.wait(), timeout=2.0)
        # While the handler is "in flight" (no transaction open), the lock must be free.
        async with asyncio.timeout(1.0):
            async with transactions.read_transaction():
                pass
    finally:
        release_handler.set()
        await worker.stop()


async def test_worker_recovers_abandoned_jobs_on_start(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.claim_job(db, job["id"], "dead-worker")
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    await db.execute(
        "UPDATE ai_generation_jobs SET lease_expires_at = ? WHERE id = ?", (expired, job["id"])
    )
    await db.commit()

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    await worker.start()  # no handler registered -- must not re-claim it either
    await asyncio.sleep(0.05)
    await worker.stop()

    recovered = await ai_job_service.get_job(db, job["id"], project["id"])
    assert recovered["status"] == "pending"
    assert recovered["recovery_count"] == 1


async def test_worker_stop_is_bounded_even_if_a_handler_never_returns(db, monkeypatch):
    import app.services.ai_worker as ai_worker_module

    monkeypatch.setattr(ai_worker_module, "AI_WORKER_SHUTDOWN_GRACE_SECONDS", 0.2)

    project = await _project(db)
    await ai_job_service.create_job(db, project["id"], "script", {})

    async def stuck_handler(claimed_job, worker):
        await asyncio.sleep(999)

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    worker.register_handler("script", stuck_handler)
    await worker.start()
    await asyncio.sleep(0.1)  # let it claim and enter the stuck handler

    started = asyncio.get_event_loop().time()
    await asyncio.wait_for(worker.stop(), timeout=5.0)  # must return well before this outer bound
    elapsed = asyncio.get_event_loop().time() - started
    assert elapsed < 2.0  # bounded by the (patched, short) grace period, not indefinite


# --- Task 16.1 (BUG-022): the loop never dies silently ------------------------------


async def test_loop_survives_a_transient_claim_error_and_processes_a_later_job(db, monkeypatch):
    """A failure inside `_claim_next` (e.g. `database is locked`) must not end the
    poll loop -- the next job still gets claimed and completed."""
    import app.services.ai_worker as ai_worker_module

    monkeypatch.setattr(ai_worker_module, "AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS", 0.01)

    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})

    processed = []

    async def handler(claimed_job, worker):
        processed.append(claimed_job["id"])
        async with transactions.write_transaction(db):
            await ai_job_service.transition_status(db, claimed_job["id"], "validating", commit=False)
            await ai_job_service.transition_status(db, claimed_job["id"], "complete", commit=False)

    original_find_next = ai_job_service.find_next_pending_job
    calls = {"count": 0}

    async def flaky_find_next(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("simulated transient claim failure")
        return await original_find_next(*args, **kwargs)

    monkeypatch.setattr(ai_job_service, "find_next_pending_job", flaky_find_next)

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    worker.register_handler("script", handler)
    await worker.start()
    try:
        await _wait_until(lambda: _job_status_is(db, job["id"], project["id"], "complete"))
    finally:
        await worker.stop()

    assert processed == [job["id"]]
    assert calls["count"] >= 2


async def test_loop_logs_and_backs_off_on_an_unhandled_iteration_error(db, monkeypatch, caplog):
    import app.services.ai_worker as ai_worker_module

    monkeypatch.setattr(ai_worker_module, "AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS", 0.01)

    async def find_next_always_fails(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_job_service, "find_next_pending_job", find_next_always_fails)

    async def handler(claimed_job, worker):
        pass  # never reached -- no job is ever successfully claimed

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    worker.register_handler("script", handler)
    with caplog.at_level(logging.ERROR, logger="app.services.ai_worker"):
        await worker.start()
        await asyncio.sleep(0.1)
        await worker.stop()

    assert any("ai_worker_loop_error" in r.getMessage() for r in caplog.records)


async def test_process_survives_an_illegal_error_transition_after_handler_already_completed(db, caplog):
    """If a handler commits `complete` and then raises, the now-illegal
    `complete -> error` transition must be logged, not raised -- the job is left
    `complete` (BUG-022's guarded error-transition, known residual noted in the
    task card)."""
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})

    async def handler(claimed_job, worker):
        async with transactions.write_transaction(db):
            await ai_job_service.transition_status(db, claimed_job["id"], "validating", commit=False)
            await ai_job_service.transition_status(db, claimed_job["id"], "complete", commit=False)
        raise RuntimeError("late failure after commit")

    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    worker.register_handler("script", handler)
    with caplog.at_level(logging.ERROR, logger="app.services.ai_worker"):
        await worker.start()
        try:
            await _wait_until(lambda: _job_status_is(db, job["id"], project["id"], "complete"))
            await asyncio.sleep(0.1)  # let the (failing) error-transition attempt run
        finally:
            await worker.stop()

    final = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final["status"] == "complete"
    assert any("ai_worker_error_transition_failed" in r.getMessage() for r in caplog.records)


async def test_run_loop_does_not_swallow_cancellation(db):
    """The per-iteration guard must never catch `CancelledError` -- confirmed by
    cancelling the loop task directly, bypassing `stop()`'s own (expected)
    cancel-on-timeout path."""
    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    await worker.start()
    task = worker._task
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()


async def test_is_alive_reflects_task_lifecycle(db):
    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    assert worker.is_alive is False
    await worker.start()
    assert worker.is_alive is True
    await worker.stop()
    assert worker.is_alive is False


async def test_done_callback_logs_when_loop_task_ends_without_stop(db, caplog):
    worker = AIWorker(db_getter=lambda: db, poll_interval_seconds=0.02)
    await worker.start()
    task = worker._task
    with caplog.at_level(logging.ERROR, logger="app.services.ai_worker"):
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)  # let the done-callback (scheduled via call_soon) run

    assert any("ai_worker_task_ended_unexpectedly" in r.getMessage() for r in caplog.records)
