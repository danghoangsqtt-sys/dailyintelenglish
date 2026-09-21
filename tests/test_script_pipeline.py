"""Tests for the checkpointed script pipeline (Task 13.4)."""

import json
from pathlib import Path

import pytest

from app.core.exceptions import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.models.project import ProjectUpdate, ScriptConfig, SpeakerConfig
from app.services import ai_job_service, project_service, script_pipeline, script_service
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter
from app.services.ai_worker import AIWorker


async def _no_op_sleep(delay: float) -> None:
    """Task 14.2 error-code tests exercise the router's real transient-error
    exhaustion path (4 attempts) -- patched onto `app.services.ai.router.sleep`
    so nothing actually waits out the backoff. See tests/test_ai_router.py's
    `sleep_calls` fixture for the same pattern."""
    return None

GOLDEN_FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "ai" / "golden_projects.json"


def _load_golden_projects() -> dict[str, dict]:
    data = json.loads(GOLDEN_FIXTURES_PATH.read_text(encoding="utf-8"))
    return {project["fixture_id"]: project for project in data["projects"]}


def _words(count: int, start: int = 0) -> str:
    """`count` globally-unique tokens -- guarantees no accidental duplicate lines
    or repeated 8-grams across a test's whole fabricated transcript."""
    return " ".join(f"word{start + i}" for i in range(count))


def _result(text: str) -> GenerationResult:
    return GenerationResult(
        text=text, provider="fake-gemini", model="fake-model", latency_ms=1.0, attempt=1, prompt_hash="abc123"
    )


def make_config(duration_minutes: float = 1.0, topic: str = "healthy morning habits") -> ScriptConfig:
    return ScriptConfig(
        name="Pipeline test",
        topic=topic,
        cefr_level="B1",
        duration_minutes=duration_minutes,
        num_speakers=2,
        genre="interview",
        accent="american",
        speakers=[
            SpeakerConfig(name="Alex", gender="male", accent="american"),
            SpeakerConfig(name="Maya", gender="female", accent="american"),
        ],
    )


async def _project(db, **overrides) -> dict:
    return await project_service.create_project(db, make_config(**overrides))


def _build_router(gemini_outcomes: list) -> tuple[AIRouter, FakeProvider, FakeProvider]:
    gemini = FakeProvider("gemini", gemini_outcomes)
    local = FakeProvider("ollama", [])
    return AIRouter(local=local, gemini=gemini, mode=AIMode.GEMINI), gemini, local


# --- pure functions: word budgets ---------------------------------------------------


@pytest.mark.parametrize(
    "fixture_id,expected_words",
    [
        ("a2_5min_daily_routine", 450),
        ("b1_8min_remote_work", 800),
        ("c1_10min_urban_policy", 1300),
    ],
)
def test_compute_target_words_matches_golden_fixtures(fixture_id, expected_words):
    projects = _load_golden_projects()
    project = projects[fixture_id]
    assert script_pipeline.compute_target_words(project["cefr_level"], project["duration_minutes"]) == expected_words


def test_plan_sections_sums_to_target_words():
    for target, level in [(450, "A2"), (800, "B1"), (1300, "C1"), (1, "A1")]:
        budgets = script_pipeline.plan_sections(target, level)
        assert sum(budgets) == target
        assert all(budget > 0 for budget in budgets)


def test_plan_sections_splits_into_roughly_90_second_chunks():
    # B1 100 wpm * 1.5 min = 150 words/section -> 800 words should split into ~5 sections.
    budgets = script_pipeline.plan_sections(800, "B1")
    assert len(budgets) == 5


# --- pure functions: validators -----------------------------------------------------


def test_validate_section_accepts_a_balanced_valid_section():
    lines = [
        script_pipeline.SectionLineOut(speaker_id="a", text=_words(50, 0)),
        script_pipeline.SectionLineOut(speaker_id="b", text=_words(50, 50)),
    ]
    assert script_pipeline.validate_section(lines, 100, {"a", "b"}) == []


def test_validate_section_rejects_word_count_outside_tolerance():
    lines = [script_pipeline.SectionLineOut(speaker_id="a", text=_words(10))]
    errors = script_pipeline.validate_section(lines, 100, {"a"})
    assert any("word count" in error for error in errors)


def test_validate_section_rejects_unknown_speaker():
    lines = [script_pipeline.SectionLineOut(speaker_id="ghost", text=_words(100))]
    errors = script_pipeline.validate_section(lines, 100, {"a", "b"})
    assert any("unknown speaker_id" in error for error in errors)


def test_validate_section_rejects_too_many_consecutive_lines():
    lines = [script_pipeline.SectionLineOut(speaker_id="a", text=_words(15, i * 15)) for i in range(6)]
    errors = script_pipeline.validate_section(lines, 90, {"a", "b"})
    assert any("consecutive lines" in error for error in errors)


def test_validate_section_skips_consecutive_check_for_a_single_speaker():
    lines = [script_pipeline.SectionLineOut(speaker_id="a", text=_words(15, i * 15)) for i in range(6)]
    errors = script_pipeline.validate_section(lines, 90, {"a"})
    assert not any("consecutive lines" in error for error in errors)


def test_validate_global_rejects_speaker_imbalance_for_two_speakers():
    lines = [
        script_pipeline.SectionLineOut(speaker_id="a", text=_words(90, 0)),
        script_pipeline.SectionLineOut(speaker_id="b", text=_words(10, 90)),
    ]
    hard_errors, _warnings = script_pipeline.validate_global(lines, 100, {"a", "b"}, 2, "topic")
    assert any("word share" in error for error in hard_errors)


def test_validate_global_skips_balance_check_for_solo_speaker():
    lines = [script_pipeline.SectionLineOut(speaker_id="a", text=_words(100, 0))]
    hard_errors, _warnings = script_pipeline.validate_global(lines, 100, {"a"}, 1, "topic")
    assert hard_errors == []


def test_validate_global_rejects_exact_duplicate_lines():
    lines = [
        script_pipeline.SectionLineOut(speaker_id="a", text="the exact same line"),
        script_pipeline.SectionLineOut(speaker_id="b", text="The Exact Same Line"),
    ]
    hard_errors, _warnings = script_pipeline.validate_global(lines, 8, {"a", "b"}, 2, "topic")
    assert any("duplicate" in error for error in hard_errors)


def test_repeated_8gram_ratio_detects_real_repetition():
    words = "a b c d e f g h".split() * 3
    assert script_pipeline.repeated_8gram_ratio(words) > 0.5


def test_repeated_8gram_ratio_zero_for_unique_text():
    words = _words(50).split()
    assert script_pipeline.repeated_8gram_ratio(words) == 0.0


def test_validate_global_topic_relevance_is_a_warning_not_a_hard_error():
    lines = [script_pipeline.SectionLineOut(speaker_id="a", text=_words(100, 0))]
    hard_errors, warnings = script_pipeline.validate_global(
        lines, 100, {"a"}, 1, "a very specific unrelated keyword"
    )
    assert hard_errors == []
    assert any("topic keyword" in warning for warning in warnings)


# --- handler: end-to-end with a FakeProvider-backed router --------------------------


async def test_pipeline_happy_path_completes_and_saves_script(db):
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "Morning Routines",
            "sections": [{"index": 1, "objective": "discuss a simple healthy morning routine", "target_words": 100}],
        }
    )
    section_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 0)},
            {"speaker_id": maya_id, "text": _words(25, 25)},
            {"speaker_id": alex_id, "text": _words(25, 50)},
            {"speaker_id": maya_id, "text": _words(25, 75)},
        ]
    )
    router, gemini, local = _build_router([_result(outline_json), _result(section_json)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert local.call_count == 0

    lines = await script_service.get_script(db, project["id"])
    assert len(lines) == 4
    assert all(line["id"] for line in lines)  # server-assigned, never model-supplied

    final_project = await project_service.get_project(db, project["id"])
    assert final_project["status"] == "script_generated"


async def test_pipeline_repairs_an_invalid_section_once_then_completes(db):
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    invalid_section_json = json.dumps([{"speaker_id": alex_id, "text": _words(5, 0)}])  # way too short
    repaired_section_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 0)},
            {"speaker_id": maya_id, "text": _words(25, 25)},
            {"speaker_id": alex_id, "text": _words(25, 50)},
            {"speaker_id": maya_id, "text": _words(25, 75)},
        ]
    )
    router, gemini, _local = _build_router(
        [_result(outline_json), _result(invalid_section_json), _result(repaired_section_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert gemini.call_count == 3  # outline + invalid attempt + one repair
    lines = await script_service.get_script(db, project["id"])
    assert len(lines) == 4


async def test_pipeline_fails_transparently_when_repair_also_fails(db):
    project = await _project(db)
    alex_id = project["speakers"][0]["id"]

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    invalid_json = json.dumps([{"speaker_id": alex_id, "text": _words(5, 0)}])
    still_invalid_json = json.dumps([{"speaker_id": alex_id, "text": _words(6, 100)}])
    router, gemini, _local = _build_router(
        [_result(outline_json), _result(invalid_json), _result(still_invalid_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == "section_validation_failed"
    # prior state (none, for a fresh project) is provably unchanged -- no partial script.
    lines = await script_service.get_script(db, project["id"])
    assert lines == []


async def test_pipeline_resumes_from_checkpoint_after_interruption(db):
    project = await _project(db, duration_minutes=2.0)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first half of the discussion", "target_words": 100},
                {"index": 2, "objective": "cover the second half of the discussion", "target_words": 100},
            ],
        }
    )
    section1_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 0)},
            {"speaker_id": maya_id, "text": _words(25, 25)},
            {"speaker_id": alex_id, "text": _words(25, 50)},
            {"speaker_id": maya_id, "text": _words(25, 75)},
        ]
    )
    section2_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 100)},
            {"speaker_id": maya_id, "text": _words(25, 125)},
            {"speaker_id": alex_id, "text": _words(25, 150)},
            {"speaker_id": maya_id, "text": _words(25, 175)},
        ]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    router_first_run, _gemini1, _local1 = _build_router([_result(outline_json), _result(section1_json)])
    with pytest.raises(RuntimeError, match="no more scripted outcomes"):
        await script_pipeline.make_handler(router_first_run)(claimed, worker)

    mid_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert mid_job["status"] == "running"
    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    assert {checkpoint["section_index"] for checkpoint in checkpoints} == {0, 1}

    router_second_run, gemini2, _local2 = _build_router([_result(section2_json)])
    await script_pipeline.make_handler(router_second_run)(mid_job, worker)

    assert gemini2.call_count == 1  # only section 2 -- outline/section 1 not regenerated

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    lines = await script_service.get_script(db, project["id"])
    assert len(lines) == 8


async def test_pipeline_cancels_when_already_requested_before_processing(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    await ai_job_service.claim_job(db, job["id"], "worker-1")
    await ai_job_service.request_cancel(db, job["id"], project["id"])
    fresh_claimed = await ai_job_service.get_job(db, job["id"], project["id"])

    router, gemini, _local = _build_router([])
    worker = AIWorker(db_getter=lambda: db)
    await script_pipeline.make_handler(router)(fresh_claimed, worker)

    result = await ai_job_service.get_job(db, job["id"], project["id"])
    assert result["status"] == "cancelled"
    assert gemini.call_count == 0


async def test_pipeline_marks_stale_when_project_changed_since_job_creation(db):
    project = await _project(db)
    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")

    await project_service.update_project(
        db, project["id"], ProjectUpdate(topic="A completely different topic than before")
    )

    router, gemini, _local = _build_router([])
    worker = AIWorker(db_getter=lambda: db)
    await script_pipeline.make_handler(router)(claimed, worker)

    result = await ai_job_service.get_job(db, job["id"], project["id"])
    assert result["status"] == "stale"
    assert gemini.call_count == 0


# --- Task 14.2: job/checkpoint telemetry -----------------------------------------------


async def test_pipeline_happy_path_records_zero_repairs_and_ok_calls(db):
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "Morning Routines",
            "sections": [{"index": 1, "objective": "discuss a simple healthy morning routine", "target_words": 100}],
        }
    )
    section_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 0)},
            {"speaker_id": maya_id, "text": _words(25, 25)},
            {"speaker_id": alex_id, "text": _words(25, 50)},
            {"speaker_id": maya_id, "text": _words(25, 75)},
        ]
    )
    router, gemini, _local = _build_router([_result(outline_json), _result(section_json)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert final_job["repair_count"] == 0
    calls = json.loads(final_job["metrics_json"])["calls"]
    assert len(calls) == 2  # outline + 1 section
    assert [call["purpose"] for call in calls] == ["script_outline", "script_section"]
    assert all(call["outcome"] == "ok" for call in calls)
    assert all(call["is_repair"] is False for call in calls)
    assert calls[0]["section_index"] is None
    assert calls[1]["section_index"] == 1


async def test_pipeline_repair_sets_repair_count_and_checkpoint_metrics(db):
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    invalid_section_json = json.dumps([{"speaker_id": alex_id, "text": _words(5, 0)}])  # way too short
    repaired_section_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 0)},
            {"speaker_id": maya_id, "text": _words(25, 25)},
            {"speaker_id": alex_id, "text": _words(25, 50)},
            {"speaker_id": maya_id, "text": _words(25, 75)},
        ]
    )
    router, gemini, _local = _build_router(
        [_result(outline_json), _result(invalid_section_json), _result(repaired_section_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert final_job["repair_count"] == 1

    calls = json.loads(final_job["metrics_json"])["calls"]
    assert [call["purpose"] for call in calls] == ["script_outline", "script_section", "script_section_repair"]
    assert calls[2]["is_repair"] is True

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    section_checkpoint = next(c for c in checkpoints if c["section_index"] == 1)
    metrics = json.loads(section_checkpoint["metrics_json"])
    assert metrics["repaired"] is True
    assert metrics["words_before_repair"] == 5
    assert metrics["errors_before_repair"] > 0
    assert metrics["target_nominal"] == 100
    assert metrics["target_effective"] == 100  # unchanged until Task 14.3
    assert metrics["words"] == 100


async def test_pipeline_happy_path_section_checkpoint_has_unrepaired_metrics(db):
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    section_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 0)},
            {"speaker_id": maya_id, "text": _words(25, 25)},
            {"speaker_id": alex_id, "text": _words(25, 50)},
            {"speaker_id": maya_id, "text": _words(25, 75)},
        ]
    )
    router, gemini, _local = _build_router([_result(outline_json), _result(section_json)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    section_checkpoint = next(c for c in checkpoints if c["section_index"] == 1)
    metrics = json.loads(section_checkpoint["metrics_json"])
    assert metrics["repaired"] is False
    assert metrics["words_before_repair"] is None
    assert metrics["errors_before_repair"] == 0


async def test_pipeline_hybrid_fallback_records_fallback_telemetry(db, monkeypatch):
    monkeypatch.setattr("app.services.ai.router.sleep", _no_op_sleep)
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    section_json = json.dumps(
        [
            {"speaker_id": alex_id, "text": _words(25, 0)},
            {"speaker_id": maya_id, "text": _words(25, 25)},
            {"speaker_id": alex_id, "text": _words(25, 50)},
            {"speaker_id": maya_id, "text": _words(25, 75)},
        ]
    )
    # AI_TRANSIENT_MAX_ATTEMPTS=4: local exhausts on the outline call; failure_threshold=1
    # opens the circuit immediately after, so the section call skips straight to gemini
    # (matches the plan's "no nested retries" / one-fallback-per-route shape).
    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [_result(outline_json), _result(section_json)])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID, failure_threshold=1, cooldown_seconds=60.0)

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert final_job["fallback_used"] == 1
    assert final_job["fallback_count"] >= 1
    # "fake-gemini" -- this test file's own `_result()` helper's hardcoded provider
    # name (the router trusts whatever `GenerationResult.provider` the provider
    # returns; it never derives it from the FakeProvider's own `name`).
    assert final_job["actual_provider"] == "fake-gemini"


@pytest.mark.parametrize(
    "outcomes,expected_error_code",
    [
        ([ProviderUnavailableError("down")] * 4, "provider_unavailable"),
        ([ProviderTimeoutError("slow")] * 4, "provider_timeout"),
        ([ProviderRateLimitError("429")] * 4, "provider_rate_limited"),
        ([ProviderAuthError("bad key")] * 1, "provider_auth"),
        ([ProviderInvalidResponseError("bad shape")] * 2, "provider_invalid_response"),
    ],
)
async def test_pipeline_maps_provider_errors_to_specific_error_codes(db, monkeypatch, outcomes, expected_error_code):
    monkeypatch.setattr("app.services.ai.router.sleep", _no_op_sleep)
    project = await _project(db)
    router, gemini, _local = _build_router(list(outcomes))

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == expected_error_code
    assert final_job["error_code"] != "handler_exception"
    # the outline call itself is telemetered even though it failed the job.
    calls = json.loads(final_job["metrics_json"])["calls"]
    assert calls[-1]["outcome"] == "error"
    assert calls[-1]["purpose"] == "script_outline"
    lines = await script_service.get_script(db, project["id"])
    assert lines == []  # no partial script from a job that never got past the outline


async def test_pipeline_maps_unparseable_outline_to_schema_validation_failed_not_provider_error(db):
    """Amendment B (Task 14.2-b): SchemaValidationError is a ProviderError subclass
    structurally but a content failure -- the outline path's `except ProviderError`
    must still land on `schema_validation_failed`, never the generic `provider_error`
    that Gate B-2's classification would read as infrastructure (plan §4.4)."""
    project = await _project(db)
    router, gemini, _local = _build_router([_result("not valid json")])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == "schema_validation_failed"
    assert not final_job["error_code"].startswith("provider_")
    assert final_job["error_code"] != "handler_exception"
