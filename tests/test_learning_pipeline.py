"""Tests for the grounded learning-content pipeline (Task 13.5)."""

import json

import pytest

from app.core.exceptions import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.models.learning import LearningPackOut
from app.models.project import ScriptConfig, SpeakerConfig
from app.services import ai_job_service, learning_pipeline, learning_service, project_service, script_service
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

TRANSCRIPT = (
    "Alex: I have been working remotely from home for five years now. "
    "Maya: That is great, you really hit the ground running when the pandemic started."
)


def _pack(**overrides) -> LearningPackOut:
    base = {
        "vocabulary": [
            {
                "word": "remotely",
                "part_of_speech": "adverb",
                "ipa": "/r/",
                "definition_en": "from a distance",
                "definition_vi": "tu xa",
                "example_sentence": "I have been working remotely from home for five years now.",
            }
        ],
        "idioms": [
            {
                "phrase": "hit the ground running",
                "meaning_en": "start fast and effectively",
                "meaning_vi": "bat dau nhanh chong va hieu qua",
                "example_sentence": "you really hit the ground running when the pandemic started.",
            }
        ],
        "grammar": [
            {
                "point": "Present Perfect Continuous",
                "structure": "have/has + been + verb-ing",
                "explanation_en": "for an action continuing up to now",
                "explanation_vi": "hanh dong tiep dien den hien tai",
                "examples": ["I have been working remotely from home for five years now."],
            }
        ],
        "questions": [
            {"question": "Q1?", "options": ["A", "B"], "correct_answer": "A", "explanation": "e"},
            {"question": "Q2?", "options": ["A", "B"], "correct_answer": "B", "explanation": "e"},
            {"question": "Q3 (open-ended)?", "options": [], "correct_answer": "", "explanation": "e"},
        ],
    }
    base.update(overrides)
    return LearningPackOut.model_validate(base)


def _result(pack: LearningPackOut) -> GenerationResult:
    return GenerationResult(
        text=pack.model_dump_json(), provider="fake-gemini", model="fake-model",
        latency_ms=1.0, attempt=1, prompt_hash="abc123",
    )


def _build_router(gemini_outcomes: list) -> tuple[AIRouter, FakeProvider, FakeProvider]:
    gemini = FakeProvider("gemini", gemini_outcomes)
    local = FakeProvider("ollama", [])
    return AIRouter(local=local, gemini=gemini, mode=AIMode.GEMINI), gemini, local


def make_config() -> ScriptConfig:
    return ScriptConfig(
        name="Learning pipeline test",
        topic="remote work",
        cefr_level="B1",
        duration_minutes=2.0,
        num_speakers=2,
        genre="interview",
        accent="american",
        speakers=[
            SpeakerConfig(name="Alex", gender="male", accent="american"),
            SpeakerConfig(name="Maya", gender="female", accent="american"),
        ],
    )


async def _project_with_script(db) -> dict:
    project = await project_service.create_project(db, make_config())
    speaker_ids = [speaker["id"] for speaker in project["speakers"]]
    lines = [
        {"speaker_id": speaker_ids[0], "text": "I have been working remotely from home for five years now."},
        {"speaker_id": speaker_ids[1], "text": "That is great, you really hit the ground running when the pandemic started."},
    ]
    await script_service.save_script(db, project["id"], lines, set(speaker_ids))
    return await project_service.get_project(db, project["id"])


# --- pure validators: five deterministic fixture packs -------------------------------


def test_fixture_1_valid_pack_passes_all_checks():
    assert learning_pipeline.validate_pack(_pack(), TRANSCRIPT) == []


def test_fixture_2_ungrounded_example_sentence_fails():
    pack = _pack(vocabulary=[{**_pack().vocabulary[0].model_dump(), "example_sentence": "This sentence is invented."}])
    errors = learning_pipeline.validate_pack(pack, TRANSCRIPT)
    assert any("not found in transcript" in error for error in errors)


def test_fixture_3_duplicate_question_fails():
    q = _pack().questions[0].model_dump()
    pack = _pack(questions=[q, q, _pack().questions[2].model_dump()])
    errors = learning_pipeline.validate_pack(pack, TRANSCRIPT)
    assert any("duplicate question" in error for error in errors)


def test_fixture_4_mcq_answer_not_in_options_fails():
    pack = _pack(
        questions=[
            {"question": "Q1?", "options": ["A", "B"], "correct_answer": "C", "explanation": "e"},
            {"question": "Q2?", "options": ["A", "B"], "correct_answer": "B", "explanation": "e"},
            {"question": "Q3?", "options": [], "correct_answer": "", "explanation": "e"},
        ]
    )
    errors = learning_pipeline.validate_pack(pack, TRANSCRIPT)
    assert any("correct_answer not among its options" in error for error in errors)


def test_fixture_5_too_few_questions_fails_count_check():
    pack = _pack(questions=[{"question": "Only one?", "options": [], "correct_answer": "", "explanation": "e"}])
    errors = learning_pipeline.validate_pack(pack, TRANSCRIPT)
    assert any("questions has 1 item" in error for error in errors)


# --- pure validators: additional targeted cases ---------------------------------------


def test_validate_grounding_rejects_ungrounded_idiom_phrase():
    pack = _pack(idioms=[{**_pack().idioms[0].model_dump(), "phrase": "a completely made up idiom"}])
    errors = learning_pipeline.validate_grounding(pack, TRANSCRIPT)
    assert any("phrase not found in transcript" in error for error in errors)


def test_validate_counts_rejects_too_many_grammar_points():
    pack = _pack(grammar=[_pack().grammar[0].model_dump()] * 3)
    # 3 distinct grammar points needed to avoid tripping duplicate detection instead
    for i, item in enumerate(pack.grammar):
        item.point = f"Point {i}"
    errors = learning_pipeline.validate_counts(pack)
    assert any("grammar has 3 point" in error for error in errors)


def test_validate_duplicates_rejects_duplicate_vocabulary_word():
    entry = _pack().vocabulary[0].model_dump()
    pack = _pack(vocabulary=[entry, dict(entry)])
    errors = learning_pipeline.validate_duplicates(pack)
    assert any("duplicate vocabulary word" in error for error in errors)


def test_validate_answers_allows_open_ended_with_no_options():
    pack = _pack(questions=[{"question": "Discuss.", "options": [], "correct_answer": "", "explanation": "e"}] * 1
                 + [_pack().questions[0].model_dump(), _pack().questions[1].model_dump()])
    assert learning_pipeline.validate_answers(pack) == []


# --- handler: end-to-end with a FakeProvider-backed router --------------------------


async def test_pipeline_happy_path_completes_and_saves_pack(db):
    project = await _project_with_script(db)
    router, gemini, local = _build_router([_result(_pack())])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert local.call_count == 0

    saved = await learning_service.get_learning_content(db, project["id"])
    assert saved is not None
    assert len(saved["vocabulary"]) == 1


async def test_pipeline_repairs_an_invalid_pack_once_then_completes(db):
    project = await _project_with_script(db)
    invalid_pack = _pack(vocabulary=[{**_pack().vocabulary[0].model_dump(), "example_sentence": "Invented sentence."}])
    router, gemini, _local = _build_router([_result(invalid_pack), _result(_pack())])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert gemini.call_count == 2  # one invalid attempt + one repair
    saved = await learning_service.get_learning_content(db, project["id"])
    assert saved is not None


async def test_pipeline_fails_transparently_when_repair_also_fails(db):
    """Task 14.11 (D15): this fixture's surviving failure (the pack's only idiom,
    still ungrounded after the one repair) *is* removable on its own -- but the
    base pack has exactly one idiom and LEARNING_MIN_IDIOMS == 1, so dropping it
    would breach the minimum. Verification item 2: still hard-fails exactly as
    before, and the failure message now names what would have been dropped and
    why, proving the removal path was actually exercised (not silently skipped)."""
    project = await _project_with_script(db)
    invalid_pack = _pack(vocabulary=[{**_pack().vocabulary[0].model_dump(), "example_sentence": "Invented."}])
    still_invalid_pack = _pack(idioms=[{**_pack().idioms[0].model_dump(), "phrase": "still made up"}])
    router, gemini, _local = _build_router([_result(invalid_pack), _result(still_invalid_pack)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == "pack_validation_failed"
    assert "dropped idiom 'still made up'" in final_job["error_message"]
    assert "idioms has 0 item" in final_job["error_message"]
    # prior state (none, for a fresh project) is provably unchanged.
    assert await learning_service.get_learning_content(db, project["id"]) is None


# --- Task 14.11: learning repair by removal (D15) ------------------------------------


async def test_pipeline_drops_a_still_ungrounded_idiom_after_repair_and_completes(db):
    """Verification item 1: a still-ungrounded idiom survives the one repair, but
    the pack has a second, genuinely grounded idiom -- dropping just the bad one
    still meets LEARNING_MIN_IDIOMS, so the job completes rather than failing."""
    project = await _project_with_script(db)
    invalid_pack = _pack(vocabulary=[{**_pack().vocabulary[0].model_dump(), "example_sentence": "Invented."}])
    repaired_pack = _pack(
        idioms=[
            _pack().idioms[0].model_dump(),  # "hit the ground running" -- grounded
            {
                "phrase": "a bolt from the blue",
                "meaning_en": "something totally unexpected",
                "meaning_vi": "chuyen bat ngo",
                "example_sentence": "It was a bolt from the blue.",
            },  # never appears in TRANSCRIPT -- survives the repair ungrounded
        ]
    )
    router, gemini, _local = _build_router([_result(invalid_pack), _result(repaired_pack)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    assert gemini.call_count == 2  # one invalid attempt + one repair, no third call

    saved = await learning_service.get_learning_content(db, project["id"])
    assert [item["phrase"] for item in saved["idioms"]] == ["hit the ground running"]

    dropped = json.loads(final_job["metrics_json"])["dropped_items"]
    assert dropped == [
        {
            "kind": "idiom",
            "key": "a bolt from the blue",
            "reason": "phrase or example_sentence not found in transcript",
        }
    ]


async def test_pipeline_drops_a_still_inconsistent_answer_after_repair_and_completes(db):
    """Verification item 3: an MCQ whose correct_answer isn't among its own
    options survives the one repair; the pack has 4 questions, so dropping the
    bad one still meets LEARNING_MIN_QUESTIONS (3)."""
    project = await _project_with_script(db)
    invalid_pack = _pack(vocabulary=[{**_pack().vocabulary[0].model_dump(), "example_sentence": "Invented."}])
    repaired_pack = _pack(
        questions=[
            {"question": "Q1?", "options": ["A", "B"], "correct_answer": "A", "explanation": "e"},
            {"question": "Q2?", "options": ["A", "B"], "correct_answer": "B", "explanation": "e"},
            {"question": "Q3?", "options": ["A", "B"], "correct_answer": "C", "explanation": "e"},  # C not an option
            {"question": "Q4 (open-ended)?", "options": [], "correct_answer": "", "explanation": "e"},
        ]
    )
    router, gemini, _local = _build_router([_result(invalid_pack), _result(repaired_pack)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")

    saved = await learning_service.get_learning_content(db, project["id"])
    assert [item["question"] for item in saved["questions"]] == ["Q1?", "Q2?", "Q4 (open-ended)?"]

    dropped = json.loads(final_job["metrics_json"])["dropped_items"]
    assert dropped == [{"kind": "question", "key": "Q3?", "reason": "correct_answer not among its options"}]


async def test_pipeline_fails_when_script_is_empty(db):
    project = await project_service.create_project(db, make_config())  # no script saved
    router, gemini, _local = _build_router([])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == "script_empty"
    assert gemini.call_count == 0


async def test_pipeline_cancels_when_already_requested_before_processing(db):
    project = await _project_with_script(db)
    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    await ai_job_service.claim_job(db, job["id"], "worker-1")
    await ai_job_service.request_cancel(db, job["id"], project["id"])
    fresh_claimed = await ai_job_service.get_job(db, job["id"], project["id"])

    router, gemini, _local = _build_router([])
    worker = AIWorker(db_getter=lambda: db)
    await learning_pipeline.make_handler(router)(fresh_claimed, worker)

    result = await ai_job_service.get_job(db, job["id"], project["id"])
    assert result["status"] == "cancelled"
    assert gemini.call_count == 0


async def test_pipeline_marks_stale_when_project_changed_since_job_creation(db):
    project = await _project_with_script(db)
    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")

    from app.models.project import ProjectUpdate

    await project_service.update_project(db, project["id"], ProjectUpdate(topic="A totally different topic now"))

    router, gemini, _local = _build_router([])
    worker = AIWorker(db_getter=lambda: db)
    await learning_pipeline.make_handler(router)(claimed, worker)

    result = await ai_job_service.get_job(db, job["id"], project["id"])
    assert result["status"] == "stale"
    assert gemini.call_count == 0


async def test_pipeline_marks_stale_when_script_changed_during_generation(db, monkeypatch):
    """The pipeline's own start-vs-final-save script-hash check (see
    task-13.5.md's 'real gap' note) catches a script edit landing mid-flight,
    since ai_generation_jobs.script_hash_at_start is never populated yet."""
    project = await _project_with_script(db)
    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")

    real_get_script = script_service.get_script
    call_count = {"n": 0}

    async def get_script_then_mutate(db_arg, project_id):
        call_count["n"] += 1
        lines = await real_get_script(db_arg, project_id)
        if call_count["n"] == 1:
            # Simulate a concurrent script edit landing right after the pipeline's
            # first read, before its final-save re-check.
            speaker_ids = [s["id"] for s in project["speakers"]]
            await script_service.save_script(
                db_arg, project_id,
                [{"speaker_id": speaker_ids[0], "text": "This script was edited during generation."}],
                set(speaker_ids),
            )
        return lines

    monkeypatch.setattr(learning_pipeline.script_service, "get_script", get_script_then_mutate)

    router, gemini, _local = _build_router([_result(_pack())])
    worker = AIWorker(db_getter=lambda: db)
    await learning_pipeline.make_handler(router)(claimed, worker)

    result = await ai_job_service.get_job(db, job["id"], project["id"])
    assert result["status"] == "stale"
    assert await learning_service.get_learning_content(db, project["id"]) is None


# --- Task 14.2: job telemetry -----------------------------------------------------------


async def test_pipeline_happy_path_records_zero_repairs_and_one_ok_call(db):
    project = await _project_with_script(db)
    router, gemini, _local = _build_router([_result(_pack())])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert final_job["repair_count"] == 0
    calls = json.loads(final_job["metrics_json"])["calls"]
    assert len(calls) == 1
    assert calls[0]["purpose"] == "learning_pack"
    assert calls[0]["outcome"] == "ok"
    assert calls[0]["is_repair"] is False
    assert calls[0]["section_index"] is None


async def test_pipeline_repair_sets_repair_count(db):
    project = await _project_with_script(db)
    invalid_pack = _pack(vocabulary=[{**_pack().vocabulary[0].model_dump(), "example_sentence": "Invented sentence."}])
    router, gemini, _local = _build_router([_result(invalid_pack), _result(_pack())])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert final_job["repair_count"] == 1
    calls = json.loads(final_job["metrics_json"])["calls"]
    assert [call["purpose"] for call in calls] == ["learning_pack", "learning_pack_repair"]
    assert calls[1]["is_repair"] is True


async def test_pipeline_hybrid_fallback_records_fallback_telemetry(db, monkeypatch):
    monkeypatch.setattr("app.services.ai.router.sleep", _no_op_sleep)
    project = await _project_with_script(db)

    local = FakeProvider("ollama", [ProviderUnavailableError("down")] * 4)
    gemini = FakeProvider("gemini", [_result(_pack())])
    router = AIRouter(local=local, gemini=gemini, mode=AIMode.HYBRID, failure_threshold=1, cooldown_seconds=60.0)

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"
    assert final_job["fallback_used"] == 1
    assert final_job["fallback_count"] >= 1
    assert final_job["actual_provider"] == "fake-gemini"  # this file's `_result()` helper's hardcoded value


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
    project = await _project_with_script(db)
    router, gemini, _local = _build_router(list(outcomes))

    job, _ = await ai_job_service.create_job(
        db, project["id"], "learning", {"project": project, "operation": "learning"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await learning_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == expected_error_code
    assert final_job["error_code"] != "handler_exception"
    calls = json.loads(final_job["metrics_json"])["calls"]
    assert calls[-1]["outcome"] == "error"
    assert calls[-1]["purpose"] == "learning_pack"
    assert await learning_service.get_learning_content(db, project["id"]) is None
