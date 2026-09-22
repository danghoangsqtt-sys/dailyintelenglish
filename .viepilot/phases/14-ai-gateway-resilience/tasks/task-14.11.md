# Task 14.11 — Learning Repair by Removal

- **Status:** pending
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** Task 14.10 done (sequential, per plan §13's execution order)
- **Controlling detail:** plan §13 "14.11 — Learning repair by removal"; Amendment G
  decision D15; `docs/brainstorm/session-2026-09-21.md` §Addendum 2

## Objective

Stop losing a whole learning pack to one still-ungrounded item after the one repair
pass — drop just that item and publish the rest, but only when every remaining count
still meets the existing minimums; otherwise fail exactly as today.

## Measured problem (do not re-derive)

Gate B-2 and Gate B-3 each lost one otherwise-good learning pack to a single ungrounded
idiom that survived the one repair pass (`learning_pack_repair ok` in telemetry, but the
item still wasn't found verbatim in the transcript on re-check) — `pack_validation_failed`
on an otherwise-complete pack.

## Allowed files

`app/services/learning_pipeline.py`, `app/core/constants.py`,
`prompts/learning/learning_repair.txt` (optional wording only),
`tests/test_learning_pipeline.py`, `tests/fixtures/ai/*`.

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

Current flow (`app/services/learning_pipeline.py::_run_learning_job`, lines ~346-360):
generate → `validate_pack` → if errors, one `_repair_pack` call → `validate_pack` again
→ any remaining error hard-fails with `pack_validation_failed`. This task changes only
what happens **after** that second `validate_pack` call:

1. If the post-repair pack still has errors, split them: **grounding failures**
   (`validate_grounding` — an ungrounded vocabulary `example_sentence`, or an ungrounded
   idiom `phrase`/`example_sentence`) and **answer-consistency failures**
   (`validate_answers` — an MCQ `correct_answer` not among its own `options`) identify
   individual items (vocabulary word / idiom phrase / question text) by construction —
   drop exactly those items from the pack (`pack.vocabulary`/`pack.idioms`/`pack.questions`).
   `validate_counts` and `validate_duplicates` failures are **not** per-item removable and
   are not targeted by this step — a pack that still fails either of those after repair
   continues to hard-fail exactly as today (D15 only covers "still fails
   grounding/answer checks", not a count or duplicate problem).
2. Re-run the **count** checks (`validate_counts`'s existing `LEARNING_MIN_VOCABULARY`/
   `LEARNING_MIN_IDIOMS`/`LEARNING_MIN_GRAMMAR_POINTS`/`LEARNING_MIN_QUESTIONS` bounds,
   unchanged) against the *reduced* pack.
   - If every count still meets its minimum → publish the reduced pack. Record
     `dropped_items: [{"kind": ..., "key": ..., "reason": ...}, ...]` in the job's
     `metrics_json` (a sibling key next to the existing `"calls"` list written by
     `record_generation_call` — no new DB column, no new migration).
   - If any count now falls below its minimum → fail exactly as today,
     `pack_validation_failed`, with the dropped-item list appended to the error message
     tail (so the failure is diagnosable, not just "count too low" with no history).
3. Grammar points are never targeted for removal — `validate_grounding` has no per-item
   grammar check today, and D15's own evidence (Gate B-2/B-3) is about idioms
   specifically; nothing in this task adds a new grounding check for grammar.
4. Every **published** item is still fully grounded and every published MCQ still has a
   valid `correct_answer` — nothing is invented to fill a gap; a dropped item is simply
   removed, never replaced with fabricated content. `LEARNING_MIN_*`/`LEARNING_MAX_*`
   values themselves are unchanged.

## Explicitly forbidden

- Editing any `LEARNING_MIN_*`/`LEARNING_MAX_*` constant to make the new path pass more
  easily — the minimums are the whole point of the "publish only if still valid" gate.
- A second repair call (semantic or otherwise) — this task is a removal step after the
  one existing repair, not a new repair budget.
- Dropping an item for a `validate_duplicates` or `validate_counts` reason — only
  grounding/answer-consistency failures are removable per D15.
- Fabricating a replacement item to backfill a count after a drop.

## Verification (all must be in the diff)

1. FakeProvider e2e test: one ungrounded idiom survives the one repair → dropped →
   job reaches `complete` → `metrics_json["dropped_items"]` records it (kind, key,
   reason) → the saved pack does not contain the dropped item.
2. FakeProvider e2e test: a drop that would breach a minimum (e.g. dropping the only
   idiom when `LEARNING_MIN_IDIOMS == 1`) → `pack_validation_failed`, dropped-item list
   in the message tail, nothing saved.
3. FakeProvider e2e test: an answer-consistency failure (MCQ `correct_answer` not in
   `options`) survives repair → dropped the same way as a grounding failure.
4. Revert-and-confirm-failure on the drop step itself (e.g. temporarily skip the removal
   and confirm the same fixture that now passes goes back to hard-failing, for the right
   reason, then restore).
5. Full suite green; `ruff check app tests scripts` clean.

## Rollback

Revert `_run_learning_job`'s post-repair branch to the pre-14.11 immediate-fail
behavior; no schema/migration change is involved (metrics_json is already free-form
JSON, so removing the `dropped_items` key is not a migration either).

## Execution record

- Plan/decisions before code:
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
