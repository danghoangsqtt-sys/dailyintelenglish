# Task 15.2 — Deterministic Consecutive-Lines Fix

- **Status:** pending
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
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
