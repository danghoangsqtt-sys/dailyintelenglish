"""Tests for the checkpointed script pipeline (Task 13.4)."""

import itertools
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
from app.services.script_service import LanguageNotesOut


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
    """Build a `SectionLineWire[]` JSON body from `(speaker_id, word_count,
    start_offset)` tuples -- one line per tuple. `start_offset` keeps every
    line's tokens globally unique across a test (see `_words`). Task 15.1: the
    wire key is `"speaker"`, not `"speaker_id"` -- passing each test's real
    speaker UUID as the value still resolves correctly (an exact UUID match is
    one of `resolve_speaker`'s own rules), so no test call site needs to
    change, only this helper's JSON shape."""
    return json.dumps(
        [{"speaker": speaker_id, "text": _words(count, start)} for speaker_id, count, start in speaker_words_start]
    )


def make_config(duration_minutes: float = 0.8, topic: str = "healthy morning habits") -> ScriptConfig:
    # Task 14.10 (D13): the default was 1.0 (-> 100 target_words under the old B1
    # 100wpm). Changed to 0.8 so 125wpm (new B1) * 0.8 = 100 exactly -- every existing
    # fixture in this file that hardcodes "100 words" / 4x25-word lines for the
    # default single-section case stays valid unchanged, matching the same
    # round-number-preservation approach already used for the "800" fixtures below.
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
        # Task 14.10 (D13): measured pace, not the old unmeasured 90/100/130 wpm --
        # A2 111wpm*5=555, B1 125wpm*8=1000, C1 145wpm*10=1450.
        ("a2_5min_daily_routine", 555),
        ("b1_8min_remote_work", 1000),
        ("c1_10min_urban_policy", 1450),
    ],
)
def test_compute_target_words_matches_golden_fixtures(fixture_id, expected_words):
    projects = _load_golden_projects()
    project = projects[fixture_id]
    assert script_pipeline.compute_target_words(project["cefr_level"], project["duration_minutes"]) == expected_words


def test_plan_sections_sums_to_target_words():
    # Task 14.10 (D13): updated to the measured table's values -- sum(budgets) == target
    # holds for any level/target pair by construction (only section *count* depends on
    # wpm), but these are kept in sync with the real table anyway so no stale pre-14.10
    # numbers sit next to it elsewhere in this file.
    for target, level in [(555, "A2"), (1000, "B1"), (1450, "C1"), (1, "A1")]:
        budgets = script_pipeline.plan_sections(target, level)
        assert sum(budgets) == target
        assert all(budget > 0 for budget in budgets)


def test_plan_sections_splits_into_roughly_90_second_chunks():
    # Task 14.10 (D13): B1 125 wpm * 1.5 min = 187.5 -> round() = 188 words/section;
    # 1000 words / 188 -> round(5.32) = 5 sections, splitting evenly into 5x200.
    budgets = script_pipeline.plan_sections(1000, "B1")
    assert budgets == [200, 200, 200, 200, 200]


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


# --- Task 15.1: speaker alias resolution ----------------------------------------------

SPEAKERS_2 = [
    {"id": "ff5f20e0-4082-417b-8d9f-752e844d46f0", "name": "Alex"},
    {"id": "11111111-2222-3333-4444-555555555555", "name": "Maya"},
]


def test_resolve_speaker_exact_alias():
    assert script_pipeline.resolve_speaker("S1", SPEAKERS_2) == (SPEAKERS_2[0]["id"], "alias_exact")
    assert script_pipeline.resolve_speaker("S2", SPEAKERS_2) == (SPEAKERS_2[1]["id"], "alias_exact")


def test_resolve_speaker_alias_case_and_whitespace_insensitive():
    assert script_pipeline.resolve_speaker(" s1 ", SPEAKERS_2) == (SPEAKERS_2[0]["id"], "alias_normalized")
    assert script_pipeline.resolve_speaker("S2", SPEAKERS_2) == (SPEAKERS_2[1]["id"], "alias_exact")


def test_resolve_speaker_display_name_when_unique():
    assert script_pipeline.resolve_speaker("alex", SPEAKERS_2) == (SPEAKERS_2[0]["id"], "display_name")
    assert script_pipeline.resolve_speaker(" Maya ", SPEAKERS_2) == (SPEAKERS_2[1]["id"], "display_name")


def test_resolve_speaker_display_name_skipped_when_not_unique():
    """PM review note: two speakers sharing a name means the display-name rule
    contributes nothing for either -- never a guess between them."""
    duplicate_name_speakers = [
        {"id": "aaaaaaaa-0000-0000-0000-000000000001", "name": "Sam"},
        {"id": "bbbbbbbb-0000-0000-0000-000000000002", "name": "Sam"},
    ]
    resolved, kind = script_pipeline.resolve_speaker("sam", duplicate_name_speakers)
    assert kind is None
    assert resolved == "sam"


def test_resolve_speaker_exact_uuid():
    assert script_pipeline.resolve_speaker(SPEAKERS_2[1]["id"], SPEAKERS_2) == (SPEAKERS_2[1]["id"], "uuid_exact")


def test_resolve_speaker_real_trigger_case_via_safety_net():
    """The exact real-world failure this phase opened on: the model dropped one
    UUID group (`ff5f20e0-417b-8d9f-752e844d46f0`) from the real id
    (`ff5f20e0-4082-417b-8d9f-752e844d46f0`, Alex) -- must resolve via the
    difflib safety net, not fail."""
    resolved, kind = script_pipeline.resolve_speaker("ff5f20e0-417b-8d9f-752e844d46f0", SPEAKERS_2)
    assert resolved == "ff5f20e0-4082-417b-8d9f-752e844d46f0"
    assert kind == "uuid_near_miss"


def test_resolve_speaker_safety_net_never_applies_to_a_non_uuid_shaped_value():
    """PM review note: the 0.85 safety net is gated to UUID-*shaped* values
    only (hex digits and dashes) -- an arbitrary string is never scored against
    known ids, however textually similar it might coincidentally be."""
    resolved, kind = script_pipeline.resolve_speaker("not at all uuid shaped", SPEAKERS_2)
    assert kind is None
    assert resolved == "not at all uuid shaped"


def test_resolve_speaker_uuid_shaped_but_no_match_above_threshold_is_unknown():
    resolved, kind = script_pipeline.resolve_speaker("00000000-0000-0000-0000-000000000000", SPEAKERS_2)
    assert kind is None
    assert resolved == "00000000-0000-0000-0000-000000000000"


def test_resolve_speaker_equidistant_between_two_ids_is_unknown():
    """PM review note: two-or-more ids tying at/above the threshold means
    unknown, never an arbitrary pick between them."""
    tied_speakers = [
        {"id": "aaaaaaaa-1111-2222-3333-444444444445", "name": "One"},
        {"id": "aaaaaaaa-1111-2222-3333-444444444446", "name": "Two"},
    ]
    equidistant_value = "aaaaaaaa-1111-2222-3333-4444444444XY"
    resolved, kind = script_pipeline.resolve_speaker(equidistant_value, tied_speakers)
    assert kind is None
    assert resolved == equidistant_value


def test_resolve_section_lines_logs_only_actual_resolutions(caplog):
    import logging

    wire_lines = [
        script_pipeline.SectionLineWire(speaker="S1", text=_words(5, 0)),
        script_pipeline.SectionLineWire(speaker="nonsense-unresolvable-value", text=_words(5, 100)),
    ]
    with caplog.at_level(logging.INFO, logger="app.services.script_pipeline"):
        resolved = script_pipeline.resolve_section_lines(wire_lines, SPEAKERS_2)

    assert resolved[0].speaker_id == SPEAKERS_2[0]["id"]
    assert resolved[1].speaker_id == "nonsense-unresolvable-value"  # unresolved, passed through unchanged
    resolved_logs = [r for r in caplog.records if "script_speaker_resolved" in r.message]
    assert len(resolved_logs) == 1  # only the actual resolution, not the pass-through
    assert "kind=alias_exact" in resolved_logs[0].message


async def test_pipeline_model_returning_aliases_completes(db):
    """Verification item 2: the model returns the actual alias contract
    (`"speaker": "S1"`/`"S2"`), not a UUID -- the normal, expected case going
    forward -- and the job completes."""
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
    )
    section_json = json.dumps(
        [
            {"speaker": "S1", "text": _words(25, 0)},
            {"speaker": "S2", "text": _words(25, 25)},
            {"speaker": "S1", "text": _words(25, 50)},
            {"speaker": "S2", "text": _words(25, 75)},
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
    assert final_job["status"] == "complete", final_job.get("error_message")

    lines = await script_service.get_script(db, project["id"])
    assert {line["speaker_id"] for line in lines} == {alex_id, maya_id}
    assert gemini.call_count == 2  # outline + section -- no repair needed


async def test_pipeline_model_returning_a_near_miss_uuid_resolves_and_completes(db, caplog):
    """Verification item 3: the model echoes a garbled/truncated UUID (the real
    trigger case) instead of the alias -- resolved via the safety net, the job
    completes, and the resolution is logged."""
    import logging

    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
    )
    # alex_id with its 5th character dropped -- the exact real-world defect shape.
    garbled_alex_id = alex_id[:4] + alex_id[5:]
    section_json = json.dumps(
        [
            {"speaker": garbled_alex_id, "text": _words(25, 0)},
            {"speaker": "S2", "text": _words(25, 25)},
            {"speaker": garbled_alex_id, "text": _words(25, 50)},
            {"speaker": "S2", "text": _words(25, 75)},
        ]
    )
    router, gemini, _local = _build_router([_result(outline_json), _result(section_json)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    with caplog.at_level(logging.INFO, logger="app.services.script_pipeline"):
        await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")

    lines = await script_service.get_script(db, project["id"])
    assert {line["speaker_id"] for line in lines} == {alex_id, maya_id}
    assert any(
        "script_speaker_resolved" in r.message and "kind=uuid_near_miss" in r.message for r in caplog.records
    )


async def test_pipeline_unresolvable_speaker_still_fails_after_repair(db):
    """Verification item 4: a genuinely unresolvable speaker value (not an
    alias, not a name, not UUID-shaped enough to trigger the safety net) still
    fails exactly as today -- the alias contract adds a resolution path, it
    never widens what counts as a known speaker."""
    project = await _project(db)

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
    )
    invalid_json = json.dumps([{"speaker": "the narrator", "text": _words(100, 0)}])
    still_invalid_json = json.dumps([{"speaker": "the narrator", "text": _words(100, 200)}])
    router, gemini, _local = _build_router([_result(outline_json), _result(invalid_json), _result(still_invalid_json)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == "section_validation_failed"
    assert "unknown speaker_id" in final_job["error_message"]
    assert await script_service.get_script(db, project["id"]) == []


# --- Task 15.2: deterministic consecutive-lines merge fix -----------------------------


def _line(speaker_id: str, text: str, **language_notes) -> script_pipeline.SectionLineOut:
    return script_pipeline.SectionLineOut(
        speaker_id=speaker_id, text=text, language_notes=LanguageNotesOut(**language_notes)
    )


def test_merge_consecutive_lines_returns_none_when_the_whole_section_is_one_speaker():
    lines = [_line("a", f"line{i}") for i in range(7)]
    assert script_pipeline.merge_consecutive_lines(lines, limit=5) is None


def test_merge_consecutive_lines_leaves_an_in_limit_run_untouched():
    lines = [_line("a", "one"), _line("a", "two"), _line("b", "three")]
    merged = script_pipeline.merge_consecutive_lines(lines, limit=5)
    assert merged == lines


def test_merge_consecutive_lines_brings_a_run_of_seven_within_the_limit():
    run = [_line("a", f"w{i}") for i in range(7)]
    lines = run + [_line("b", "closing")]
    merged = script_pipeline.merge_consecutive_lines(lines, limit=5)
    # Run of 7 into 5 groups (divmod distribution): sizes [2, 2, 1, 1, 1].
    assert [line.speaker_id for line in merged[:-1]] == ["a"] * 5
    assert merged[-1] == lines[-1]  # the closing "b" line is untouched
    consecutive = max(len(list(group)) for _, group in itertools.groupby(line.speaker_id for line in merged))
    assert consecutive <= 5


def test_merge_consecutive_lines_preserves_every_word_in_order():
    run = [_line("a", f"w{i} w{i}b") for i in range(7)]
    lines = run + [_line("b", "closing words here")]
    merged = script_pipeline.merge_consecutive_lines(lines, limit=5)
    original_words = " ".join(line.text for line in lines).split()
    merged_words = " ".join(line.text for line in merged).split()
    assert merged_words == original_words  # nothing added, removed, or reordered


def test_merge_consecutive_lines_never_re_attributes_a_line():
    run = [_line("a", f"w{i}") for i in range(7)]
    lines = run + [_line("b", "closing")]
    merged = script_pipeline.merge_consecutive_lines(lines, limit=5)
    assert {line.speaker_id for line in merged} == {"a", "b"}
    assert merged[-1].speaker_id == "b"  # the one "b" line is still attributed to "b"


def test_merge_consecutive_lines_handles_two_separate_over_limit_runs():
    lines = (
        [_line("a", f"a{i}") for i in range(6)]
        + [_line("b", "bridge")]
        + [_line("a", f"a2-{i}") for i in range(6)]
    )
    merged = script_pipeline.merge_consecutive_lines(lines, limit=5)
    run_lengths = [len(list(group)) for _, group in itertools.groupby(line.speaker_id for line in merged)]
    assert all(length <= 5 for length in run_lengths)
    assert " ".join(line.text for line in merged).split() == " ".join(line.text for line in lines).split()


def test_merge_group_unions_collocations_and_idioms_deduplicated():
    group = [
        _line("a", "one", collocations=["make a decision"], idioms=["hit the ground running"]),
        _line("a", "two", collocations=["make a decision", "take a break"], idioms=[]),
    ]
    merged = script_pipeline._merge_group(group)
    assert merged.text == "one two"
    assert merged.language_notes.collocations == ["make a decision", "take a break"]
    assert merged.language_notes.idioms == ["hit the ground running"]


def test_merge_group_grammar_point_keeps_the_first_lines_value():
    group = [
        _line("a", "one", grammar_point="Present Simple"),
        _line("a", "two", grammar_point="Past Simple"),
    ]
    merged = script_pipeline._merge_group(group)
    assert merged.language_notes.grammar_point == "Present Simple"


def test_merge_group_single_line_returned_unchanged():
    line = _line("a", "solo", grammar_point="X")
    assert script_pipeline._merge_group([line]) is line


async def test_pipeline_merges_a_run_of_seven_and_completes(db):
    """Verification: a run of 7 consecutive lines from one speaker survives
    the one semantic repair -- merged down to within the limit, job
    completes."""
    project = await _project(db)  # duration_minutes=0.8 -> target_words=100 (Task 14.10)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
    )
    attempt_json = _section_json((alex_id, 1, 0))  # way too short -> triggers the one repair
    # 7 consecutive alex lines (run > 5) + 1 maya line -- both speakers present,
    # so merge_consecutive_lines can actually help (not the unfixable case).
    # Word counts (49/51) keep the global speaker-balance check inside 35-65%.
    repair_json = _section_json(
        *[(alex_id, 7, 1000 + i * 20) for i in range(7)],
        (maya_id, 51, 2000),
    )
    router, gemini, _local = _build_router([_result(outline_json), _result(attempt_json), _result(repair_json)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    assert gemini.call_count == 3  # outline + attempt + the one repair (merge itself costs no extra AI call)

    lines = await script_service.get_script(db, project["id"])
    run_lengths = [len(list(group)) for _, group in itertools.groupby(line["speaker_id"] for line in lines)]
    assert all(length <= 5 for length in run_lengths)
    assert sum(len(line["text"].split()) for line in lines) == 100  # merge never changes total word count

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    section_checkpoint = next(c for c in checkpoints if c["section_index"] == 1)
    metrics = json.loads(section_checkpoint["metrics_json"])
    assert metrics["structural_fix"] == "merged_consecutive_lines"
    assert metrics["lines_before_fix"] == 8
    assert metrics["lines_after_fix"] == 6  # run of 7 -> 5 groups ([2,2,1,1,1]) + the 1 maya line


async def test_pipeline_whole_section_one_speaker_still_fails(db):
    """Verification: the merge fix's own unfixable case -- the repaired
    section is entirely one speaker (the plan's own example) -- still fails
    exactly as today, with no extra AI call attempted."""
    project = await _project(db)
    alex_id, _maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
    )
    attempt_json = _section_json((alex_id, 1, 0))
    still_invalid_json = _section_json(*[(alex_id, 14, 1000 + i * 20) for i in range(7)])  # all alex, no maya

    router, gemini, _local = _build_router([_result(outline_json), _result(attempt_json), _result(still_invalid_json)])

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "error"
    assert final_job["error_code"] == "section_validation_failed"
    assert gemini.call_count == 3  # outline + attempt + the one repair -- no merge attempt possible
    assert await script_service.get_script(db, project["id"]) == []


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


# --- Task 14.13: repetition-repair pure functions ------------------------------------


def _section_lines(*texts: str) -> list:
    return [script_pipeline.SectionLineOut(speaker_id="a", text=text) for text in texts]


def test_find_repeated_8grams_by_section_attributes_repeat_to_its_own_section():
    repeated = "a b c d e f g h"
    sections = [
        (1, _section_lines(repeated, _words(20, 100))),
        (2, _section_lines(repeated, _words(20, 200))),
    ]
    grams, per_section = script_pipeline.find_repeated_8grams_by_section(sections)
    assert grams == [tuple(repeated.split())]
    assert per_section == {1: 1, 2: 1}


def test_find_repeated_8grams_by_section_attributes_cross_boundary_repeat_to_start_section():
    """A repeated 8-word window whose first word is in section 1 but whose last
    words spill into section 2 is attributed to section 1 -- the section it
    *starts* in, matching the card's worst-section selection rule."""
    repeated = "a b c d e f g h"
    sections = [
        (1, _section_lines(f"{_words(20, 100)} a b c d")),  # ends mid-phrase
        (2, _section_lines(f"e f g h {_words(20, 200)}")),  # completes it
        (3, _section_lines(repeated)),  # a second, separate occurrence
    ]
    grams, per_section = script_pipeline.find_repeated_8grams_by_section(sections)
    assert grams == [tuple(repeated.split())]
    assert per_section == {1: 1, 3: 1}
    assert 2 not in per_section


def test_find_repeated_8grams_by_section_picks_the_worst_by_occurrence_count():
    repeated = "a b c d e f g h"
    sections = [
        (1, _section_lines(repeated, _words(20, 100))),  # 1 occurrence
        (2, _section_lines(repeated, repeated, _words(20, 200))),  # 2 occurrences
    ]
    _grams, per_section = script_pipeline.find_repeated_8grams_by_section(sections)
    worst_index = max(per_section, key=per_section.get)
    assert worst_index == 2
    assert per_section[2] > per_section[1]


def test_find_repeated_8grams_by_section_empty_for_no_repeats():
    sections = [(1, _section_lines(_words(20, 0))), (2, _section_lines(_words(20, 100)))]
    grams, per_section = script_pipeline.find_repeated_8grams_by_section(sections)
    assert grams == []
    assert per_section == {}


def test_find_repeated_8grams_by_section_empty_for_fewer_than_8_words():
    sections = [(1, _section_lines("only three words"))]
    grams, per_section = script_pipeline.find_repeated_8grams_by_section(sections)
    assert grams == []
    assert per_section == {}


def test_frequent_repeated_phrases_ranks_by_frequency_and_respects_limit():
    words = (
        ("common phrase used many times over " * 3).split()
        + ("less common phrase seen just twice " * 2).split()
        + _words(30, 900).split()
    )
    phrases = script_pipeline.frequent_repeated_phrases([w.casefold() for w in words], limit=1)
    assert phrases == ["common phrase used many times over common phrase"]


def test_frequent_repeated_phrases_empty_for_no_repeats():
    assert script_pipeline.frequent_repeated_phrases(_words(20).split()) == []


def test_validate_global_topic_relevance_is_a_warning_not_a_hard_error():
    lines = [script_pipeline.SectionLineOut(speaker_id="a", text=_words(100, 0))]
    hard_errors, warnings = script_pipeline.validate_global(
        lines, 100, {"a"}, 1, "a very specific unrelated keyword"
    )
    assert hard_errors == []
    assert any("topic keyword" in warning for warning in warnings)


def test_constants_pin_word_tolerances_are_unchanged_by_task_14_3():
    """Task 14.3/14.8/14.13/15.1 governance note: SCRIPT_GLOBAL_WORD_TOLERANCE,
    SCRIPT_SECTION_WORD_TOLERANCE, SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER,
    SCRIPT_MAX_REPEATED_8GRAM_RATIO, and SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO are a
    stop condition, not an implementation choice -- this pins all five values so
    a silent edit fails CI."""
    from app.core import constants

    assert constants.SCRIPT_GLOBAL_WORD_TOLERANCE == 0.10
    assert constants.SCRIPT_SECTION_WORD_TOLERANCE == 0.15
    assert constants.SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER == 5
    assert constants.SCRIPT_MAX_REPEATED_8GRAM_RATIO == 0.01
    assert constants.SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO == 0.85


def test_constants_pin_pace_calibration_table_matches_the_d13_measurement():
    """Task 14.10 (Amendment G, D13): CEFR_WORDS_PER_MINUTE and
    CEFR_DEFAULT_TTS_SPEED are measured values (real Edge TTS synthesis at 5
    speeds, data/quality_reviews/phase14/gate-b3/pace-calibration.json), not an
    implementation choice -- pins both tables so a silent edit fails CI."""
    from app.core import constants

    assert constants.CEFR_WORDS_PER_MINUTE == {
        "A1": 111, "A2": 111, "B1": 125, "B2": 132, "C1": 145, "C2": 159,
    }
    assert constants.CEFR_DEFAULT_TTS_SPEED == {
        "A1": 0.75, "A2": 0.75, "B1": 0.85, "B2": 0.90, "C1": 1.00, "C2": 1.10,
    }


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
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
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
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
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


async def test_pipeline_section_prompt_always_includes_the_static_anti_repetition_rules(db):
    """Task 16.4 (ENH-009 step A): 3 fixed rules against the framing patterns Gate
    B-6's evidence showed (agreement-opener, thesis/takeaway restatement,
    within-section self-repeat) must be present in every section prompt,
    unconditionally -- both when the existing dynamic `avoid_phrases` block is
    empty (section 1, no prior sections yet) and when it's populated (section 2,
    once section 1 has produced a phrase that's already repeated). N6 (PM
    review): the rules must describe the observed patterns abstractly, never
    quote the actual forbidden phrase -- a quoted example risks *priming* reuse
    on a small local model. Asserts the literal quoted phrase never appears."""
    # duration_minutes=1.6 -> compute_target_words(B1, 1.6) = 200, matching this
    # test's 2-section outline (100 words each) -- the pipeline computes its own
    # overall episode target from duration, independent of the fake outline's
    # per-section target_words fields, so the two must agree or the second
    # section's word-budget check fails and triggers an unscripted repair call.
    project = await _project(db, duration_minutes=1.6)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the full topic here", "target_words": 100},
                {"index": 2, "objective": "continue the discussion here", "target_words": 100},
            ],
        }
    )
    # Section 1: an 8-word phrase (word0..word7) appears in two different Alex
    # lines -- sharing an 8-word run without being byte-identical lines (an
    # exact duplicate line is a separate, stricter hard error) -- deliberately,
    # so frequent_repeated_phrases() has something to surface to section 2's
    # prompt. 28 + 22 + 28 + 22 = 100 words, matching the section's own target;
    # Alex's 56/100 here plus 50/100 in section 2 keeps the whole-episode
    # speaker balance (106/200 = 53%) inside the required 35-65% share.
    section1_json = json.dumps(
        [
            {"speaker": alex_id, "text": f"{_words(20, 900)} {_words(8, 0)}"},
            {"speaker": maya_id, "text": _words(22, 50)},
            {"speaker": alex_id, "text": f"{_words(8, 0)} {_words(20, 950)}"},
            {"speaker": maya_id, "text": _words(22, 150)},
        ]
    )
    section2_json = _section_json(
        (alex_id, 25, 500), (maya_id, 25, 525), (alex_id, 25, 550), (maya_id, 25, 575)
    )
    # The deliberate repeat above also trips the whole-episode repeated-8-gram
    # ratio check (2 occurrences / ~193 windows ~= 1.04%, just over the 1%
    # threshold) -- expected, and exactly what triggers the existing one-time
    # repetition repair (Task 14.13) on section 1 (the only section the repeat
    # is attributed to). Scripts a clean, non-repeating replacement for it.
    repaired_section1_json = _section_json(
        (alex_id, 25, 700), (maya_id, 25, 725), (alex_id, 25, 750), (maya_id, 25, 775)
    )
    router, gemini, _local = _build_router(
        [_result(outline_json), _result(section1_json), _result(section2_json), _result(repaired_section1_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete"

    section1_prompt = gemini.calls[1].prompt
    section2_prompt = gemini.calls[2].prompt

    static_rule_fragments = [
        "Never open more than one turn in the whole episode with the same stock "
        "agreement phrase",
        "Never repeat the same summary or takeaway sentence, word-for-word or "
        "nearly so, in more than one section.",
        "Do not restate the same sentence or claim twice within this section itself",
    ]
    for fragment in static_rule_fragments:
        assert fragment in section1_prompt, "static rules must be present with no prior sections"
        assert fragment in section2_prompt, "static rules must still be present once avoid_phrases is populated"

    # Section 2 actually got the dynamic (existing, unchanged) avoid-phrases block too.
    assert "word0 word1 word2 word3 word4 word5 word6 word7" in section2_prompt

    # N6: the observed forbidden phrase is never quoted verbatim -- a quoted
    # example risks priming a small local model to reuse it.
    assert "I truly believe" not in section1_prompt
    assert "I truly believe" not in section2_prompt


async def test_pipeline_repair_prompt_also_avoids_quoting_a_repetition_example(db):
    """Task 16.4, N6: the repair prompt's new anti-repetition line must be
    present and, like the section prompt's, must never quote a concrete
    example phrase."""
    project = await _project(db)
    alex_id = project["speakers"][0]["id"]

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    invalid_section_json = json.dumps([{"speaker": alex_id, "text": _words(5, 0)}])  # way too short
    repaired_section_json = _section_json(
        (alex_id, 25, 0), (project["speakers"][1]["id"], 25, 25),
        (alex_id, 25, 50), (project["speakers"][1]["id"], 25, 75),
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

    repair_prompt = gemini.calls[2].prompt
    assert "avoid reusing the same stock agreement phrase or the same summary/" in repair_prompt
    assert "I truly believe" not in repair_prompt


async def test_pipeline_repairs_an_invalid_section_once_then_completes(db):
    project = await _project(db)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the full topic here", "target_words": 100}]}
    )
    invalid_section_json = json.dumps([{"speaker": alex_id, "text": _words(5, 0)}])  # way too short
    repaired_section_json = json.dumps(
        [
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
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
    invalid_json = json.dumps([{"speaker": ghost_id, "text": _words(100, 0)}])
    still_invalid_json = json.dumps([{"speaker": ghost_id, "text": _words(100, 100)}])
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
    project = await _project(db, duration_minutes=1.6)  # 1.6 * 125 wpm (B1) = 200 (Task 14.10)
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
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
        ]
    )
    section2_json = json.dumps(
        [
            {"speaker": alex_id, "text": _words(25, 100)},
            {"speaker": maya_id, "text": _words(25, 125)},
            {"speaker": alex_id, "text": _words(25, 150)},
            {"speaker": maya_id, "text": _words(25, 175)},
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
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
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
    invalid_section_json = json.dumps([{"speaker": alex_id, "text": _words(5, 0)}])  # way too short
    repaired_section_json = json.dumps(
        [
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
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
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
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
            {"speaker": alex_id, "text": _words(25, 0)},
            {"speaker": maya_id, "text": _words(25, 25)},
            {"speaker": alex_id, "text": _words(25, 50)},
            {"speaker": maya_id, "text": _words(25, 75)},
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
    # Task 14.10 (D13): 6.4 min * 125 wpm (B1) = 800 target_words -- preserves this
    # test's existing carry/clamp/repair arithmetic unchanged.
    project = await _project(db, duration_minutes=6.4)
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
            "structural_fix", "lines_before_fix", "lines_after_fix",
        }
        assert metrics["length_repaired"] is False  # 130 never exceeds any clamped ceiling here
        assert metrics["structural_fix"] is None  # no consecutive-lines violation here
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
    # Task 14.10 (D13): 6.4 min * 125 wpm (B1) = 800 -- preserves this test's
    # existing carry/clamp/repair arithmetic unchanged; never actually about "8
    # minutes", only about the round number 800.
    project = await _project(db, duration_minutes=6.4)  # target_words = 800
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
    # Task 14.10 (D13): 6.4 min * 125 wpm (B1) = 800 -- preserves this test's
    # existing carry/clamp/repair arithmetic unchanged; never actually about "8
    # minutes", only about the round number 800.
    project = await _project(db, duration_minutes=6.4)  # target_words = 800
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
    # Task 14.10 (D13): 6.4 min * 125 wpm (B1) = 800 target_words, matching this
    # test's own hand-computed carry math (see comments in _scenario_outcomes above).
    uninterrupted_project = await _project(db, duration_minutes=6.4)
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
    resumed_project = await _project(db, duration_minutes=6.4)  # 6.4 * 125 wpm (B1) = 800
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
    project = await _project(db)  # duration_minutes=0.8 -> target_words=100 (Task 14.10), 1 section
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
    # Task 14.10 (D13): 6.4 min * 125 wpm (B1) = 800 -- preserves this test's
    # existing carry/clamp/repair arithmetic unchanged; never actually about "8
    # minutes", only about the round number 800.
    project = await _project(db, duration_minutes=6.4)  # target_words = 800
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
    invalid_json = json.dumps([{"speaker": ghost_id, "text": _words(400, 0)}])  # structural AND over-length
    still_invalid_json = json.dumps([{"speaker": ghost_id, "text": _words(500, 1000)}])  # structural persists
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
    # Task 14.10 (D13): 6.4 min * 125 wpm (B1) = 800 -- preserves this test's
    # existing carry/clamp/repair arithmetic unchanged; never actually about "8
    # minutes", only about the round number 800.
    project = await _project(db, duration_minutes=6.4)  # target_words = 800
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


# --- Task 14.13: repetition repair (D17) ----------------------------------------------


def _lines_json(*speaker_texts: tuple[str, str]) -> str:
    """Build a `SectionLineWire[]` JSON body from `(speaker_id, literal text)`
    pairs -- unlike `_section_json`, this lets a test control the exact words
    (e.g. to deliberately plant a repeated 8-gram). Task 15.1: the wire key is
    `"speaker"` -- see `_section_json`'s docstring for why passing a real UUID
    still resolves correctly unchanged."""
    return json.dumps([{"speaker": speaker_id, "text": text} for speaker_id, text in speaker_texts])


REPEATED_PHRASE = "the weather today is quite nice actually indeed"  # exactly 8 words


async def test_pipeline_repetition_only_failure_repairs_the_worst_section_and_completes(db):
    """Verification item 2: a repetition-only global failure -- word count,
    balance, and duplicates all pass, only the repeated-8-gram check fails --
    gets one repair of the section attributed as the worst offender, then
    completes."""
    project = await _project(db, duration_minutes=1.6)  # 1.6 * 125 wpm (B1) = 200
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first part here", "target_words": 100},
                {"index": 2, "objective": "cover the second part here", "target_words": 100},
            ],
        }
    )
    # Section 1: the repeated phrase appears once (100 words total, passes its
    # own ±15% budget check individually -- no per-section repair triggered).
    section1_json = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(42, 0)}"),
        (maya_id, _words(50, 100)),
    )
    # Section 2 (last): the SAME phrase appears twice -- the worst offender
    # (2 occurrences starting here vs. section 1's 1).
    section2_json = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(17, 300)}"),
        (maya_id, f"{REPEATED_PHRASE} {_words(17, 400)}"),
        (alex_id, _words(25, 500)),
        (maya_id, _words(25, 600)),
    )
    # The repetition repair's fixed replacement for section 2 -- no repeated
    # phrase, still 100 words, still passes its own ±15% budget.
    section2_fixed_json = _lines_json(
        (alex_id, _words(50, 700)),
        (maya_id, _words(50, 800)),
    )

    router, gemini, _local = _build_router(
        [_result(outline_json), _result(section1_json), _result(section2_json), _result(section2_fixed_json)]
    )

    job, _ = await ai_job_service.create_job(
        db, project["id"], "script", {"project": project, "operation": "script"}
    )
    claimed = await ai_job_service.claim_job(db, job["id"], "worker-1")
    worker = AIWorker(db_getter=lambda: db)

    await script_pipeline.make_handler(router)(claimed, worker)

    final_job = await ai_job_service.get_job(db, job["id"], project["id"])
    assert final_job["status"] == "complete", final_job.get("error_message")
    assert final_job["repair_count"] == 1  # exactly the one repetition repair
    assert gemini.call_count == 4  # outline + 2 sections (no per-section repair) + 1 repetition repair

    calls = json.loads(final_job["metrics_json"])["calls"]
    assert calls[-1]["purpose"] == "script_section_repetition_repair"

    lines = await script_service.get_script(db, project["id"])
    total_words = sum(len(line["text"].split()) for line in lines)
    assert total_words == 200
    assert REPEATED_PHRASE not in " ".join(line["text"] for line in lines).replace(REPEATED_PHRASE, "", 1)

    checkpoints = await ai_job_service.get_valid_checkpoints(db, job["id"])
    section2_checkpoint = next(c for c in checkpoints if c["section_index"] == 2)
    assert json.loads(section2_checkpoint["metrics_json"])["repetition_repaired"] is True
    section1_checkpoint = next(c for c in checkpoints if c["section_index"] == 1)
    assert "repetition_repaired" not in json.loads(section1_checkpoint["metrics_json"])


async def test_pipeline_repetition_repair_still_failing_hard_fails(db):
    """Verification item 3: the repetition repair itself still fails the
    check -- global_validation_failed, unchanged."""
    project = await _project(db, duration_minutes=1.6)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first part here", "target_words": 100},
                {"index": 2, "objective": "cover the second part here", "target_words": 100},
            ],
        }
    )
    section1_json = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(42, 0)}"),
        (maya_id, _words(50, 100)),
    )
    section2_json = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(17, 300)}"),
        (maya_id, f"{REPEATED_PHRASE} {_words(17, 400)}"),
        (alex_id, _words(25, 500)),
        (maya_id, _words(25, 600)),
    )
    # The repair's own output STILL reuses the phrase -- still fails.
    section2_still_repeating_json = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(42, 700)}"),
        (maya_id, _words(50, 800)),
    )

    router, gemini, _local = _build_router(
        [
            _result(outline_json), _result(section1_json), _result(section2_json),
            _result(section2_still_repeating_json),
        ]
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
    assert "repeated 8-gram ratio" in final_job["error_message"]
    assert gemini.call_count == 4  # no second repetition-repair attempt
    assert await script_service.get_script(db, project["id"]) == []


async def test_pipeline_mixed_global_failure_never_triggers_repetition_repair(db):
    """Verification item 4: a global failure that is *not* repetition-only
    (paired with a word-count miss) never triggers the repetition-repair
    path -- falls straight through to the existing, unchanged final-section
    budget-repair machinery (Task 14.3 item 6).

    Single default section (target_words=100): its own per-section tolerance
    is wider (+-15%, [85, 115]) than the global tolerance (+-10%, [90, 110]),
    so 88 words passes the section's own budget check (no semantic/length-only
    repair fires) while still failing the *global* check -- the gap between
    the two tolerances, not multi-section carry math, is what makes both
    failures coexist without any per-section repair muddying the call count."""
    project = await _project(db)  # duration_minutes=0.8 -> target_words=100 (Task 14.10)
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {"title": "T", "sections": [{"index": 1, "objective": "cover the topic fully here", "target_words": 100}]}
    )
    # 88 words, repeated phrase twice -- passes its own +-15% band, fails the
    # global +-10% band, and fails the repetition check. No per-section repair.
    section_json = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(36, 0)}"),
        (maya_id, f"{REPEATED_PHRASE} {_words(36, 100)}"),
    )
    # The existing final-section budget repair's own output -- still short,
    # still repeats the phrase, so the post-repair hard_errors stay mixed.
    budget_repair_json = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(36, 300)}"),
        (maya_id, f"{REPEATED_PHRASE} {_words(36, 400)}"),
    )

    router, gemini, _local = _build_router(
        [_result(outline_json), _result(section_json), _result(budget_repair_json)]
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
    assert "total word count" in final_job["error_message"]
    assert "repeated 8-gram ratio" in final_job["error_message"]
    # Exactly the 3 scripted calls consumed (outline + attempt + the existing
    # final-section budget repair) -- no repetition-repair 4th call attempted
    # (would have raised "no more scripted outcomes" otherwise).
    assert gemini.call_count == 3


async def test_pipeline_repair_count_hits_the_2n_plus_2_ceiling(db):
    """Verification item 5: the total repair-call bound per job is
    2 * num_sections + 2 (Task 14.8's 2n+1 -- two per-section repairs plus the
    one final-section global-budget repair -- plus one more for this task's
    repetition repair). Both sections need both per-section repairs; the
    resulting total misses the global ±10% band, so the final-section budget
    repair fires; its own output brings the word count back in range but
    plants a repeated phrase, so the repetition repair fires last -- hitting
    the ceiling exactly, asserted directly against the formula."""
    project = await _project(db, duration_minutes=1.6)  # target_words = 200
    alex_id, maya_id = (speaker["id"] for speaker in project["speakers"])

    outline_json = json.dumps(
        {
            "title": "T",
            "sections": [
                {"index": 1, "objective": "cover the first part here", "target_words": 75},
                {"index": 2, "objective": "cover the second part here", "target_words": 125},
            ],
        }
    )
    # Section 1 (not last, effective target 75): semantic + length-only
    # repair, final content still over-length (100) -- accepted off-target.
    # Plants the repeated phrase once.
    s1_attempt = _section_json((alex_id, 10, 0))
    s1_semantic_repair = _section_json((alex_id, 60, 1000), (maya_id, 60, 1500))
    s1_length_repair = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(42, 2000)}"),
        (maya_id, _words(50, 2500)),
    )  # 100 words, kept
    # Section 2 (last, nominal 125, effective clamped to 100 given
    # words_so_far=100): semantic + length-only repair, final content (130)
    # still over-length.
    s2_attempt = _section_json((maya_id, 10, 3000))
    s2_semantic_repair = _section_json((alex_id, 75, 4000), (maya_id, 75, 4500))
    s2_length_repair = _section_json((alex_id, 65, 5000), (maya_id, 65, 5500))
    # Merged total (100 + 130 = 230) misses the global ±10% band ([180, 220])
    # -> the one final-section global-budget repair fires, landing the total
    # back at 200 -- but plants the repeated phrase twice more (3 total).
    s2_budget_repair = _lines_json(
        (alex_id, f"{REPEATED_PHRASE} {_words(9, 6000)}"),
        (maya_id, f"{REPEATED_PHRASE} {_words(9, 6500)}"),
        (alex_id, _words(33, 6100)),
        (maya_id, _words(33, 6600)),
    )  # 100 words
    # Global re-check is now repetition-only (word count/balance/duplicates
    # all pass) -> the one repetition repair fires on section 2 (2 of the 3
    # occurrences start there, vs. section 1's 1) and removes the phrase.
    s2_repetition_repair = _section_json((alex_id, 50, 7000), (maya_id, 50, 7500))

    router, gemini, _local = _build_router(
        [
            _result(outline_json),
            _result(s1_attempt), _result(s1_semantic_repair), _result(s1_length_repair),
            _result(s2_attempt), _result(s2_semantic_repair), _result(s2_length_repair),
            _result(s2_budget_repair), _result(s2_repetition_repair),
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
    assert final_job["repair_count"] == 2 * num_sections + 2
    assert gemini.call_count == 9

    lines = await script_service.get_script(db, project["id"])
    total_words = sum(len(line["text"].split()) for line in lines)
    assert total_words == 200
    joined = " ".join(line["text"] for line in lines)
    assert joined.count(REPEATED_PHRASE) == 1  # section 1's occurrence survives; section 2's is gone
