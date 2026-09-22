# Phase 15 Implementation Plan — Local Script Robustness (structural failures)

**Status:** Controlling plan, PM/Tester, 2026-09-22; opened under the owner's delegated
decision authority (`/vp-auto` 2026-09-22) after a real-use failure
**Predecessors:** Phase 13 plan (still controlling where not amended), Phase 14 plan
(`docs/implementation/phase-14-ai-gateway-resilience.md`), ADR-001 (+A1, A2)
**Trigger:** the owner's first hands-on run after Phase 14 — an A2 / small_talk /
10-minute / 2-speaker project died at section 3 with
`section_validation_failed: unknown speaker_id(s): ['ff5f20e0-417b-8d9f-752e844d46f0']`.
The project's real speaker is `ff5f20e0-4082-417b-8d9f-752e844d46f0` (Alex): the model
**dropped one UUID group**. Sections 1–2 had completed (with repairs); three minutes of
generation were lost to a copy error the server could have resolved deterministically.
The same class killed the B1 5-min sample in Gate B-4 (`unknown speaker_id`, truncated
UUID) and the B1 10-min sample in Gate B-3 (consecutive-lines rule).

## 1. Why this phase exists

Every content check now has a bounded repair path (word budget, length, repetition,
learning grounding) **except the two structural checks**: unknown speaker id and more
than five consecutive lines from one speaker. Both are fatal after the one semantic
repair. Both are also the checks a 9B model fails for *mechanical* reasons (echoing a
36-character UUID per line; counting turns), not for content reasons — and both can be
resolved on the server without inventing content.

## 2. Invariants (in addition to Phase 13 §2 and Phase 14 §2)

20. **No invented speaker, ever.** A line is published only with a speaker id that
    belongs to the project. Server-side mapping may *resolve* an alias or a near-miss to a
    real speaker; it may never *choose* a speaker the model did not indicate.
21. **No content invented by the server.** Structural fixes reorder or re-attribute
    nothing that changes the words; a line's text is never edited by a deterministic fix.
22. **Thresholds unchanged.** `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5`, both word
    tolerances, and the 8-gram ratio stay pinned.
23. Session partition and doc-first as in Phase 14 §10.

## 3. Tasks

### 15.1 — Speaker aliases in the section contract (P0, Coder)

**Allowed files:** `app/services/script_pipeline.py`, `app/core/constants.py`,
`prompts/script/section.txt`, `prompts/script/repair.txt`, `tests/test_script_pipeline.py`,
`tests/fixtures/ai/*`.

**Design:**
1. The section and repair prompts present speakers as short aliases — `S1`, `S2`, … in
   `speaker_index` order — alongside the display name; the JSON contract asks for
   `"speaker": "S1"` (alias), **not** the UUID. `SectionLineOut` gains `speaker: str`
   (alias) and the pipeline resolves alias → UUID server-side before validation; the
   persisted line shape (`speaker_id` UUID) is unchanged, so `script_service.save_script`,
   the API and the UI see no difference.
2. **Resolution rules, deterministic and logged** (`script_speaker_resolved kind=…`):
   exact alias (`S1`); alias case/whitespace-insensitive; the speaker's display name when
   names are unique within the project; a full UUID that matches exactly; and — safety net
   for older checkpoints or a model that still echoes ids — a UUID-shaped value that
   matches exactly one known id with ≥ 0.85 similarity (`difflib.SequenceMatcher` ratio;
   constant `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO = 0.85`). Anything else stays an unknown
   speaker → repair → `section_validation_failed`, exactly as today.
3. Resume compatibility: checkpoints written before this task hold `speaker_id` UUIDs;
   the loader accepts both shapes.
4. Legacy single-line `regenerate_line` (`script_service`) is **out of scope** — it
   still echoes ids; note it, do not touch it.

**Verification:** pure tests for every resolution rule including the real Gate B-4 and
owner-run examples (`ff5f20e0-417b-8d9f-752e844d46f0` → Alex; a value equidistant from two
ids → unknown); e2e: model returns aliases → complete; model returns a truncated UUID →
resolved, job completes, resolution logged; unresolvable → fails as today; old-shape
checkpoint resumes; constants pin extended; revert-and-confirm-failure on the safety
net; full suite; `ruff`.

### 15.2 — Deterministic consecutive-lines fix (P1, Coder)

**Allowed files:** `app/services/script_pipeline.py`, `app/core/constants.py`,
`prompts/script/repair.txt`, `tests/test_script_pipeline.py`, `tests/fixtures/ai/*`.

**Design:** after the one semantic repair, if the *only* remaining structural error is a
run of more than `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER` lines by one speaker in a
two-speaker section, apply one bounded server-side fix: **merge** the run's consecutive
lines from the same speaker into fewer lines (joining text with a space; words unchanged,
order unchanged) until the run length is ≤ the limit — never re-attribute a line to the
other speaker (that would invent dialogue). If merging cannot bring the run within the
limit (e.g. the whole section is one speaker) → fail as today. Bounded by
`SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 1` per section; recorded in the checkpoint
`metrics_json` (`structural_fix: "merged_consecutive_lines"`, lines before/after).

**Verification:** pure merge tests (word count invariant, order invariant, limit
satisfied); e2e: run-of-7 → merged → complete; single-speaker section → still fails;
constants pin; revert-and-confirm-failure; full suite; `ruff`.

### 15.3 — Trial runner per-gate evidence path + `_record_dropped_items` layering (P2, Coder)

**Allowed files:** `scripts/run_ai_operational_trial.py`, `app/services/ai_job_service.py`,
`app/services/learning_pipeline.py`, `tests/test_ai_job_service.py`,
`tests/test_learning_pipeline.py`.

**Actions:** `--gate <name>` selects `data/quality_reviews/phase15/<name>/` for evidence
and trial data (default keeps today's path); `ai_job_service.set_job_metric(db, job_id,
key, value)` replaces the pipeline-local SQL in `learning_pipeline._record_dropped_items`
(behaviour unchanged, tests moved).

### 15.4 — Gate B-6, local only (PM)

Protocol of Gate B-5 plus **the owner's own failing configuration** (A2, small_talk,
10 minutes, 2 speakers) as a fifth sample. Pass rule unchanged. **Pace calibration is
not re-done in this phase**; the media gate is reported as declared.

### 15.5 — Multi-script pace calibration (P2, PM measurement → Coder constants) — optional

Only if the owner wants the media gate to pass: measure real pace on the five Gate B-5
scripts per level (mean and spread), set `CEFR_WORDS_PER_MINUTE` to the mean, and declare
the media gate on the completed run closest to the target. Deferred until 15.1–15.4 land.

## 4. Order, stop conditions, rollback

15.1 → 15.2 → 15.3 (Coder, doc-first cards reviewed by the PM) → 15.4 (PM) → close-out;
15.5 only on the owner's word. Stop conditions: Phase 14 §8 plus "a structural fix would
change or re-attribute any line's text". Rollback: `SCRIPT_SPEAKER_ID_MATCH_MIN_RATIO =
1.0` and `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 0` restore Phase 14 behaviour; the alias
contract is reverted by git only.
