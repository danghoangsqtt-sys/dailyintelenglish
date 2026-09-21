# Task 14.8 — Local Hardening: Over-Length Sections and the Consecutive-Lines Rule

- **Status:** in progress
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
  1. **Constant:** add `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS = 1` to
     `app/core/constants.py`, right after `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS`,
     with a Task 14.8 comment. `0` disables the new pass (the card's own rollback).
  2. **`prompts/script/section.txt`:**
     - "Target length: about `{{ target_words }}` spoken words (stay within ±15%)"
       becomes a hard, pre-computed range: "between `{{ (target_words*0.85)|round|int }}`
       and `{{ (target_words*1.15)|round|int }}` spoken words -- count your words
       before answering." Computed with plain Jinja arithmetic on the existing
       `target_words` variable -- no new template variable, matching the card's "no
       change to how the value gets there" instruction. The ±15% literal already
       existed in this same line's prose before this task; not a tolerance-constant
       edit (that stays in Python, untouched).
     - Multi-speaker turn-taking rule gains "alternate speakers by default" alongside
       the existing `{{ max_consecutive_lines }}` number.
  3. **`prompts/script/repair.txt`:** `_repair_section` will compute and pass
     `measured_words` (word count of the previous answer) and `delta` (signed,
     `measured_words - target_words`); the template shows both and, for `delta > 0`,
     instructs the model to remove/shorten specific existing lines rather than
     rewrite from scratch (the card's explicit over-length instruction); for
     `delta < 0`, the symmetric add/expand instruction (prompt-only, does not change
     any gating logic -- under-length misses still resolve via 14.3's unchanged
     accept-and-carry).
  4. **Consecutive-lines error message** (`validate_section_structure`): changes from
     the generic "more than 5 consecutive lines from one speaker" to naming the
     offending speaker id and approximate 1-based line range, e.g. "more than 5
     consecutive lines from speaker <id> (lines 3-9)" -- flows into `repair.txt`'s
     existing `errors` loop with no template change needed there. Still contains the
     substring `"consecutive lines"`, so the existing substring-matching unit tests
     (`test_validate_section_rejects_too_many_consecutive_lines` et al.) are
     unaffected.
  5. **`_repair_section` signature:** gains `purpose: str = "script_section_repair"`
     (default preserves every existing caller's telemetry string unchanged), passed
     through to `GenerationRequest.purpose` -- the new length-only call passes
     `purpose="script_section_length_repair"` so telemetry can tell the two kinds of
     repair apart.
  6. **Pipeline trigger** (`_run_script_job`'s main per-section loop, right after the
     existing "if structural_errors: fail" check): if `repaired` is `True` (the one
     semantic repair already fired) AND `budget_errors` is still non-empty AND
     `words > effective_target * (1 + SCRIPT_SECTION_CARRY_CAP)` AND
     `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS > 0`, fire exactly one more `_repair_section`
     call (`errors=budget_errors`, `purpose="script_section_length_repair"`). A
     `ProviderError` fails the job the same way as the first repair; a structural
     error in its output hard-fails with `section_validation_failed` (defensive, same
     treatment as the first repair, even though the length-only prompt never asks for
     structural changes). Otherwise `words` is recomputed and the existing
     accept-and-carry / checkpoint-save flow continues unchanged. The
     `SCRIPT_SECTION_CARRY_CAP` threshold (not `SCRIPT_SECTION_WORD_TOLERANCE`) is the
     over-length gate deliberately -- it's already the clamp band's own ceiling, so
     "still over after repair, by more than the clamp itself allows for" is the
     narrowest correct trigger, matching Gate B-2's evidence (417/214, 426/173,
     404/208 -- all far past +35%, not just +15%). Under-length sections can never
     satisfy `words > effective_target * 1.35`, so 14.3's accept-and-carry for them is
     provably untouched by this new branch. The last section is eligible the same as
     any other section (the card does not exclude it); the separate, pre-existing
     final-section global-budget-repair block later in the function is untouched
     apart from inheriting `repair.txt`'s new measured/target/delta lines for free
     (same `_repair_section` function, no call-site logic change there).
  7. **Checkpoint `metrics_json` shape** (verification item 1's "document the exact
     shape chosen"): two new keys alongside the existing seven --
     `length_repaired: bool` and `words_before_length_repair: int | None` -- mirroring
     the existing `repaired`/`words_before_repair` pair. Additive and backward
     compatible; both default `False`/`None` when the new pass never fires.
  8. **Test-file follow-on edits required by this shape change (not a deviation, an
     expected consequence):**
     `test_pipeline_accepts_off_target_sections_when_total_lands_inside_tolerance`'s
     exact-set assertion (`set(metrics) == {...}`) must gain the two new keys or it
     will fail on an unrelated diff -- that fixture's own deviations (130 vs an
     effective ceiling of at most 216) never cross the new CARRY_CAP trigger, so only
     the key-set list changes, not any asserted value.
  9. New FakeProvider e2e tests for verification items 1/2/3/5 (four new tests,
     named `test_pipeline_length_only_repair_*`), plus the constants-pin extension
     (item 4) and its revert-and-confirm-failure.
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
