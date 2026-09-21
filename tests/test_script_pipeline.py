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


def _section_json(*speaker_words_start: tuple[str, int, int]) -> str:
    """Build a `SectionLineOut[]` JSON body from `(speaker_id, word_count,
    start_offset)` tuples -- one line per tuple. `start_offset` keeps every
    line's tokens globally unique across a test (see `_words`)."""
    return json.dumps(
        [{"speaker_id": speaker_id, "text": _words(count, start)} for speaker_id, count, start in speaker_words_start]
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


# --- pure functions: Task 14.3 effective-target/clamp/carry math --------------------


def test_clamp_bounds_a_value_into_range():
    assert script_pipeline.clamp(5, 0, 10) == 5
    assert script_pipeline.clamp(-5, 0, 10) == 0
    assert script_pipeline.clamp(15, 0, 10) == 10


def test_compute_section_effective_target_applies_carry_within_the_cap():
    # nominal=160, carry=+20 -> 180, within [160*0.65, 160*1.35] = [104, 216].
    assert script_pipeline.compute_section_effective_target(160, 20.0) == 180
    # nominal=160, carry=-20 -> 140, still within bounds.
    assert script_pipeline.compute_section_effective_target(160, -20.0) == 140


def test_compute_section_effective_target_clamps_large_carry():
    assert script_pipeline.compute_section_effective_target(100, 1000.0) == 135  # 100*1.35
    assert script_pipeline.compute_section_effective_target(100, -1000.0) == 65  # 100*0.65


def test_compute_last_section_effective_target_aims_at_the_remaining_budget():
    # nominal_last=150, episode target=800, 650 words already written -> exactly
    # the 150 words remaining, well within [150*0.5, 150*1.5] = [75, 225].
    assert script_pipeline.compute_last_section_effective_target(150, 800, 650) == 150


def test_compute_last_section_effective_target_clamps_a_large_remaining_budget():
    # Only 200 words written so far -> 600 words remain, clamped down to 150*1.5=225.
    assert script_pipeline.compute_last_section_effective_target(150, 800, 200) == 225
    # 790 words already written -> only 10 remain, clamped up to 150*0.5=75.
    assert script_pipeline.compute_last_section_effective_target(150, 800, 790) == 75


def test_carry_update_preserves_the_clamp_residual_for_the_next_section():
    """Plan §4.3 item 2's "residual beyond the clamp stays in carry": the
    formula `carry = carry + (effective_i - actual_i)` never resets `carry` to
    just the clamped delta, so whatever the clamp couldn't apply to section i
    is still available to section i+1 (and beyond)."""
    carry = 0.0
    effective_1 = script_pipeline.compute_section_effective_target(100, carry)
    assert effective_1 == 100
    carry += effective_1 - 0  # section 1 undershoots completely (actual=0)
    assert carry == 100.0

    # nominal(100) + carry(100) = 200, clamped down to 100*1.35=135 -- 65 words
    # of the requested 200 could not be applied this section.
    effective_2 = script_pipeline.compute_section_effective_target(100, carry)
    assert effective_2 == 135
    carry += effective_2 - 135  # section 2 lands exactly on its clamped target
    # carry is unchanged by section 2's clamp -- the 65-word residual survives.
    assert carry == 100.0


def test_resume_carry_recomputation_from_stored_target_effective_matches_live_replay():
    """PM's Amendment (task-14.3.md "Resume/carry" decision, condition 2): proves
    that reading `target_effective` off checkpoints and replaying the same
    formula purely from nominal targets + actual words produce an identical
    final `carry` -- not two independent sources of truth that could diverge."""
    nominal_sequence = [160, 145, 170]
    actual_sequence = [120, 200, 150]

    # (a) "live" sequential computation -- what an uninterrupted run does.
    live_carry = 0.0
    live_effectives: list[int] = []
    for nominal, actual in zip(nominal_sequence, actual_sequence, strict=True):
        effective = script_pipeline.compute_section_effective_target(nominal, live_carry)
        live_effectives.append(effective)
        live_carry += effective - actual

    # (b) resume-style recomputation reading each checkpoint's stored
    # `target_effective` (exactly what `_run_script_job`'s upfront resume pass does).
    resumed_carry = 0.0
    for effective, actual in zip(live_effectives, actual_sequence, strict=True):
        resumed_carry += effective - actual

    # (c) "replay from nominal" -- recompute effective_i from scratch using only
    # nominal targets + actual words, never trusting a stored value (the plan
    # prose's literal "against the outline's nominal targets" reading).
    replayed_carry = 0.0
    for nominal, actual in zip(nominal_sequence, actual_sequence, strict=True):
        effective = script_pipeline.compute_section_effective_target(nominal, replayed_carry)
        replayed_carry += effective - actual

    assert resumed_carry == live_carry
    assert replayed_carry == live_carry


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


# --- pure functions: Task 14.3's structural/word-budget split -----------------------


def test_validate_section_structure_and_word_budget_together_equal_validate_section():
    """Task 14.3 split `validate_section` into two functions; `validate_section`
    itself is kept as their concatenation for existing callers -- this pins that
    equivalence directly rather than relying only on the individual tests above."""
    lines = [script_pipeline.SectionLineOut(speaker_id="ghost", text=_words(10))]
    combined = script_pipeline.validate_section(lines, 100, {"a", "b"})
    split = script_pipeline.validate_section_structure(
        lines, {"a", "b"}
    ) + script_pipeline.validate_section_word_budget(lines, 100)
    assert sorted(combined) == sorted(split)


def test_validate_section_word_budget_returns_empty_for_no_lines():
    """The "no lines" case is `validate_section_structure`'s job -- the budget
    check must not also report it (would double-report the same root cause)."""
    assert script_pipeline.validate_section_word_budget([], 100) == []


def test_validate_section_structure_passes_a_word_deviation_that_word_budget_rejects():
    """The whole point of the 14.3 split: a section can be structurally clean
    while still failing its word budget -- the two must be independently checkable."""
    lines = [script_pipeline.SectionLineOut(speaker_id="a", text=_words(10))]
    assert script_pipeline.validate_section_structure(lines, {"a"}) == []
    assert script_pipeline.validate_section_word_budget(lines, 100) != []


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


def test_constants_pin_word_tolerances_are_unchanged_by_task_14_3():
    """Task 14.3/14.8 governance note: SCRIPT_GLOBAL_WORD_TOLERANCE,
    SCRIPT_SECTION_WORD_TOLERANCE, and SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER
    are a stop condition, not an implementation choice -- this pins all three
    values so a silent edit fails CI."""
    from app.core import constants

    assert constants.SCRIPT_GLOBAL_WORD_TOLERANCE == 0.10
    assert constants.SCRIPT_SECTION_WORD_TOLERANCE == 0.15
    assert constants.SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER == 5


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


async def test_pipeline_section_prompt_word_range_matches_the_tolerance_constant(db):
    """Task 14.8-b (CR-02): the word-count range shown in the section prompt is
    computed from SCRIPT_SECTION_WORD_TOLERANCE at render time, not a second,
    hard-coded copy of it in the template -- pins the two from silently
    drifting apart."""
    from app.core.constants import SCRIPT_SECTION_WORD_TOLERANCE

    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
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

    section_prompt = gemini.calls[1].prompt  # calls[0] is the outline
    min_words = round(100 * (1 - SCRIPT_SECTION_WORD_TOLERANCE))
    max_words = round(100 * (1 + SCRIPT_SECTION_WORD_TOLERANCE))
    assert f"between {min_words} and {max_words} spoken words" in section_prompt


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
    """Task 14.3 changed assertion: this test previously used two word-count-only
    failures (5 then 6 words against a 100-word target) to exercise "repair also
    fails". Under Task 14.3, a word-deviation-only failure that survives repair is
    now *accepted* (accept-and-carry -- the whole point of this task), so that
    fixture would no longer reach `section_validation_failed` here at all. Switched
    to an unknown-speaker id, a *structural* error, which still unconditionally
    hard-fails after repair (task-14.3.md required behaviour item 4/verification
    item 6) -- this test now exercises exactly that unchanged path."""
    project = await _project(db)
    ghost_id = "00000000-0000-0000-0000-000000000000"  # not one of this project's speakers

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    invalid_json = json.dumps([{"speaker_id": ghost_id, "text": _words(100, 0)}])
    still_invalid_json = json.dumps([{"speaker_id": ghost_id, "text": _words(100, 100)}])
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


# --- Task 14.3: running section budget, hard gate only at the global total ---------


async def test_pipeline_accepts_off_target_sections_when_total_lands_inside_tolerance(db):
    """Verification item 3: five sections each land far outside ±15% of their own
    NOMINAL target even after their one repair pass, but the pipeline accepts
    every one of them (accept-and-carry, no job-killing per-section gate) and the
    episode completes because the TOTAL lands inside the product's only hard
    gate, ±10% of the whole-episode target -- mirroring the plan's own measured
    evidence (the one Phase 13 job that passed had per-section deviations from
    -14% to +3% while the total was -2.4%)."""
    project = await _project(db, duration_minutes=8.0)  # B1 100wpm*8 = 800 target_words
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": i, "objective": "cover part of the topic here", "target_words": 160}
                for i in range(1, 6)
            ],
        }
    )

    outcomes = [_result(outline_json)]
    # Sections 1-4 (non-last): a deliberately bad first attempt (100 words)
    # triggers the one repair pass; the repair's output (130 words) is STILL
    # outside ±15% of that section's (carry-shifted) effective target --
    # accepted off-target rather than failing the job.
    for i in range(4):
        speaker = alex_id if i % 2 == 0 else maya_id
        outcomes.append(_result(_section_json((speaker, 100, i * 1000))))
        outcomes.append(_result(_section_json((speaker, 130, i * 1000 + 500))))
    # Section 5 (last): lands exactly on its own clamped effective target (240)
    # -- no repair needed -- split 50/50 across both speakers for global balance.
    outcomes.append(_result(_section_json((alex_id, 120, 9000), (maya_id, 120, 9200))))

    router, gemini, _local = _build_router(outcomes)

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    assert final_job["repair_count"] == 4  # one repair per non-last section
    assert gemini.call_count == len(outcomes)  # nothing left un-consumed or over-called

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    section_checkpoints = [c for c in checkpoints if c["stage"] == "section"]
    assert len(section_checkpoints) == 5
    for checkpoint in section_checkpoints:
        metrics = json.loads(checkpoint["metrics_json"])
        assert set(metrics) == {
            "target_nominal", "target_effective", "words", "deviation_pct",
            "repaired", "words_before_repair", "errors_before_repair",
            "length_repaired", "words_before_length_repair",
        }
        assert metrics["length_repaired"] is False  # 130 never exceeds any clamped ceiling here
        assert metrics["target_nominal"] == 160

    lines = await script_service.get_script(db, project["id"])
    assert len(lines) == 4 + 2  # sections 1-4's one line each + section 5's two lines


async def test_pipeline_final_section_budget_repair_brings_the_total_inside_tolerance(db):
    """Verification item 4: the last section lands exactly on its own (clamped)
    effective target -- passing its own ±15% check -- but because that target
    was clamped well short of the true remaining need, the merged total still
    misses the global ±10% gate. The one final-section budget repair (item 6)
    regenerates just the last section against the *real* remaining word count
    and the job completes; `repair_count` reflects exactly that one extra
    repair, and the last section's checkpoint is overwritten with the new text."""
    project = await _project(db, duration_minutes=8.0)  # target_words = 800
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first part here", "target_words": 300},
                {"index": 2, "objective": "cover the second part here", "target_words": 100},
            ],
        }
    )
    # Section 1: lands exactly on its effective target (300, carry=0) -- no repair.
    section1_json = _section_json((alex_id, 300, 0))
    # Section 2 (last, nominal=100): true remaining need is 800-300=500, but
    # clamped to 100*1.5=150 (SCRIPT_LAST_SECTION_CARRY_CAP=0.5) -- landing
    # exactly on that clamped 150 passes the section's own ±15% check, yet the
    # total (300+150=450) is nowhere near the global ±10% band [720, 880].
    section2_first_json = _section_json((maya_id, 150, 1000))
    # Final-section budget repair targets the real deficit (800-300=500) --
    # scripted to land close enough (470) to bring the total inside tolerance.
    section2_repaired_json = _section_json((maya_id, 470, 2000))

    router, gemini, _local = _build_router(
        [_result(outline_json), _result(section1_json), _result(section2_first_json), _result(section2_repaired_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    assert final_job["repair_count"] == 1  # exactly the one final-section budget repair
    assert gemini.call_count == 4

    lines = await script_service.get_script(db, project["id"])
    total_words = sum(len(text.split()) for text in (line["text"] for line in lines))
    assert 720 <= total_words <= 880

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    last_checkpoint = next(c for c in checkpoints if c["section_index"] == 2)
    metrics = json.loads(last_checkpoint["metrics_json"])
    assert metrics["repaired"] is True
    assert metrics["words"] == 470  # overwritten by the final-section repair, not the original 150


async def test_pipeline_global_validation_still_fails_after_one_final_section_repair(db):
    """Verification item 5: the one final-section budget repair is bounded
    (`SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS=1`) -- if its output still
    misses the global ±10% band, the job fails with `global_validation_failed`,
    no second attempt is made, and no partial script is saved."""
    project = await _project(db, duration_minutes=8.0)  # target_words = 800
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first part here", "target_words": 300},
                {"index": 2, "objective": "cover the second part here", "target_words": 100},
            ],
        }
    )
    section1_json = _section_json((alex_id, 300, 0))
    section2_first_json = _section_json((maya_id, 150, 1000))
    # The final-section budget repair's own output is STILL far short -- the
    # merged total (300+80=380) stays well outside [720, 880].
    section2_still_short_json = _section_json((maya_id, 80, 2000))

    router, gemini, _local = _build_router(
        [_result(outline_json), _result(section1_json), _result(section2_first_json), _result(section2_still_short_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == "global_validation_failed"
    # bounded: outline + section1 + section2 + exactly one final-section repair,
    # never a second attempt at the final-section budget repair.
    assert gemini.call_count == 4
    num_sections = 2
    assert final_job["repair_count"] <= num_sections + 1
    lines = await script_service.get_script(db, project["id"])
    assert lines == []  # no partial script from a job that never completed


async def test_pipeline_interrupted_with_drift_then_resumed_reaches_the_same_total_as_uninterrupted(db):
    """Verification item 7: a job interrupted after section 2 (with genuine
    per-section drift already recorded) and then resumed must recompute `carry`
    from the checkpoints and land on the same total an uninterrupted run of the
    identical scenario would reach."""
    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "part one", "target_words": 300},
                {"index": 2, "objective": "part two", "target_words": 300},
                {"index": 3, "objective": "part three", "target_words": 200},
            ],
        }
    )

    def _scenario_outcomes(alex_id: str, maya_id: str) -> list[GenerationResult]:
        # Section 1: effective=300 (carry=0), lands at 270 (within its own
        # ±15%, no repair) -- undershoots by 30, carry becomes 30.
        # Section 2: effective=clamp(300+30, ...)=330, lands at 310 (within
        # ±15% of 330, no repair) -- undershoots by 20 more, carry becomes 50.
        # Section 3 (last): words_so_far=580, remaining=800-580=220
        # (unclamped, within [100,300]) -- lands exactly on it.
        return [
            _result(_section_json((alex_id, 270, 0))),
            _result(_section_json((maya_id, 310, 1000))),
            _result(_section_json((alex_id, 110, 2000), (maya_id, 110, 2500))),
        ]

    # --- uninterrupted run: fresh project, all three outcomes scripted up front.
    uninterrupted_project = await _project(db, duration_minutes=8.0)
    u_alex_id, u_maya_id = (speaker["id"] for speaker in uninterrupted_project["speakers"])
    router_u, _gemini_u, _local_u = _build_router(
        [_result(outline_json), *_scenario_outcomes(u_alex_id, u_maya_id)]
    )
    job_u, _ = await ai_job_service.create_job(
        db, uninterrupted_project["id"], "script", {"project": uninterrupted_project, "operation": "script"}
    )
    claimed_u = await ai_job_service.claim_job(db, job_u["id"], "worker-1")
    worker_u = AIWorker(db_getter=lambda: db)
    await script_pipeline.make_handler(router_u)(claimed_u, worker_u)
    final_u = await ai_job_service.get_job(db, job_u["id"], uninterrupted_project["id"])
    assert final_u["status"] == "complete", final_u.get("error_message")
    lines_u = await script_service.get_script(db, uninterrupted_project["id"])
    total_u = sum(len(line["text"].split()) for line in lines_u)

    # --- interrupted-then-resumed run: identical scenario, a separate project
    # (each project mints its own speaker UUIDs, so the JSON bodies are built
    # fresh per-project via `_scenario_outcomes`, not reused from the run above).
    resumed_project = await _project(db, duration_minutes=8.0)
    r_alex_id, r_maya_id = (speaker["id"] for speaker in resumed_project["speakers"])
    resumed_outcomes = _scenario_outcomes(r_alex_id, r_maya_id)
    outcomes_first_run = [_result(outline_json), *resumed_outcomes[:2]]  # interrupted after section 2
    router_first, _gemini_first, _local_first = _build_router(outcomes_first_run)
    job_r, _ = await ai_job_service.create_job(
        db, resumed_project["id"], "script", {"project": resumed_project, "operation": "script"}
    )
    claimed_r = await ai_job_service.claim_job(db, job_r["id"], "worker-1")
    worker_r = AIWorker(db_getter=lambda: db)
    with pytest.raises(RuntimeError, match="no more scripted outcomes"):
        await script_pipeline.make_handler(router_first)(claimed_r, worker_r)

    mid_job = await ai_job_service.get_job(db, job_r["id"], resumed_project["id"])
    assert mid_job["status"] == "running"
    checkpoints = await ai_job_service.get_valid_checkpoints(db, job_r["id"])
    assert {c["section_index"] for c in checkpoints} == {0, 1, 2}

    router_second, _gemini_second, _local_second = _build_router(resumed_outcomes[2:])
    await script_pipeline.make_handler(router_second)(mid_job, worker_r)

    final_r = await ai_job_service.get_job(db, job_r["id"], resumed_project["id"])
    assert final_r["status"] == "complete", final_r.get("error_message")
    lines_r = await script_service.get_script(db, resumed_project["id"])
    total_r = sum(len(line["text"].split()) for line in lines_r)

    assert total_r == total_u


# --- Task 14.8: length-only repair pass ----------------------------------------------


async def test_pipeline_length_only_repair_fires_and_fixes_an_over_length_section(db):
    """Verification item 1: a section is still over
    effective_target * (1 + SCRIPT_SECTION_CARRY_CAP) after its one semantic
    repair -- the length-only pass fires and trims it inside tolerance; the
    checkpoint's metrics_json records both repair attempts."""
    project = await _project(db)  # duration_minutes=1.0 -> target_words=100, 1 section
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
    )
    attempt_json = _section_json((alex_id, 20, 0))  # way short -> triggers the one semantic repair
    # Repair output is itself way OVER effective_target(100) * 1.35 = 135 -> triggers the length-only pass.
    repair_json = _section_json((alex_id, 100, 1000), (maya_id, 100, 1500))  # 200 words
    length_repair_json = _section_json((alex_id, 50, 2000), (maya_id, 50, 2500))  # 100 words -- inside tolerance

    router, gemini, _local = _build_router(
        [_result(outline_json), _result(attempt_json), _result(repair_json), _result(length_repair_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    assert final_job["repair_count"] == 2  # one semantic + one length-only
    assert gemini.call_count == 4

    calls = json.loads(final_job["metrics_json"])["calls"]
    assert [call["purpose"] for call in calls] == [
        "script_outline", "script_section", "script_section_repair", "script_section_length_repair",
    ]

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    section_checkpoint = next(c for c in checkpoints if c["section_index"] == 1)
    metrics = json.loads(section_checkpoint["metrics_json"])
    assert metrics["repaired"] is True
    assert metrics["words_before_repair"] == 20
    assert metrics["length_repaired"] is True
    assert metrics["words_before_length_repair"] == 200
    assert metrics["words"] == 100

    lines = await script_service.get_script(db, project["id"])
    assert sum(len(line["text"].split()) for line in lines) == 100


async def test_pipeline_length_only_repair_still_over_length_is_accepted_off_target(db):
    """Verification item 2: the length-only repair itself still misses (stays
    over-length) -- the section is accepted via 14.3's accept-and-carry rather
    than hard-failing the job; this is a best-effort extra attempt, not a new
    gate."""
    project = await _project(db, duration_minutes=8.0)  # target_words = 800
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first part here", "target_words": 300},
                {"index": 2, "objective": "cover the second part here", "target_words": 350},
            ],
        }
    )
    # Section 1 (not last, effective target 300): short attempt -> semantic repair
    # -> repair output (500) is over 300*1.35=405 -> length-only pass -> its
    # output (450) STILL misses 300's ±15% band ([255, 345]) -- accepted anyway.
    s1_attempt = _section_json((alex_id, 50, 0))
    s1_repair = _section_json((alex_id, 250, 1000), (maya_id, 250, 1500))
    s1_length_repair = _section_json((alex_id, 225, 2000), (maya_id, 225, 2500))  # kept -- 450 words
    # Section 2 (last, nominal 350): true remaining need is 800-450=350, clamped
    # target lands exactly at 350 -- no repair needed.
    s2_attempt = _section_json((alex_id, 175, 3000), (maya_id, 175, 3500))  # 350 words

    router, gemini, _local = _build_router(
        [
            _result(outline_json),
            _result(s1_attempt), _result(s1_repair), _result(s1_length_repair),
            _result(s2_attempt),
        ]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    assert final_job["repair_count"] == 2  # section 1's semantic + length-only; section 2 needed neither
    assert gemini.call_count == 5

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    section1_checkpoint = next(c for c in checkpoints if c["section_index"] == 1)
    metrics = json.loads(section1_checkpoint["metrics_json"])
    assert metrics["length_repaired"] is True
    assert metrics["words_before_length_repair"] == 500
    assert metrics["words"] == 450  # still outside section 1's own ±15% band -- accepted anyway

    lines = await script_service.get_script(db, project["id"])
    assert sum(len(line["text"].split()) for line in lines) == 800  # 450 + 350, inside the global ±10% band


async def test_pipeline_structural_error_after_repair_never_triggers_length_only_pass(db):
    """Verification item 3: a structural error (consecutive-lines/unknown-speaker)
    survives the one semantic repair -> section_validation_failed, unchanged --
    the length-only pass never fires for a structural error even when the
    surviving output is also wildly over length."""
    project = await _project(db)
    ghost_id = "00000000-0000-0000-0000-000000000000"  # not one of this project's speakers

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    invalid_json = json.dumps([{"speaker_id": ghost_id, "text": _words(400, 0)}])  # structural AND over-length
    still_invalid_json = json.dumps([{"speaker_id": ghost_id, "text": _words(500, 1000)}])  # structural persists
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
    assert gemini.call_count == 3  # outline + attempt + one repair -- no third, length-only call
    lines = await script_service.get_script(db, project["id"])
    assert lines == []


async def test_pipeline_repair_count_hits_the_2n_plus_1_ceiling(db):
    """Verification item 5: the total repair-call bound per job is
    2 * num_sections + 1 (each section: one semantic + one length-only repair;
    plus the one final-section global-budget repair). Both sections here need
    both repairs, and the resulting total still misses the global ±10% band,
    so the final-section budget repair also fires -- hitting the ceiling
    exactly, asserted directly against the formula."""
    project = await _project(db, duration_minutes=8.0)  # target_words = 800
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first part here", "target_words": 300},
                {"index": 2, "objective": "cover the second part here", "target_words": 400},
            ],
        }
    )
    # Section 1 (not last, effective target 300): semantic + length-only repair,
    # final content still over-length (450) -- accepted off-target, carry -150.
    s1_attempt = _section_json((alex_id, 50, 0))
    s1_repair = _section_json((alex_id, 250, 1000), (maya_id, 250, 1500))
    s1_length_repair = _section_json((alex_id, 225, 2000), (maya_id, 225, 2500))  # 450 words
    # Section 2 (last, nominal 400, effective clamped to 350 given words_so_far=450):
    # semantic + length-only repair, final content (450) still over-length.
    s2_attempt = _section_json((maya_id, 50, 3000))
    s2_repair = _section_json((alex_id, 250, 4000), (maya_id, 250, 4500))
    s2_length_repair = _section_json((alex_id, 225, 5000), (maya_id, 225, 5500))  # 450 words
    # Merged total (450 + 450 = 900) misses the global ±10% band ([720, 880]) ->
    # the one final-section global-budget repair fires and lands inside it.
    s2_global_budget_repair = _section_json((alex_id, 190, 6000), (maya_id, 190, 6500))  # 380 words

    router, gemini, _local = _build_router(
        [
            _result(outline_json),
            _result(s1_attempt), _result(s1_repair), _result(s1_length_repair),
            _result(s2_attempt), _result(s2_repair), _result(s2_length_repair),
            _result(s2_global_budget_repair),
        ]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    num_sections = 2
    assert final_job["repair_count"] == 2 * num_sections + 1
    assert gemini.call_count == 8

    lines = await script_service.get_script(db, project["id"])
    total_words = sum(len(line["text"].split()) for line in lines)
    assert 720 <= total_words <= 880  # 450 + 380 = 830
