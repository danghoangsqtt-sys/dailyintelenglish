"""Durable AI generation job state machine (Phase 13, Task 13.3).

Provides the job/checkpoint lifecycle only -- atomic create/claim, transitions,
lease/heartbeat, cancellation, staleness, and startup recovery. Task 13.4/13.5 plug
in the actual script/learning content pipelines via `app.services.ai_worker`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import aiosqlite

from app.core.constants import (
    AI_JOB_LEASE_SECONDS,
    AI_JOB_MAX_RECORDED_CALLS,
    AI_JOB_MAX_RECOVERY_ATTEMPTS,
    AI_PIPELINE_VERSION,
)
from app.core.exceptions import (
    NotFoundError,
    ProviderAuthError,
    ProviderDailyQuotaError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SchemaValidationError,
    ValidationError,
)

# Legal forward transitions. Terminal states map to an empty set -- immutable except
# for non-semantic diagnostic metadata (e.g. appending to metrics_json), which never
# goes through transition_status at all.
_LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "cancelled", "stale"},
    "running": {"validating", "error", "cancelled", "stale"},
    "validating": {"complete", "error", "cancelled", "stale"},
    "complete": set(),
    "error": set(),
    "cancelled": set(),
    "stale": set(),
}
_TERMINAL_STATUSES = frozenset(status for status, targets in _LEGAL_TRANSITIONS.items() if not targets)

# Phase 14 Task 14.2 -- maps a router-raised ProviderError to the job's error_code,
# so an infrastructure failure is distinguishable from a content failure (never
# `handler_exception`) on the job row and in Gate B evidence.
#
# `SchemaValidationError` IS listed (Amendment B, 2026-09-21): it is a `ProviderError`
# subclass structurally, but a *content* failure -- raised by
# `app/services/ai/validation.py:parse_and_validate` after a successful
# `router.generate()`, never by the router/provider layer itself. A pipeline's
# `except ProviderError` around a router call (e.g. script_pipeline's outline step)
# also catches it, since Python's exception matching is by class, not by "was this
# raised by the router". Leaving it unmapped fell through to the generic
# "provider_error" fallback below, which Gate B-2's failure classification (plan §4.4)
# reads as `infra` purely from the `provider_` prefix -- mapping it here instead keeps
# infra/content failures distinguishable exactly as the plan requires.
_PROVIDER_ERROR_CODES: dict[type[ProviderError], str] = {
    ProviderUnavailableError: "provider_unavailable",
    ProviderTimeoutError: "provider_timeout",
    ProviderRateLimitError: "provider_rate_limited",
    ProviderDailyQuotaError: "provider_daily_quota",
    ProviderAuthError: "provider_auth",
    ProviderInvalidResponseError: "provider_invalid_response",
    SchemaValidationError: "schema_validation_failed",
}


def provider_error_code(exc: ProviderError) -> str:
    """Map one `ProviderError` (sub)class to its Task 14.2 job `error_code`.

    Falls back to `"provider_error"` for the base class or any subclass not in
    `_PROVIDER_ERROR_CODES`, so a future provider exception type never crashes
    job-failure handling -- it just loses some specificity until this table is
    updated.
    """
    return _PROVIDER_ERROR_CODES.get(type(exc), "provider_error")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


def _canonical_hash(data: dict) -> str:
    """Stable sha256 over a JSON-serializable dict, independent of key order."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _assert_legal_transition(current: str, target: str) -> None:
    """Raise ValidationError if `current -> target` is not an allowed edge."""
    allowed = _LEGAL_TRANSITIONS.get(current)
    if allowed is None:
        raise ValidationError(f"Unknown job status {current!r}")
    if target not in allowed:
        raise ValidationError(f"Illegal job transition {current!r} -> {target!r}")


async def _fetch_row(db: aiosqlite.Connection, job_id: str) -> aiosqlite.Row | None:
    cursor = await db.execute("SELECT * FROM ai_generation_jobs WHERE id = ?", (job_id,))
    return await cursor.fetchone()


async def get_job(db: aiosqlite.Connection, job_id: str, project_id: str) -> dict:
    """Fetch one job, verifying it belongs to `project_id`.

    Raises:
        NotFoundError: If no such job exists, or it belongs to a different project
            (the two cases are indistinguishable to the caller on purpose).
    """
    row = await _fetch_row(db, job_id)
    if row is None or row["project_id"] != project_id:
        raise NotFoundError(f"AI job {job_id} not found for project {project_id}")
    return dict(row)


async def get_active_job(db: aiosqlite.Connection, project_id: str, operation: str) -> dict | None:
    """Return the current pending/running/validating job for this project+operation, if any."""
    cursor = await db.execute(
        "SELECT * FROM ai_generation_jobs WHERE project_id = ? AND operation = ? "
        "AND status IN ('pending', 'running', 'validating')",
        (project_id, operation),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_job(
    db: aiosqlite.Connection,
    project_id: str,
    operation: str,
    input_snapshot: dict[str, Any],
    idempotency_key: str | None = None,
    requested_provider: str | None = None,
    commit: bool = True,
) -> tuple[dict, bool]:
    """Create a new job, or atomically return the existing equivalent one.

    Two independent unique indexes make this safe under real concurrency, not just
    in the common single-request case:
    - one active (pending/running/validating) job per (project_id, operation);
    - one job per (project_id, operation, idempotency_key), terminal or not, so a
      client retry with the same key always gets back the same result.
    A caller-omitted `idempotency_key` gets a fresh random one per call, so it can
    never coincidentally collide with a real client-supplied key.

    Returns:
        (job, created) -- `created` is False when an existing active/idempotent job
        was returned instead of inserting a new row.
    """
    active = await get_active_job(db, project_id, operation)
    if active is not None:
        return active, False

    key = idempotency_key or _new_id()
    job_id = _new_id()
    now = _now_iso()
    input_hash = _canonical_hash(input_snapshot)
    row = {
        "id": job_id,
        "project_id": project_id,
        "operation": operation,
        "status": "pending",
        "stage": "queued",
        "progress": 0,
        "requested_provider": requested_provider,
        "input_snapshot_json": json.dumps(input_snapshot, default=str),
        "input_hash": input_hash,
        "config_hash": input_hash,  # refined once 13.4/13.5 have a narrower config shape
        "pipeline_version": AI_PIPELINE_VERSION,
        "idempotency_key": key,
        "created_at": now,
        "updated_at": now,
    }
    try:
        await db.execute(
            "INSERT INTO ai_generation_jobs "
            "(id, project_id, operation, status, stage, progress, requested_provider, "
            " input_snapshot_json, input_hash, config_hash, pipeline_version, "
            " idempotency_key, created_at, updated_at) "
            "VALUES (:id, :project_id, :operation, :status, :stage, :progress, "
            " :requested_provider, :input_snapshot_json, :input_hash, :config_hash, "
            " :pipeline_version, :idempotency_key, :created_at, :updated_at)",
            row,
        )
    except aiosqlite.IntegrityError:
        # Lost a real race to a concurrent creator (or a genuine idempotency-key
        # replay) -- whichever index fired, the equivalent job now exists; find it
        # rather than raising back a constraint error the caller can't act on.
        existing = await get_active_job(db, project_id, operation)
        if existing is not None:
            return existing, False
        cursor = await db.execute(
            "SELECT * FROM ai_generation_jobs WHERE project_id = ? AND operation = ? "
            "AND idempotency_key = ?",
            (project_id, operation, key),
        )
        existing_row = await cursor.fetchone()
        if existing_row is None:
            raise
        return dict(existing_row), False

    if commit:
        await db.commit()
    created_row = await _fetch_row(db, job_id)
    return dict(created_row), True


async def claim_job(db: aiosqlite.Connection, job_id: str, worker_id: str, commit: bool = True) -> dict | None:
    """Atomically claim a `pending` job for `worker_id`.

    One conditional `UPDATE ... WHERE status = 'pending'` -- never a separate
    unguarded SELECT-then-UPDATE, so two workers racing on the same job can never
    both believe they claimed it.

    Returns:
        The claimed row, or `None` if it was no longer `pending` (another worker
        won the race, or it was cancelled/made stale first).
    """
    now = datetime.now(timezone.utc)
    lease_expires = (now + timedelta(seconds=AI_JOB_LEASE_SECONDS)).isoformat()
    now_iso = now.isoformat()
    cursor = await db.execute(
        "UPDATE ai_generation_jobs SET status = 'running', lease_owner = ?, "
        "lease_expires_at = ?, heartbeat_at = ?, started_at = COALESCE(started_at, ?), "
        "updated_at = ? WHERE id = ? AND status = 'pending'",
        (worker_id, lease_expires, now_iso, now_iso, now_iso, job_id),
    )
    if cursor.rowcount != 1:
        return None
    if commit:
        await db.commit()
    row = await _fetch_row(db, job_id)
    return dict(row) if row else None


async def release_claim(db: aiosqlite.Connection, job_id: str, commit: bool = True) -> None:
    """Return a claimed-but-unprocessed job to `pending` (e.g. no handler registered yet).

    Only releases if still `running` and untouched otherwise -- a job already moved
    on (cancelled, made stale, etc.) is left alone.
    """
    now_iso = _now_iso()
    await db.execute(
        "UPDATE ai_generation_jobs SET status = 'pending', lease_owner = NULL, "
        "lease_expires_at = NULL, heartbeat_at = NULL, updated_at = ? "
        "WHERE id = ? AND status = 'running'",
        (now_iso, job_id),
    )
    if commit:
        await db.commit()


async def heartbeat(db: aiosqlite.Connection, job_id: str, worker_id: str, commit: bool = True) -> None:
    """Refresh a job's lease while its owning worker is still actively processing it."""
    now = datetime.now(timezone.utc)
    lease_expires = (now + timedelta(seconds=AI_JOB_LEASE_SECONDS)).isoformat()
    await db.execute(
        "UPDATE ai_generation_jobs SET heartbeat_at = ?, lease_expires_at = ?, updated_at = ? "
        "WHERE id = ? AND lease_owner = ? AND status IN ('running', 'validating')",
        (now.isoformat(), lease_expires, now.isoformat(), job_id, worker_id),
    )
    if commit:
        await db.commit()


async def update_progress(
    db: aiosqlite.Connection,
    job_id: str,
    stage: str,
    progress: int,
    commit: bool = True,
) -> None:
    """Update a job's free-form stage label and 0-100 progress, monotonic by convention.

    Not enforced at the SQL layer (a legitimate re-validation pass can briefly step
    progress back within the same `running`/`validating` status) -- callers own not
    reporting nonsensical regressions to the UI.
    """
    if not 0 <= progress <= 100:
        raise ValidationError(f"progress must be within 0..100, got {progress}")
    await db.execute(
        "UPDATE ai_generation_jobs SET stage = ?, progress = ?, updated_at = ? WHERE id = ?",
        (stage, progress, _now_iso(), job_id),
    )
    if commit:
        await db.commit()


async def transition_status(
    db: aiosqlite.Connection,
    job_id: str,
    new_status: str,
    error_code: str | None = None,
    error_message: str | None = None,
    fallback_used: bool | None = None,
    fallback_reason: str | None = None,
    commit: bool = True,
) -> dict:
    """Move a job to `new_status`, enforcing the legal transition matrix.

    Raises:
        NotFoundError: If the job doesn't exist.
        ValidationError: If `new_status` isn't a legal transition from the job's
            current status.
    """
    row = await _fetch_row(db, job_id)
    if row is None:
        raise NotFoundError(f"AI job {job_id} not found")
    _assert_legal_transition(row["status"], new_status)

    now_iso = _now_iso()
    finished_at = now_iso if new_status in _TERMINAL_STATUSES else None
    fields = {
        "status": new_status,
        "updated_at": now_iso,
        "finished_at": finished_at,
        "error_code": error_code,
        "error_message": error_message,
    }
    set_clauses = ["status = :status", "updated_at = :updated_at"]
    if finished_at is not None:
        set_clauses.append("finished_at = :finished_at")
    if error_code is not None:
        set_clauses.append("error_code = :error_code")
    if error_message is not None:
        set_clauses.append("error_message = :error_message")
    if fallback_used is not None:
        fields["fallback_used"] = int(fallback_used)
        set_clauses.append("fallback_used = :fallback_used")
    if fallback_reason is not None:
        fields["fallback_reason"] = fallback_reason
        set_clauses.append("fallback_reason = :fallback_reason")
    fields["id"] = job_id

    await db.execute(f"UPDATE ai_generation_jobs SET {', '.join(set_clauses)} WHERE id = :id", fields)
    if commit:
        await db.commit()
    updated = await _fetch_row(db, job_id)
    return dict(updated)


async def record_generation_call(
    db: aiosqlite.Connection, job_id: str, call: dict[str, Any], commit: bool = True
) -> dict:
    """Append one Task 14.2 telemetry `call` record to a job's `metrics_json`.

    Always called *after* the router call it describes has already returned or
    raised -- never wraps or is called from within an in-flight `router.generate()`
    (see `script_pipeline._call_router`/`learning_pipeline._call_router`). One
    UPDATE inside the caller's own transaction; this function never commits its
    own separate transaction beyond the `commit` flag callers already use
    elsewhere in this module.

    `call` fields (see task-14.2.md for the full safe-field shape): `provider`/
    `model` update the job row via `COALESCE` (a `None` here -- e.g. an
    `outcome="error"` call -- never overwrites a value a prior successful call
    already set). `fallback_used` (+ optional `fallback_reason`) and `is_repair`
    drive `fallback_used`/`fallback_count`/`repair_count` only when truthy.

    Raises:
        NotFoundError: If the job doesn't exist.
        ValidationError: If the job is already in a terminal status -- a
            terminal job's row is otherwise immutable, and this is diagnostic
            metadata, not a status transition, so it never goes through
            `_assert_legal_transition`.
    """
    row = await _fetch_row(db, job_id)
    if row is None:
        raise NotFoundError(f"AI job {job_id} not found")
    if row["status"] not in ("running", "validating"):
        raise ValidationError(
            f"Cannot record a generation call on job {job_id}: status {row['status']!r} is terminal"
        )

    try:
        metrics = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
    except (TypeError, ValueError):
        metrics = {}
    if not isinstance(metrics, dict):
        metrics = {}
    calls = metrics.get("calls")
    if not isinstance(calls, list):
        calls = []
    calls.append(call)
    if len(calls) > AI_JOB_MAX_RECORDED_CALLS:
        calls = calls[-AI_JOB_MAX_RECORDED_CALLS:]
    metrics["calls"] = calls

    fields: dict[str, Any] = {
        "id": job_id,
        "metrics_json": json.dumps(metrics),
        "actual_provider": call.get("provider"),
        "model": call.get("model"),
        "updated_at": _now_iso(),
    }
    set_clauses = [
        "metrics_json = :metrics_json",
        "actual_provider = COALESCE(:actual_provider, actual_provider)",
        "model = COALESCE(:model, model)",
        "updated_at = :updated_at",
    ]
    if call.get("fallback_used"):
        set_clauses.append("fallback_used = 1")
        set_clauses.append("fallback_count = fallback_count + 1")
        fallback_reason = call.get("fallback_reason")
        if fallback_reason is not None:
            fields["fallback_reason"] = fallback_reason
            set_clauses.append("fallback_reason = :fallback_reason")
    if call.get("is_repair"):
        set_clauses.append("repair_count = repair_count + 1")

    await db.execute(f"UPDATE ai_generation_jobs SET {', '.join(set_clauses)} WHERE id = :id", fields)
    if commit:
        await db.commit()
    updated = await _fetch_row(db, job_id)
    return dict(updated)


async def set_job_metric(db: aiosqlite.Connection, job_id: str, key: str, value: Any, commit: bool = True) -> dict:
    """Sets one sibling key in a job's `metrics_json`, next to
    `record_generation_call`'s own `"calls"` list -- a generic read-modify-write
    for arbitrary diagnostic metadata (Task 15.3). Used e.g. by
    `learning_pipeline` for `dropped_items` (Task 14.11), which previously
    duplicated this exact shape locally because this file was outside that
    task's allowed files. Never touches `"calls"` or any other existing key.

    Raises:
        NotFoundError: If the job doesn't exist.
    """
    row = await _fetch_row(db, job_id)
    if row is None:
        raise NotFoundError(f"AI job {job_id} not found")
    try:
        metrics = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
    except (TypeError, ValueError):
        metrics = {}
    if not isinstance(metrics, dict):
        metrics = {}
    metrics[key] = value
    await db.execute(
        "UPDATE ai_generation_jobs SET metrics_json = ?, updated_at = ? WHERE id = ?",
        (json.dumps(metrics), _now_iso(), job_id),
    )
    if commit:
        await db.commit()
    updated = await _fetch_row(db, job_id)
    return dict(updated)


async def request_cancel(db: aiosqlite.Connection, job_id: str, project_id: str, commit: bool = True) -> dict:
    """Idempotently request cancellation.

    A job already in a terminal state (including one already `cancelled`) is
    returned unchanged -- cancelling twice, or cancelling a job that finished a
    moment earlier, is never an error.
    """
    job = await get_job(db, job_id, project_id)
    if job["status"] in _TERMINAL_STATUSES:
        return job
    await db.execute(
        "UPDATE ai_generation_jobs SET cancel_requested = 1, updated_at = ? WHERE id = ?",
        (_now_iso(), job_id),
    )
    if commit:
        await db.commit()
    return await get_job(db, job_id, project_id)


async def mark_stale(db: aiosqlite.Connection, job_id: str, commit: bool = True) -> dict:
    """Transition a job to `stale` (its inputs no longer match current project state)."""
    return await transition_status(db, job_id, "stale", commit=commit)


async def save_checkpoint(
    db: aiosqlite.Connection,
    job_id: str,
    section_index: int,
    stage: str,
    status: str,
    input_hash: str,
    result_json: str | None = None,
    metrics_json: str = "{}",
    commit: bool = True,
) -> dict:
    """Insert or replace one `(job_id, stage, section_index)` checkpoint."""
    now_iso = _now_iso()
    checkpoint_id = _new_id()
    await db.execute(
        "INSERT INTO ai_generation_checkpoints "
        "(id, job_id, section_index, stage, status, input_hash, result_json, metrics_json, "
        " created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(job_id, stage, section_index) DO UPDATE SET "
        "status = excluded.status, input_hash = excluded.input_hash, "
        "result_json = excluded.result_json, metrics_json = excluded.metrics_json, "
        "updated_at = excluded.updated_at",
        (checkpoint_id, job_id, section_index, stage, status, input_hash, result_json, metrics_json, now_iso, now_iso),
    )
    if commit:
        await db.commit()
    cursor = await db.execute(
        "SELECT * FROM ai_generation_checkpoints WHERE job_id = ? AND stage = ? AND section_index = ?",
        (job_id, stage, section_index),
    )
    row = await cursor.fetchone()
    return dict(row)


async def get_valid_checkpoints(db: aiosqlite.Connection, job_id: str) -> list[dict]:
    """List a job's `valid` checkpoints in section order (what a resume reads from)."""
    cursor = await db.execute(
        "SELECT * FROM ai_generation_checkpoints WHERE job_id = ? AND status = 'valid' "
        "ORDER BY section_index",
        (job_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def find_next_pending_job(db: aiosqlite.Connection, operations: list[str]) -> dict | None:
    """Return the oldest `pending` job whose operation has a registered handler."""
    if not operations:
        return None
    placeholders = ", ".join("?" for _ in operations)
    cursor = await db.execute(
        f"SELECT * FROM ai_generation_jobs WHERE status = 'pending' "
        f"AND operation IN ({placeholders}) ORDER BY created_at LIMIT 1",
        operations,
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def recover_abandoned_jobs(db: aiosqlite.Connection, commit: bool = True) -> list[dict]:
    """Reclaim jobs left `running`/`validating` past their lease (a prior crash/stop).

    Each is either requeued to `pending` (with `recovery_count` incremented, so a
    worker's normal claim loop picks it up again) or, once
    `AI_JOB_MAX_RECOVERY_ATTEMPTS` is reached, forced to a terminal `error` instead
    of being retried forever across repeated crash/restart cycles.

    Returns the list of affected jobs (post-update), for logging/tests.
    """
    now_iso = _now_iso()
    cursor = await db.execute(
        "SELECT * FROM ai_generation_jobs WHERE status IN ('running', 'validating') "
        "AND lease_expires_at IS NOT NULL AND lease_expires_at < ?",
        (now_iso,),
    )
    abandoned = [dict(row) for row in await cursor.fetchall()]
    results = []
    for job in abandoned:
        if job["recovery_count"] + 1 >= AI_JOB_MAX_RECOVERY_ATTEMPTS:
            updated = await transition_status(
                db,
                job["id"],
                "error",
                error_code="recovery_exhausted",
                error_message="Job was abandoned by its worker too many times.",
                commit=False,
            )
        else:
            await db.execute(
                "UPDATE ai_generation_jobs SET status = 'pending', lease_owner = NULL, "
                "lease_expires_at = NULL, heartbeat_at = NULL, recovery_count = recovery_count + 1, "
                "updated_at = ? WHERE id = ?",
                (now_iso, job["id"]),
            )
            updated = dict(await _fetch_row(db, job["id"]))
        results.append(updated)
    if commit:
        await db.commit()
    return results


# Task 18.4 (D22): window size for the fallback-rate readout -- a decision INPUT for
# cloud-vs-local trade-offs, never a pass/fail gate. Kept local to this module rather
# than app/core/constants.py (not in this task's allowed files, and the constant is
# meaningful only to this one aggregate).
FALLBACK_RATE_WINDOW = 50


async def get_fallback_rate_stats(db: aiosqlite.Connection, limit: int = FALLBACK_RATE_WINDOW) -> dict:
    """Task 18.4 (D22): fallback-rate readout over the last `limit` terminal AI jobs.

    Read-only over data Task 14.2/18.2 already persist -- `fallback_used` per job
    (`record_generation_call`) and `provider`/`model`/`fallback_used`/`fallback_reason`
    per call (`metrics_json.calls`, safe fields only, no prompt/response/key). No new
    table, column, or migration.

    PM review C1: the window is `status IN ('complete', 'error')`, not `'complete'`
    alone -- excluding `error` jobs would hide exactly the case D22 most needs to see:
    a job where the cloud call failed AND the fallback didn't save it either. `stale`/
    `cancelled` jobs are excluded (never reached a real outcome).

    Returns `{"window": int, "by_status": {status: count}, "call_fallback_rate":
    float | None, "job_fallback_rate": float | None, "fallback_reason_counts": {reason:
    count}}`. Both rates are `None` (not 0.0) when their denominator is zero -- an
    install with no terminal jobs yet has no fallback rate, not a 0% one.
    """
    cursor = await db.execute(
        "SELECT status, fallback_used, metrics_json FROM ai_generation_jobs "
        "WHERE status IN ('complete', 'error') ORDER BY finished_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()

    by_status: dict[str, int] = {}
    n_jobs_with_fallback = 0
    total_calls = 0
    fallback_calls = 0
    reason_counts: dict[str, int] = {}

    for row in rows:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
        if row["fallback_used"]:
            n_jobs_with_fallback += 1
        try:
            metrics = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
        except (TypeError, ValueError):
            metrics = {}
        calls = metrics.get("calls") if isinstance(metrics, dict) else None
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, dict):
                continue
            total_calls += 1
            if call.get("fallback_used"):
                fallback_calls += 1
                reason = call.get("fallback_reason") or "unknown"
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    n_jobs = len(rows)
    return {
        "window": n_jobs,
        "by_status": by_status,
        "call_fallback_rate": round(fallback_calls / total_calls, 4) if total_calls else None,
        "job_fallback_rate": round(n_jobs_with_fallback / n_jobs, 4) if n_jobs else None,
        "fallback_reason_counts": reason_counts,
    }
