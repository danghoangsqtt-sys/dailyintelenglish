# Phase 15 Specification — Local Script Robustness (Structural Failures)

The controlling implementation contract is
`docs/implementation/phase-15-local-robustness.md`. Predecessors: the Phase 13 plan
(still controlling where not amended), the Phase 14 plan
(`docs/implementation/phase-14-ai-gateway-resilience.md`), and ADR-001 (+A1, A2).

## Goal

Give the two remaining structural checks — unknown speaker id and more than five
consecutive lines from one speaker — the same bounded, deterministic repair path every
content check already has (word budget, length, repetition, learning grounding), since
both are mechanical failure modes a 9B local model hits for reasons unrelated to
content (echoing a 36-character UUID per line; counting turns), not reasons a semantic
repair can fix. Triggered by the owner's own first real run dying on exactly this class
of failure.

## Required gates

- **Doc-first:** this spec, `PHASE-STATE.md`, and the task cards for 15.1–15.4 (15.5
  description-only, optional) exist and are pushed before any product code changes.
- **Invariant 20/21 gate:** no line is ever published with a speaker id that does not
  belong to the project, and no structural fix ever changes or reorders a line's words.
  Both are directly tested, not just asserted in prose.
- **Invariant 22 gate:** `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5`, both word
  tolerances, and `SCRIPT_MAX_REPEATED_8GRAM_RATIO` stay pinned and unchanged for the
  whole phase — this phase adds resolution/repair paths around the existing checks, it
  does not relax any of them.
- **Resume-compatibility gate:** a checkpoint written before Task 15.1 (raw `speaker_id`
  UUID shape) still resumes correctly after 15.1 ships.
- **Real-example gate:** the owner's own failing case
  (`ff5f20e0-417b-8d9f-752e844d46f0` → the real id `ff5f20e0-4082-417b-8d9f-752e844d46f0`,
  Alex) is a literal test case, not a paraphrase of it.
- **Gate B-6:** the protocol of Gate B-5 plus the owner's own failing configuration (A2,
  small_talk, 10 minutes, 2 speakers) as a fifth sample. Pace calibration is not
  re-done in this phase; the media gate is reported as declared.

## Definition of Done

Use §4 of the controlling plan (order, stop conditions, rollback) without relaxation.
Deviations require updating the plan (PM), the affected task card, and
`PHASE-STATE.md` before implementation continues.

## Session partition

PM owns `docs/**`, `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`,
`.viepilot/HANDOFF.json`. Coder owns `app/**`, `tests/**`, `scripts/**`, `prompts/**`,
and this folder after the handover commit. Only the PM runs
`scripts/run_ai_operational_trial.py`. Same partition as Phase 14 §10.
