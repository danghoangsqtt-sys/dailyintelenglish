# Task 14.13 — Repetition Repair

- **Status:** pending
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** Task 14.4a-d done (sequential, per plan §14's execution order)
- **Controlling detail:** plan §14 "14.13 — Repetition repair"; Amendment H decision
  D17; `docs/operations/phase14-gate-b4.md`

## Objective

Gate B-4's script gate landed at 3/5, and both misses died on the same, single check:
the whole-episode repeated-8-gram ratio (1.02% and 4.32%, against the unchanged 1%
threshold) — not word count, which Task 14.10 already fixed. Give a repetition-only
global failure one targeted repair attempt before hard-failing the job, matching the
existing pattern already used for word-count-only global failures (Task 14.3 item 6).

## Measured problem (do not re-derive)

Gate B-4 (`docs/operations/phase14-gate-b4.md`): at the corrected 1,000-word B1 target,
3/5 script jobs completed (991/984/915 words, all passing content checks); the other 2
died on `global_validation_failed` with only the repeated-8-gram check failing (1.02%
and 4.32% against the unchanged 1% `SCRIPT_MAX_REPEATED_8GRAM_RATIO` threshold) — no job
died on word count. Repair success rate across the matrix: 65%. 0 infrastructure
failures.

## Allowed files

`app/services/script_pipeline.py`, `app/core/constants.py`, `prompts/script/section.txt`,
`prompts/script/repair.txt`, `tests/test_script_pipeline.py`, `tests/fixtures/ai/*`.

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. **New pure function(s)** in `script_pipeline.py`: given the merged, per-section lines
   (section boundaries preserved, not a flat list — `validate_global`'s existing flat-list
   signature is untouched, used only for the pass/fail check itself), find every repeated
   8-word window across the whole episode and, per section, how many repeated-window
   occurrences *start* in that section. This is the attribution needed to pick "the single
   worst section" to regenerate.
2. **Trigger**: after the existing final-section word-budget repair (Task 14.3 item 6,
   unchanged) has already run and re-validated, if `hard_errors` is still non-empty and
   **every** remaining error is the repeated-8-gram check specifically (not mixed with a
   word-count/balance/duplicate error), regenerate **only the single worst section**
   (by the per-section attribution above) through the existing `_repair_section`/repair
   prompt machinery, with the actual repeated phrases named in the errors passed to that
   prompt. Bounded by a new constant `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS = 1`
   (`app/core/constants.py`) — exactly one attempt, one section, per job. Overwrite that
   section's checkpoint with the new content, rebuild the merged script in outline order,
   and re-run `validate_global`. Still failing → `global_validation_failed`, unchanged.
   A global failure that is *not* repetition-only (e.g. still has a word-count or balance
   error alongside repetition) never triggers this new path — falls straight through to
   the existing hard-fail, exactly as today.
3. **Prompt changes**: `prompts/script/repair.txt` already supports naming errors
   verbatim (used unchanged) — the repetition-repair call's `errors` list names the
   actual repeated phrases, not just "repetition too high" in the abstract.
   `prompts/script/section.txt`'s continuity/prior-summary context gains a short list of
   the most-frequently-repeated 8-grams seen in the episode so far (not just the
   immediately-previous section's summary), so later sections are told what to avoid
   *before* generating, not only reactively repaired after the fact.
4. `SCRIPT_MAX_REPEATED_8GRAM_RATIO = 0.01` stays byte-for-byte unchanged — added to the
   existing constants-pin test alongside the tolerance/consecutive-lines values already
   pinned there.
5. The total repair-call bound per job becomes ≤ `2 × num_sections + 2` (was
   `2 × num_sections + 1` after Task 14.8: two per-section repairs + one final-section
   word-budget repair; +1 more for this task's one repetition repair) — asserted directly
   in at least one e2e test, mirroring Task 14.8's own bound test.

## Explicitly forbidden

- Editing `SCRIPT_MAX_REPEATED_8GRAM_RATIO`, `SCRIPT_GLOBAL_WORD_TOLERANCE`,
  `SCRIPT_SECTION_WORD_TOLERANCE`, `SCRIPT_SECTION_CARRY_CAP`,
  `SCRIPT_LAST_SECTION_CARRY_CAP`, `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS`, or
  `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS`.
- A second repetition-repair attempt, or regenerating more than one section for a single
  repetition failure.
- Triggering this path for a global failure that mixes repetition with any other hard
  error.

## Verification (all must be in the diff)

1. Pure-function unit tests for the repeated-8-gram-by-section finder (distinct grams
   found; correct per-section attribution; empty input; no repeats).
2. FakeProvider e2e test: a repetition-only global failure → the one repetition repair
   fires on the correctly-identified worst section → `validate_global` passes → job
   completes.
3. FakeProvider e2e test: the repetition repair itself still fails the check →
   `global_validation_failed`, unchanged.
4. FakeProvider e2e test: a global failure that is *not* repetition-only (e.g. paired
   with a word-count miss) never triggers the repetition-repair path.
5. Repair-count bound (`2 × num_sections + 2`) asserted directly in at least one e2e test.
6. Revert-and-confirm-failure on the `SCRIPT_MAX_REPEATED_8GRAM_RATIO` pin extension.
7. Full suite green; `ruff check app tests scripts` clean.

## Rollback

`SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS = 0` disables the new pass without a code
revert, restoring today's immediate-hard-fail behavior for a repetition-only miss.

## Execution record

- Plan/decisions before code:
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
