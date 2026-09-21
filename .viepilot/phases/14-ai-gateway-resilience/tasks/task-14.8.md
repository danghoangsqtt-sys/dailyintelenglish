# Task 14.8 — Local Hardening: Over-Length Sections and the Consecutive-Lines Rule

- **Status:** pending
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** Task 14.7 done and accepted by the PM
- **Controlling detail:** plan §12 Task 14.8; Gate B-2 evidence
  (`docs/operations/phase14-gate-b2.md`)

## Governance note — read before anything else

**This is not a threshold relaxation, same as Task 14.3.** `SCRIPT_GLOBAL_WORD_TOLERANCE`
(0.10), `SCRIPT_SECTION_WORD_TOLERANCE` (0.15), and `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`
(5) all stay exactly as they are. This task adds one additional, narrowly-scoped repair
pass for over-length sections specifically — it does not touch what "in tolerance" means,
and it does not touch the semantic-repair budget ADR-001 A1 already caps at one. If you
find yourself wanting to widen a tolerance or the consecutive-lines limit to make a test
pass more easily, **stop and ask the PM** — that is a stop condition, identical in kind to
Task 14.3's.

## Objective

Reduce Gate B-2's dominant real local-matrix failure modes — sections landing far over
their effective word budget, and a run dying on the consecutive-lines structural check —
using the Gate B-2 evidence itself to target the fix, without touching either tolerance
constant or the semantic-repair budget.

## Measured problem (do not re-derive)

Gate B-2 local matrix (`docs/operations/phase14-gate-b2.md`): completed sections at 417
and 426 words against effective targets of 214 and 173 (426 was itself the result of a
340-word first draft that already missed, then grew further after repair); a third
section at 404 words against an effective target of 208; a 43-word closing section (badly
under-length, the opposite failure mode, already handled by 14.3's accept-and-carry).
Run 3 died with `section_validation_failed`: "more than 5 consecutive lines from one
speaker" — a **structural** error, survives repair by definition unchanged (14.3's
accept-and-carry never applies to structural errors). Repair success rate across the
matrix: 44% (8/18) — the one semantic repair pass frequently doesn't fix an over-length
miss at all, let alone bring it inside tolerance.

## Allowed files

`prompts/script/section.txt`, `prompts/script/repair.txt`,
`app/services/script_pipeline.py`, `app/core/constants.py`,
`tests/test_script_pipeline.py`, `tests/fixtures/ai/*`.

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. **Section prompt** (`prompts/script/section.txt`): state the word budget as a hard
   range ("between A and B words — count them") rather than only "about N words", and
   state the consecutive-lines rule with its actual number
   (`SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`); require alternating speakers by default
   (not just "avoid too many in a row"). The effective target already flows into this
   template via the existing `target_words` variable (Task 14.3) — no change to how the
   value gets there, only to the prose around it.
2. **Repair prompt** (`prompts/script/repair.txt`): pass the measured word count, the
   target, and the signed delta (over/under by how much). For an over-length miss,
   instruct the model to remove or shorten specific lines to reach the target rather than
   rewrite the whole section from scratch (rewriting is how a 340-word draft became a
   426-word "repair" in the Gate B-2 evidence — strictly worse). For a consecutive-lines
   error, name the offending run of lines explicitly (which speaker, roughly which lines)
   rather than restating the rule in the abstract.
3. **Pipeline** (`app/services/script_pipeline.py`): when a section is still over
   `effective_target × (1 + SCRIPT_SECTION_CARRY_CAP)` **after** the one existing
   semantic repair, allow **one additional, length-only repair pass** — a second call to
   the repair prompt, scoped to trimming length only, bounded by a new constant
   `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS = 1` (`app/core/constants.py`, Task 14.8 comment).
   This is a **second, narrower** pass with its own explicit budget — ADR-001 A1's "at
   most one semantic repair per section" is unchanged; the length-only pass is not a
   second semantic repair, it exists specifically because the evidence shows a single
   repair pass frequently fails to fix over-length misses. Under-length sections keep the
   existing 14.3 accept-and-carry behavior unchanged — this new pass triggers on
   over-length only.
4. `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER = 5` and both word tolerances stay
   byte-for-byte unchanged. The existing constants-pin test (Task 14.3) is extended to
   also assert `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER == 5`.

## Explicitly forbidden

- Editing `SCRIPT_GLOBAL_WORD_TOLERANCE`, `SCRIPT_SECTION_WORD_TOLERANCE`, or
  `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER`.
- A second *semantic* repair (content/grounding) — the new pass is length-only, trimming
  an already-valid-content section, never re-generating content.
- Removing or weakening the structural consecutive-lines check itself.
- Uncapping the length-only repair — it is exactly one extra attempt, same as the
  existing semantic repair, each with its own named budget.

## Verification (all must be in the diff)

1. FakeProvider e2e test: a section lands over `effective × (1 + SCRIPT_SECTION_CARRY_CAP)`
   after its one semantic repair → the length-only repair pass fires, trims it inside
   tolerance → section accepted, checkpoint `metrics_json` reflects two repair attempts
   for that section (or however the card's chosen `metrics_json` shape records the
   length-only pass — document the exact shape chosen).
2. FakeProvider e2e test: the length-only repair itself still misses (stays over-length)
   → accepted off-target via the existing 14.3 accept-and-carry (this pass does not turn
   an over-length miss into a hard failure — it is a best-effort extra attempt, not a new
   gate).
3. FakeProvider e2e test: a structural error (consecutive-lines) survives the one
   semantic repair → `section_validation_failed`, unchanged — the length-only repair pass
   never fires for a structural error (over-length is the only trigger).
4. Constants-pin test extended: `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER == 5`,
   alongside the existing two tolerance assertions. Revert-and-confirm-failure by
   temporarily editing the value; record the output.
5. The total repair-call bound per job is now ≤ `2 × num_sections + 1` (each section: one
   semantic repair + one length-only repair; plus the one final-section global-budget
   repair from Task 14.3) — assert this bound directly in at least one e2e test (e.g. by
   counting `FakeProvider.call_count` or the job's `repair_count` against the formula).
6. `venv\Scripts\python.exe -m ruff check app tests scripts` clean; full suite green
   (record the exact pass count, baseline is whatever Task 14.4a-c left it at).

## Rollback

`SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS = 0` disables the new pass without a code revert,
restoring Task 14.3's exact repair behavior.

## Execution record (Coder fills in)

- Plan/decisions before code:
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
