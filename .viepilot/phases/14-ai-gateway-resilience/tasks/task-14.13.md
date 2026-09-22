# Task 14.13 — Repetition Repair

- **Status:** done (full suite 902 passed, 0 failed)
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
  1. **New constants** (`app/core/constants.py`): `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS
     = 1` (this task's own bound, mirroring `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS`'s
     comment style); `SCRIPT_SECTION_AVOID_PHRASES_MAX = 8` (PM's note (b) -- caps
     the proactive continuity-note phrase list so the prompt never grows unbounded
     as sections accumulate).
  2. **`find_repeated_8grams_by_section(sections: list[tuple[int, list[SectionLineOut]]])
     -> tuple[list[tuple[str, ...]], dict[int, int]]`** (new pure function,
     `script_pipeline.py`): concatenates every section's words in order (tagging
     each word with its source `section_index`), finds every 8-gram that repeats
     across the *whole* concatenation (not per-section in isolation -- a repeat
     spanning a section boundary must still count), and attributes each repeated
     occurrence to whichever section its *first* word falls in (PM's note (a):
     "chọn section chứa nhiều điểm BẮT ĐẦU của cửa sổ lặp nhất" -- occurrences
     starting in that section, exactly as the card already said). Returns
     `(distinct repeated grams, {section_index: occurrence count starting there})`.
     The "worst section" is `max(per_section_counts, key=per_section_counts.get)`.
  3. **`frequent_repeated_phrases(words: list[str], limit=SCRIPT_SECTION_AVOID_PHRASES_MAX)
     -> list[str]`** (new pure function): the same repeated-8-gram-finding core,
     but returns joined phrase strings sorted by frequency, capped at `limit` --
     used only for the proactive continuity note (item 3), not the repair
     attribution (item 2's function), since these two callers need different
     shapes (per-section counts vs. a flat ranked list) and are cheap enough not
     to share one function's return contract.
  4. **Proactive continuity note** (`_generate_section`/`section.txt`): the main
     loop computes `avoid_phrases = frequent_repeated_phrases(normalize_text(word)
     for word in all words accumulated in `all_lines` so far)` immediately before
     each `_generate_section` call (so it reflects everything generated up to that
     point, not a stale snapshot) and passes it through as a new parameter.
     `section.txt` gains an `{% if avoid_phrases %}` block (placed after the
     existing `is_last_section` block, before `## Speakers`) listing them.
  5. **Repair orchestration** (`_run_script_job`, inserted between the existing
     final-section word-budget re-check and the final `if hard_errors: fail`,
     lines ~854-858 today): if `hard_errors` is non-empty and **every** entry
     starts with `"repeated 8-gram ratio"` (the exact prefix
     `validate_global`'s own repetition-error message already uses -- no new
     error-shape needed) and `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS > 0`:
     - Re-fetch **fresh** checkpoints via `ai_job_service.get_valid_checkpoints`
       (not the in-memory `all_lines`, which has no section boundaries left, and
       not the resume-time `checkpoints_by_index`, which is stale for sections
       generated *during this run*) and rebuild `(section_index, lines)` pairs in
       outline order -- this also means the repetition check sees the
       *already-repaired* last section if the word-budget repair fired first.
     - Run `find_repeated_8grams_by_section`; if it found no attributable
       section (shouldn't happen when `hard_errors` says the ratio is over
       threshold, but defensively means "nothing to fix," falls through to the
       existing hard-fail unchanged).
     - Regenerate **only** the worst section via the existing `_repair_section`
       (same function already used for semantic/length-only/final-budget
       repairs -- reused, not duplicated), with `purpose=
       "script_section_repetition_repair"` (a new, distinct telemetry label,
       matching the precedent Task 14.8 already set for the length-only pass)
       and `errors=[f'repeated phrase used elsewhere in the script: "{phrase}"'
       for phrase in repeated_phrases]` -- the actual offending text, not an
       abstract "reduce repetition" instruction.
     - Overwrite **that exact section's** checkpoint via `save_checkpoint(db,
       job_id, worst_index, "section", ...)` -- PM's note (a): `save_checkpoint`
       already upserts on `(job_id, stage, section_index)` (confirmed in
       `ai_job_service.py`), so passing `worst_index` explicitly is sufficient
       to guarantee the correct checkpoint is the one overwritten, not the last
       section or any other.
     - Rebuild `all_lines` from the same `(section_index, lines)` pairs with the
       worst section's lines swapped in, then re-run `validate_global`. Still
       failing -> falls through to the existing, unchanged `if hard_errors: fail`.
     - A structural error surviving this repair hard-fails with
       `section_validation_failed`, mirroring every other repair path in this
       file (semantic/length-only/final-budget) -- never silently retried.
  6. **`_repair_section`'s existing `purpose` kwarg** (added in Task 14.8) is
     reused as-is, no signature change needed.
  7. **New tests** (`tests/test_script_pipeline.py`): pure-function tests for
     `find_repeated_8grams_by_section` (cross-section-boundary repeat correctly
     attributed to the *starting* section; correct worst-section selection when
     multiple sections have repeats; empty/no-repeat inputs) and
     `frequent_repeated_phrases` (ranking, `limit` cap); e2e tests for items 2-5
     of the card's Verification list; a repair-count-bound test extending Task
     14.8's `test_pipeline_repair_count_hits_the_2n_plus_1_ceiling` pattern to
     `2 * num_sections + 2`.
- Commands and results:
  - `venv\Scripts\python.exe -m ruff check app/services/script_pipeline.py
    app/core/constants.py tests/test_script_pipeline.py` -> All checks passed
    (checked after every edit, then again in full at the end).
  - Rendered `prompts/script/section.txt` directly with a populated
    `avoid_phrases` list (ad-hoc script, not committed) to confirm the new
    `{% if avoid_phrases %}` block renders correctly under `StrictUndefined`.
  - `pytest tests/test_script_pipeline.py -k "find_repeated_8grams or
    frequent_repeated_phrases" -q` -> 7 passed (pure-function tests) --
    one assertion needed correcting after the first run (a hand-computed
    expected phrase was off by one word; fixed against the actual output,
    not weakened).
  - `pytest tests/test_script_pipeline.py -k repetition -q` -> 4 passed
    (the 3 new e2e tests plus the bound test) -- one early bug caught by
    actually running them: `REPEATED_PHRASE` was written as 7 words, not 8,
    which silently changed every hand-derived word-count/ratio expectation
    across all 4 tests; fixed the literal string, re-ran clean.
  - `pytest tests/test_script_pipeline.py -q` (full file) -> **64 passed**
    (was 63 before this task's tests).
  - `pytest -q` (full suite) -> **902 passed, 0 failed** (408.97s), up from
    Task 14.11's 891 baseline.
- Deviations: none from the plan. Every required-behaviour and verification
  item implemented as designed; no file outside the allowed list was needed.
- Revert-and-confirm-failure evidence:
  - **Constants pin:** temporarily changed `SCRIPT_MAX_REPEATED_8GRAM_RATIO`
    from `0.01` to `0.02` (`# REVERT-AND-CONFIRM-FAILURE`) and ran
    `pytest tests/test_script_pipeline.py::test_constants_pin_word_tolerances_are_unchanged_by_task_14_3 -q`:
    **1 failed** (`AssertionError: assert 0.02 == 0.01`). Restored, re-ran
    the full file: 64 passed.
  - **Trigger logic:** temporarily replaced the repetition-only condition's
    `all(error.startswith(...) for error in hard_errors)` with `False`
    (`# REVERT-AND-CONFIRM-FAILURE`) and ran the two success-path e2e tests
    (`test_pipeline_repetition_only_failure_repairs_the_worst_section_and_completes`,
    `test_pipeline_repair_count_hits_the_2n_plus_2_ceiling`): **2 failed**,
    both for the right reason (job status `error`, error message
    `"repeated 8-gram ratio 1.55% >= 1%"` -- exactly the un-repaired failure
    the new pass exists to fix). Restored the real condition, re-ran the
    full file: 64 passed.
- Commit(s): `256ba01` (plan), plus this commit (implementation).
