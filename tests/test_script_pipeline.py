"""Tests for the checkpointed script pipeline (Task 13.4)."""

import json
from pathlib import Path

import pytest

from app.models.project import ProjectUpdate, ScriptConfig, SpeakerConfig
from app.services import ai_job_service, project_service, script_pipeline, script_service
from app.services.ai.contracts import AIMode, GenerationResult
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.router import AIRouter
from app.services.ai_worker import AIWorker

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
