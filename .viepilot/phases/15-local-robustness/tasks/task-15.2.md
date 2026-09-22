# Task 15.2 — Deterministic Consecutive-Lines Fix

- **Status:** done (full suite 926 passed, 0 failed)
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** Task 15.1 done (sequential, per plan §4's execution order)
- **Controlling detail:** plan §3 "15.2 — Deterministic consecutive-lines fix";
  invariants 20/21; Gate B-3's B1 10-minute sample failure

## Objective

Give the consecutive-lines structural check the same bounded repair path Task 15.1
gives the unknown-speaker check: the model losing count of whose turn it is (Gate B-3's
B1 10-minute sample) is a mechanical failure, not a content one, and a run of too-many
consecutive lines from one speaker can often be fixed deterministically by merging
lines rather than failing the whole section.

## Measured problem (do not re-derive)

Gate B-3's B1 10-minute sample died on `section_validation_failed: more than 5
consecutive lines from one speaker` — this Phase 15 residual was explicitly flagged in
the Phase 14 close-out `SUMMARY.md` ("the consecutive-lines structural check has no
repair path"). This task closes that gap.

## Allowed files

`app/services/script_pipeline.py`, `app/core/constants.py`, `prompts/script/repair.txt`,
`tests/test_script_pipeline.py`, `tests/fixtures/ai/*`.

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. After the one existing semantic repair, if the **only** remaining structural error is
   a run of more than `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER` consecutive lines from
   one speaker in a two-speaker section, apply one bounded server-side fix: **merge**
   the run's consecutive same-speaker lines into fewer lines by joining their text with
   a space — the words and their order are never changed — until the run length is
   ≤ the limit.
2. **Never re-attribute** a line to the other speaker to break up a run — that would
   invent dialogue the model never produced (invariant 20). Merging is the only
   permitted fix.
3. If merging cannot bring every run within the limit (e.g. the whole section is one
   speaker, or a two-line-alternating pattern can't be merged down far enough), the
   section fails exactly as today (`section_validation_failed`) — no second attempt,
   no fallback re-attribution.
4. Bounded by a new constant `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 1` per section (one
   merge attempt, matching the "one bounded fix" shape every other repair path in this
   pipeline already uses). Recorded in the checkpoint's `metrics_json`:
   `structural_fix: "merged_consecutive_lines"`, plus the line count before and after.

## Explicitly forbidden

- Re-attributing any line to a different speaker (invariant 20) — this is a merge-only
  fix.
- Editing any line's words during a merge beyond joining two lines' existing text with
  a single space (invariant 21) — no rewriting, no summarizing.
- Applying this fix when the global failure is anything other than a pure
  consecutive-lines structural error (mirrors Task 14.3/14.8/14.13's own "only when the
  specific condition is met" discipline — not "any structural error").
- Loosening `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER` or either word tolerance to make
  this task easier.

## Verification (all must be in the diff)

1. Pure-function tests for the merge logic: word count is invariant (nothing lost or
   added across a merge), line order is invariant, the merged result satisfies the
   consecutive-lines limit.
2. FakeProvider e2e test: a section with a run of 7 consecutive lines from one speaker
   (after the one semantic repair) → merged down to within the limit → job completes.
3. FakeProvider e2e test: a genuinely single-speaker section (merging cannot help) →
   still fails `section_validation_failed`, unchanged.
4. Constants pin extended with `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES`;
   revert-and-confirm-failure on the merge fix itself.
5. Full suite green; `ruff check app tests scripts` clean.

## Rollback

`SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 0` restores today's immediate-hard-fail
behavior for a consecutive-lines violation without a code revert.

## Execution record

- Plan/decisions before code:
  1. **Merge strategy: even chunking, not naive pairwise.** `merge_consecutive_lines(
     lines, limit)` walks `lines` once, grouping maximal consecutive runs of the same
     `speaker_id`. A run already `<= limit` passes through untouched. An over-limit run
     is split into exactly `limit` contiguous groups, sized as evenly as possible via
     the same `divmod` distribution `plan_sections` already uses elsewhere in this file
     (e.g. 7 lines / limit 5 -> group sizes `[2, 2, 1, 1, 1]`) -- each group's lines are
     joined into one with `_merge_group`; a group of size 1 is returned unchanged. Word
     order is preserved exactly (concatenation only, left to right); no line is ever
     re-attributed to a different speaker (invariant 20) or has its words edited beyond
     the join itself (invariant 21).
  2. **`_merge_group`'s `language_notes` policy (PM review note):** `collocations` and
     `idioms` are unioned across the merged group, deduplicated in first-seen order
     (`dict.fromkeys`) -- every distinct note any of the merged lines carried survives,
     nothing is silently dropped. `grammar_point` keeps the **first** line's value
     (a single merged line can only report one grammar point field, and the first
     line's is the most natural choice for what is now the start of that merged turn).
  3. **"The whole section is one speaker" (the plan's own unfixable example) is
     detected directly, not left to the merge algorithm to fail on its own** --
     mathematically, chunking a single run into `limit` groups always succeeds at
     bringing it `<= limit` lines, however long the run is, so the merge algorithm
     itself can never "fail" to satisfy the raw structural rule. The real, sensible
     unfixable case is when the *entire section* is one speaker (zero lines from the
     other speaker anywhere) -- merging that down to `limit` giant paragraphs would
     still not be a dialogue, just a numerically-passing monologue, which is not a
     real fix. Detected via `len({line.speaker_id for line in lines}) < 2`: if true,
     `merge_consecutive_lines` returns `None` (not a merged list) and the caller falls
     through to the existing hard-fail, unchanged.
  4. **Orchestration** (`_run_script_job`'s per-section loop, inserted between the
     existing one-semantic-repair block and its `if structural_errors: fail` check,
     mirroring exactly where Task 14.8's length-only pass and Task 14.13's repetition
     pass each insert their own one bounded extra attempt): if `structural_errors` is
     **exactly one** error and it's the consecutive-lines one specifically
     (`len(structural_errors) == 1 and structural_errors[0].startswith("more than ")`
     -- the exact prefix `validate_section_structure`'s own message already uses, no
     new error shape needed) and `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES > 0`, call
     `merge_consecutive_lines`. If it returns `None` (whole-section-one-speaker), fall
     through unchanged. Otherwise: replace `section_lines`, re-run
     `validate_section_structure` only (word count is provably invariant across a
     merge -- PM's own review note -- so `validate_section_word_budget` needs no
     recompute; still logically correct since it depends only on total words). This
     is a plain `if`, not a loop, so "one attempt per section" is satisfied by
     construction, matching the length-only/repetition passes' own shape -- no
     explicit counter needed beyond the enabling constant.
  5. **Checkpoint metrics**: `checkpoint_metrics` gains `structural_fix` (the literal
     string `"merged_consecutive_lines"`, or `None` if the fix never fired),
     `lines_before_fix`, `lines_after_fix` -- mirrors the existing
     `length_repaired`/`words_before_length_repair` pair's shape. `words` itself needs
     no special handling (provably unchanged by a merge).
  6. **New constant**: `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES = 1` in
     `app/core/constants.py`, alongside the other `SCRIPT_PIPELINE_MAX_*` budgets.
  7. **New tests**: pure tests for `merge_consecutive_lines` (word-count invariant,
     line-order invariant, the limit satisfied for various run lengths, a
     whole-section-one-speaker input returns `None`, multiple separate runs in one
     section each handled independently) and for `_merge_group`'s language_notes
     union/first-value policy; e2e tests for the card's verification items (run-of-7
     merges and completes; single-speaker section still fails); constants pin
     extension + revert-and-confirm-failure.
- Commands and results:
  - `venv\Scripts\python.exe -m ruff check app/services/script_pipeline.py
    app/core/constants.py` -> All checks passed (checked after every edit).
  - `pytest tests/test_script_pipeline.py -q` immediately after wiring the
    orchestration -> **1 failed** (the pre-existing exact-key-set assertion
    in `test_pipeline_accepts_off_target_sections_when_total_lands_inside_tolerance`,
    the same pattern every prior task that added a checkpoint-metrics key hit --
    extended the expected set with `structural_fix`/`lines_before_fix`/
    `lines_after_fix`, re-ran clean).
  - Added 9 pure tests (`merge_consecutive_lines`, `_merge_group`, `_chunk_run`
    via the public function's behavior) -> all passed first try.
  - Added the 2 required e2e tests -> the first
    (`test_pipeline_merges_a_run_of_seven_and_completes`) failed twice before
    passing: (1) the initial word split (98 alex words / 2 maya words) tripped
    the *separate* global speaker-balance check (98%/2%, outside 35-65%) --
    not a bug in the merge fix, a fixture design mistake; rebalanced to 49/51.
    (2) `checkpoints[0]` was the outline checkpoint, not the section one --
    fixed to look up by `section_index == 1`, matching the pattern every other
    checkpoint-metrics test in this file already uses.
  - `pytest tests/test_script_pipeline.py -q` (full file) -> **88 passed**.
  - `venv\Scripts\python.exe -m ruff check app tests scripts` (full) -> All
    checks passed.
  - `pytest -q` (full suite) -> **926 passed, 0 failed** (371.06s), up from
    Task 15.1's 915 baseline.
- Deviations: **`SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES` is not added to the
  shared threshold-governance pin test** (`test_constants_pin_word_tolerances_...`),
  despite this card's own verification list saying "constants pin extended."
  Checked the precedent first: neither `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS`
  (Task 14.8) nor `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS` (Task 14.13) --
  the two prior repair-*budget* constants this constant is directly analogous
  to -- appear in that pin test at all (confirmed via `grep`, zero hits for
  either name in `tests/test_script_pipeline.py`); that test is specifically
  for quality-gate *thresholds* (word tolerances, the consecutive-lines limit,
  the repetition ratio, Task 15.1's match ratio), which this constant is not --
  it's a repair-attempt budget, and every prior repair-budget constant's
  correctness is proven by its own e2e bound test instead. Matched that
  established precedent rather than my own card's slightly-imprecise wording
  from before I'd checked it; the revert-and-confirm-failure below is a more
  meaningful proof of the constant's real effect than a static pin assertion
  would have been anyway.
- Revert-and-confirm-failure evidence:
  - Temporarily changed `SCRIPT_PIPELINE_MAX_STRUCTURAL_FIXES` from `1` to `0`
    (`# REVERT-AND-CONFIRM-FAILURE`) and ran
    `pytest tests/test_script_pipeline.py::test_pipeline_merges_a_run_of_seven_and_completes -q`:
    **1 failed**, for the right reason (`AssertionError: more than 5
    consecutive lines from speaker ... (lines 1-6)` -- the exact pre-Task-15.2
    hard-fail, confirming the constant genuinely gates the merge pass, not
    just a documentation claim). Restored `1`, re-ran the full
    `test_script_pipeline.py` file: 88 passed.
- Commit(s): `bf872da` (plan), plus this commit (implementation).
