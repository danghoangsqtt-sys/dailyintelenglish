"""Tests for ai_job_service's state machine, claim/lease, cancel, and recovery."""

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from app.core.constants import AI_JOB_MAX_RECORDED_CALLS, AI_JOB_MAX_RECOVERY_ATTEMPTS
from app.core.exceptions import (
    NotFoundError,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    SchemaValidationError,
    ValidationError,
)
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import ai_job_service, project_service


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
    return await project_service.create_project(db, make_config("Job service test"))


# --- create / idempotency -----------------------------------------------------------


async def test_create_job_returns_created_true_for_a_new_job(db):
    project = await _project(db)
    job, created = await ai_job_service.create_job(db, project["id"], "script", {"x": 1})
    assert created is True
    assert job["status"] == "pending"
    assert job["operation"] == "script"


async def test_create_job_returns_existing_active_job_without_a_key(db):
    """A second bare create() (no idempotency_key) while one is still active must
    return the SAME active job, not a second row -- this is the common
    'duplicate create' case the partial unique index protects."""
    project = await _project(db)
    first, first_created = await ai_job_service.create_job(db, project["id"], "script", {"x": 1})
    second, second_created = await ai_job_service.create_job(db, project["id"], "script", {"x": 2})
    assert first_created is True
    assert second_created is False
    assert second["id"] == first["id"]


async def test_create_job_with_same_idempotency_key_returns_same_job_even_after_terminal(db):
    project = await _project(db)
    job, created = await ai_job_service.create_job(
        db, project["id"], "script", {"x": 1}, idempotency_key="client-key-1"
    )
    assert created is True
    await ai_job_service.transition_status(db, job["id"], "running")
    await ai_job_service.transition_status(db, job["id"], "validating")
    await ai_job_service.transition_status(db, job["id"], "complete")

    replay, replay_created = await ai_job_service.create_job(
        db, project["id"], "script", {"x": 999}, idempotency_key="client-key-1"
    )
    assert replay_created is False
    assert replay["id"] == job["id"]
    assert replay["status"] == "complete"


async def test_create_job_allows_a_new_one_once_the_prior_job_is_terminal(db):
    project = await _project(db)
    first, _ = await ai_job_service.create_job(db, project["id"], "script", {"x": 1})
    await ai_job_service.transition_status(db, first["id"], "running")
    await ai_job_service.transition_status(db, first["id"], "error", error_code="boom")

    second, created = await ai_job_service.create_job(db, project["id"], "script", {"x": 2})
    assert created is True
    assert second["id"] != first["id"]


async def test_create_job_different_operations_do_not_collide(db):
    project = await _project(db)
    script_job, script_created = await ai_job_service.create_job(db, project["id"], "script", {})
    learning_job, learning_created = await ai_job_service.create_job(db, project["id"], "learning", {})
    assert script_created is True
    assert learning_created is True
    assert script_job["id"] != learning_job["id"]


# --- transition matrix ---------------------------------------------------------------


@pytest.mark.parametrize(
    "start,target",
    [
        ("pending", "running"),
        ("pending", "cancelled"),
        ("pending", "stale"),
        ("running", "validating"),
        ("running", "error"),
        ("running", "cancelled"),
        ("running", "stale"),
        ("validating", "complete"),
        ("validating", "error"),
        ("validating", "cancelled"),
        ("validating", "stale"),
    ],
)
async def test_legal_transitions_succeed(db, start, target):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    if start != "pending":
        # walk to `start` through legal edges first
        path = {"running": ["running"], "validating": ["running", "validating"]}[start]
        for step in path:
            await ai_job_service.transition_status(db, job["id"], step)
    updated = await ai_job_service.transition_status(db, job["id"], target)
    assert updated["status"] == target


@pytest.mark.parametrize(
    "start,target",
    [
        ("pending", "complete"),
        ("pending", "validating"),
        ("pending", "error"),
        ("running", "pending"),
        ("running", "complete"),
        ("validating", "running"),
        ("validating", "pending"),
        ("complete", "pending"),
        ("complete", "running"),
        ("cancelled", "running"),
        ("stale", "running"),
        ("error", "pending"),
    ],
)
async def test_illegal_transitions_raise(db, start, target):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    path = {
        "pending": [],
        "running": ["running"],
        "validating": ["running", "validating"],
        "complete": ["running", "validating", "complete"],
        "error": ["running", "error"],
        "cancelled": ["cancelled"],
        "stale": ["stale"],
    }[start]
    for step in path:
        await ai_job_service.transition_status(db, job["id"], step)
    with pytest.raises(ValidationError):
        await ai_job_service.transition_status(db, job["id"], target)


async def test_transition_status_raises_not_found_for_unknown_job(db):
    with pytest.raises(NotFoundError):
        await ai_job_service.transition_status(db, "does-not-exist", "running")


# --- atomic claim ---------------------------------------------------------------------


async def test_claim_job_succeeds_once_and_sets_lease_fields(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    assert claimed is not None
    assert claimed["status"] == "running"
    assert claimed["lease_owner"] == "worker-1"
    assert claimed["lease_expires_at"] is not None
    assert claimed["started_at"] is not None


async def test_claim_job_is_atomic_only_one_of_two_concurrent_claims_wins(db):
    """Simulates the exact race the plan forbids solving with SELECT-then-UPDATE:
    two 'workers' both try to claim the same pending job concurrently."""
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})

    results = await asyncio.gather(
        ai_job_service.claim_job(db, job["id"], "worker-A"),
        ai_job_service.claim_job(db, job["id"], "worker-B"),
    )
    winners = [result for result in results if result is not None]
    assert len(winners) == 1
    assert winners[0]["lease_owner"] in ("worker-A", "worker-B")


async def test_claim_job_returns_none_for_a_non_pending_job(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.claim_job(db, job["id"], "worker-1")
    second_attempt = await ai_job_service.claim_job(db, job["id"], "worker-2")
    assert second_attempt is None


async def test_heartbeat_extends_lease_only_for_the_owning_worker(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")

    await ai_job_service.heartbeat(db, job["id"], "worker-2")  # not the owner -- no-op
    unchanged = await ai_job_service.get_job(db, job["id"], project["id"])
    assert unchanged["heartbeat_at"] == claimed["heartbeat_at"]

    await asyncio.sleep(0.01)
    await ai_job_service.heartbeat(db, job["id"], "worker-1")
    refreshed = await ai_job_service.get_job(db, job["id"], project["id"])
    assert refreshed["heartbeat_at"] != claimed["heartbeat_at"]


async def test_release_claim_returns_a_running_job_to_pending(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.claim_job(db, job["id"], "worker-1")
    await ai_job_service.release_claim(db, job["id"])
    released = await ai_job_service.get_job(db, job["id"], project["id"])
    assert released["status"] == "pending"
    assert released["lease_owner"] is None


# --- cancel ----------------------------------------------------------------------------


async def test_request_cancel_is_idempotent_on_a_pending_job(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    first = await ai_job_service.request_cancel(db, job["id"], project["id"])
    second = await ai_job_service.request_cancel(db, job["id"], project["id"])
    assert first["cancel_requested"] == 1
    assert second["cancel_requested"] == 1
    assert first["status"] == second["status"] == "pending"


async def test_request_cancel_on_a_terminal_job_is_a_noop_returning_terminal_state(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.transition_status(db, job["id"], "running")
    await ai_job_service.transition_status(db, job["id"], "error", error_code="boom")

    result = await ai_job_service.request_cancel(db, job["id"], project["id"])
    assert result["status"] == "error"
    assert result["cancel_requested"] == 0  # never touched -- already terminal


async def test_request_cancel_wrong_project_raises_not_found(db):
    project_a = await _project(db)
    project_b = await project_service.create_project(db, make_config("Other project"))
    job, _ = await ai_job_service.create_job(db, project_a["id"], "script", {})
    with pytest.raises(NotFoundError):
        await ai_job_service.request_cancel(db, job["id"], project_b["id"])


# --- checkpoints -------------------------------------------------------------------------


async def test_save_and_read_checkpoints_in_section_order(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.save_checkpoint(db, job["id"], 2, "section", "valid", "h2", result_json='{"b":2}')
    await ai_job_service.save_checkpoint(db, job["id"], 1, "section", "valid", "h1", result_json='{"a":1}')
    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    assert [c["section_index"] for c in checkpoints] == [1, 2]


async def test_save_checkpoint_upserts_on_conflict(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.save_checkpoint(db, job["id"], 1, "section", "valid", "h1", result_json='{"v":1}')
    await ai_job_service.save_checkpoint(db, job["id"], 1, "section", "valid", "h1-updated", result_json='{"v":2}')
    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    assert len(checkpoints) == 1
    assert checkpoints[0]["result_json"] == '{"v":2}'


async def test_invalid_checkpoints_are_excluded_from_resume_reads(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.save_checkpoint(db, job["id"], 1, "section", "invalid", "h1")
    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    assert checkpoints == []


# --- recovery ----------------------------------------------------------------------------


async def _make_abandoned(db, project_id: str, recovery_count: int = 0) -> dict:
    job, _ = await ai_job_service.create_job(db, project_id, "script", {})
    await ai_job_service.claim_job(db, job["id"], "dead-worker")
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    await db.execute(
        "UPDATE ai_generation_jobs SET lease_expires_at = ?, recovery_count = ? WHERE id = ?",
        (expired, recovery_count, job["id"]),
    )
    await db.commit()
    return job


async def test_recover_abandoned_jobs_requeues_to_pending(db):
    project = await _project(db)
    abandoned = await _make_abandoned(db, project["id"], recovery_count=0)
    recovered = await ai_job_service.recover_abandoned_jobs(db)
    assert len(recovered) == 1
    assert recovered[0]["id"] == abandoned["id"]
    assert recovered[0]["status"] == "pending"
    assert recovered[0]["recovery_count"] == 1
    assert recovered[0]["lease_owner"] is None


async def test_recover_abandoned_jobs_is_bounded_and_errors_out_eventually(db):
    project = await _project(db)
    abandoned = await _make_abandoned(
        db, project["id"], recovery_count=AI_JOB_MAX_RECOVERY_ATTEMPTS - 1
    )
    recovered = await ai_job_service.recover_abandoned_jobs(db)
    assert recovered[0]["id"] == abandoned["id"]
    assert recovered[0]["status"] == "error"
    assert recovered[0]["error_code"] == "recovery_exhausted"


async def test_recover_abandoned_jobs_ignores_jobs_still_within_their_lease(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    await ai_job_service.claim_job(db, job["id"], "worker-1")  # fresh lease, not expired
    recovered = await ai_job_service.recover_abandoned_jobs(db)
    assert recovered == []


# --- unrelated-project access -------------------------------------------------------------


async def test_get_active_job_is_scoped_to_its_own_project(db):
    project_a = await _project(db)
    project_b = await project_service.create_project(db, make_config("Project B"))
    job, _ = await ai_job_service.create_job(db, project_a["id"], "script", {})

    assert (await ai_job_service.get_active_job(db, project_a["id"], "script"))["id"] == job["id"]
    assert await ai_job_service.get_active_job(db, project_b["id"], "script") is None


# --- Task 14.2: record_generation_call ------------------------------------------------


def _call(**overrides) -> dict:
    base = {
        "purpose": "script_section",
        "section_index": 1,
        "provider": "ollama",
        "model": "qwen3.5:9b",
        "attempt": 1,
        "attempts": 1,
        "backoff_seconds": 0.0,
        "latency_ms": 1.0,
        "fallback_used": False,
        "circuit_open": False,
        "is_repair": False,
        "outcome": "ok",
        "error_type": None,
        "at": "2026-09-21T00:00:00+00:00",
    }
    base.update(overrides)
    return base


async def _running_job(db) -> dict:
    project = await _project(db)
    job, _ = await ai_job_service.create_job(db, project["id"], "script", {})
    return await ai_job_service.transition_status(db, job["id"], "running")


async def test_record_generation_call_appends_to_metrics_json(db):
    job = await _running_job(db)
    updated = await ai_job_service.record_generation_call(db, job["id"], _call())
    assert json.loads(updated["metrics_json"])["calls"] == [_call()]


async def test_record_generation_call_bounds_calls_and_drops_oldest(db):
    job = await _running_job(db)
    for i in range(AI_JOB_MAX_RECORDED_CALLS + 5):
        updated = await ai_job_service.record_generation_call(db, job["id"], _call(attempt=i))
    calls = json.loads(updated["metrics_json"])["calls"]
    assert len(calls) == AI_JOB_MAX_RECORDED_CALLS
    # the oldest 5 (attempt=0..4) were dropped -- the list keeps the most recent.
    assert calls[0]["attempt"] == 5
    assert calls[-1]["attempt"] == AI_JOB_MAX_RECORDED_CALLS + 4


async def test_record_generation_call_sets_actual_provider_and_model(db):
    job = await _running_job(db)
    updated = await ai_job_service.record_generation_call(
        db, job["id"], _call(provider="gemini", model="gemini-3.8-flash")
    )
    assert updated["actual_provider"] == "gemini"
    assert updated["model"] == "gemini-3.8-flash"


async def test_record_generation_call_never_overwrites_actual_provider_with_none(db):
    """An outcome="error" call has provider=None/model=None -- it must never null
    out a value a prior successful call on the same job already set."""
    job = await _running_job(db)
    await ai_job_service.record_generation_call(db, job["id"], _call(provider="gemini", model="gemini-3.8-flash"))
    updated = await ai_job_service.record_generation_call(
        db, job["id"], _call(provider=None, model=None, outcome="error", error_type="ProviderUnavailableError")
    )
    assert updated["actual_provider"] == "gemini"
    assert updated["model"] == "gemini-3.8-flash"


async def test_record_generation_call_increments_fallback_count_only_when_reported(db):
    job = await _running_job(db)
    after_no_fallback = await ai_job_service.record_generation_call(db, job["id"], _call(fallback_used=False))
    assert after_no_fallback["fallback_used"] == 0
    assert after_no_fallback["fallback_count"] == 0

    after_fallback = await ai_job_service.record_generation_call(
        db, job["id"], _call(provider="gemini", fallback_used=True)
    )
    assert after_fallback["fallback_used"] == 1
    assert after_fallback["fallback_count"] == 1


async def test_record_generation_call_sets_fallback_reason_only_when_provided(db):
    job = await _running_job(db)
    updated = await ai_job_service.record_generation_call(
        db, job["id"], _call(fallback_used=True, fallback_reason="ProviderUnavailableError")
    )
    assert updated["fallback_reason"] == "ProviderUnavailableError"


async def test_record_generation_call_increments_repair_count_only_for_is_repair(db):
    job = await _running_job(db)
    after_non_repair = await ai_job_service.record_generation_call(db, job["id"], _call(is_repair=False))
    assert after_non_repair["repair_count"] == 0

    after_repair = await ai_job_service.record_generation_call(db, job["id"], _call(is_repair=True))
    assert after_repair["repair_count"] == 1


async def test_record_generation_call_refuses_a_terminal_job(db):
    job = await _running_job(db)
    await ai_job_service.transition_status(db, job["id"], "error", error_code="boom")
    with pytest.raises(ValidationError):
        await ai_job_service.record_generation_call(db, job["id"], _call())


async def test_record_generation_call_raises_not_found_for_unknown_job(db):
    with pytest.raises(NotFoundError):
        await ai_job_service.record_generation_call(db, "does-not-exist", _call())


# --- Task 15.3: set_job_metric ---------------------------------------------------------


async def test_set_job_metric_sets_a_new_key(db):
    job = await _running_job(db)
    updated = await ai_job_service.set_job_metric(db, job["id"], "dropped_items", [{"kind": "idiom", "key": "x"}])
    assert json.loads(updated["metrics_json"])["dropped_items"] == [{"kind": "idiom", "key": "x"}]


async def test_set_job_metric_does_not_disturb_the_existing_calls_list(db):
    job = await _running_job(db)
    await ai_job_service.record_generation_call(db, job["id"], _call())
    updated = await ai_job_service.set_job_metric(db, job["id"], "dropped_items", ["x"])
    metrics = json.loads(updated["metrics_json"])
    assert metrics["calls"] == [_call()]
    assert metrics["dropped_items"] == ["x"]


async def test_set_job_metric_safe_on_a_job_with_no_prior_metrics_json(db):
    """A freshly-created job's metrics_json is the default `"{}"` -- confirms
    the read-modify-write handles that starting point, not just a job that
    already has a `"calls"` list."""
    job = await _running_job(db)
    assert json.loads(job["metrics_json"]) == {}
    updated = await ai_job_service.set_job_metric(db, job["id"], "dropped_items", ["x"])
    assert json.loads(updated["metrics_json"]) == {"dropped_items": ["x"]}


async def test_set_job_metric_overwrites_its_own_key_on_a_second_call(db):
    job = await _running_job(db)
    await ai_job_service.set_job_metric(db, job["id"], "dropped_items", ["first"])
    updated = await ai_job_service.set_job_metric(db, job["id"], "dropped_items", ["second"])
    assert json.loads(updated["metrics_json"])["dropped_items"] == ["second"]


async def test_set_job_metric_raises_not_found_for_unknown_job(db):
    with pytest.raises(NotFoundError):
        await ai_job_service.set_job_metric(db, "does-not-exist", "dropped_items", [])


async def test_set_job_metric_commit_false_leaves_the_caller_in_control(db, monkeypatch):
    """Mirrors `record_generation_call`'s own `commit=False` contract (Task 15.3
    call site: `learning_pipeline` sets this inside its own `write_transaction`)
    -- confirms `set_job_metric` itself never calls `db.commit()` when told not
    to."""
    job = await _running_job(db)
    committed = []
    original_commit = db.commit

    async def _tracking_commit():
        committed.append(True)
        await original_commit()

    monkeypatch.setattr(db, "commit", _tracking_commit)
    await ai_job_service.set_job_metric(db, job["id"], "dropped_items", ["x"], commit=False)
    assert committed == []


# --- Task 14.2: provider_error_code ----------------------------------------------------


@pytest.mark.parametrize(
    "exc,expected_code",
    [
        (ProviderUnavailableError("down"), "provider_unavailable"),
        (ProviderTimeoutError("slow"), "provider_timeout"),
        (ProviderRateLimitError("429"), "provider_rate_limited"),
        (ProviderAuthError("bad key"), "provider_auth"),
        (ProviderInvalidResponseError("bad shape"), "provider_invalid_response"),
        (SchemaValidationError("bad json"), "schema_validation_failed"),
    ],
)
def test_provider_error_code_maps_known_subclasses(exc, expected_code):
    assert ai_job_service.provider_error_code(exc) == expected_code


def test_provider_error_code_falls_back_to_provider_error_for_the_base_class():
    assert ai_job_service.provider_error_code(ProviderError("generic")) == "provider_error"


def test_provider_error_code_maps_schema_validation_error_to_content_not_infra():
    """Amendment B (2026-09-21): SchemaValidationError is a ProviderError subclass
    structurally but a *content* failure -- it must map to its own code, never fall
    through to the generic "provider_error" (which Gate B-2's classification reads
    as `infra` purely from the "provider_" prefix -- plan §4.4)."""
    code = ai_job_service.provider_error_code(SchemaValidationError("bad json"))
    assert code == "schema_validation_failed"
    assert not code.startswith("provider_")
