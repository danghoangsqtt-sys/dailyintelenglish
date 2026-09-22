# Task 15.3 — Trial Runner Per-Gate Evidence Path + `_record_dropped_items` Layering

- **Status:** pending
- **Owner:** Coder
- **Priority:** P2
- **Dependency:** Task 15.2 done (sequential, per plan §4's execution order)
- **Controlling detail:** plan §3 "15.3"; Phase 14 close-out `SUMMARY.md`'s two other
  flagged residuals (the runner's fixed `gate-b2/` evidence path,
  `_record_dropped_items` as a workaround)

## Objective

Close the other two residuals the Phase 14 `SUMMARY.md` flagged honestly: the trial
runner has always written every gate's evidence into a hard-coded
`data/quality_reviews/phase14/gate-b2/` subdirectory regardless of which gate is
actually running, and `learning_pipeline._record_dropped_items` is a local
read-modify-write workaround that duplicates `ai_job_service.record_generation_call`'s
shape only because `ai_job_service.py` was outside Task 14.11's allowed files.

## Allowed files

`scripts/run_ai_operational_trial.py`, `app/services/ai_job_service.py`,
`app/services/learning_pipeline.py`, `tests/test_ai_job_service.py`,
`tests/test_learning_pipeline.py`.

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. `scripts/run_ai_operational_trial.py` gains a `--gate <name>` option that selects
   `data/quality_reviews/phase15/<name>/` for both evidence and trial-data output;
   omitting it keeps today's default path (no behavior change for any existing
   invocation).
2. `app/services/ai_job_service.py` gains `set_job_metric(db, job_id, key, value)` — a
   small, generic function that reads a job's `metrics_json`, sets one sibling key
   (next to the existing `"calls"` list `record_generation_call` already manages), and
   writes it back. This is the proper home for the read-modify-write shape
   `learning_pipeline._record_dropped_items` had to duplicate locally in Task 14.11
   because `ai_job_service.py` wasn't in that task's allowed files.
3. `learning_pipeline._record_dropped_items` is replaced by a call to
   `ai_job_service.set_job_metric(db, job_id, "dropped_items", dropped_items)` —
   behavior is unchanged (same `metrics_json["dropped_items"]` shape Task 14.11 already
   ships and tests), only the implementation moves to its proper layer. The dedicated
   local helper in `learning_pipeline.py` is removed once the shared function replaces
   its one call site.
4. Existing Task 14.11 tests for the dropped-items behavior move to
   `tests/test_ai_job_service.py` (testing `set_job_metric` directly) where they test
   the mechanism, and stay in `tests/test_learning_pipeline.py` where they test the
   pipeline's own behavior end-to-end (both files are in this task's allowed list for
   exactly this reason).

## Explicitly forbidden

- Any change to `_record_dropped_items`'s/`set_job_metric`'s observable behavior —
  this is a pure refactor (move the logic to its proper layer), not a functional
  change. The `metrics_json["dropped_items"]` shape and every Task 14.11 e2e assertion
  must still pass unmodified.
- Changing the default (no `--gate` flag) evidence path for the runner — existing PM
  workflows and any already-written automation must keep working exactly as before.

## Verification (all must be in the diff)

1. `set_job_metric` unit/integration tests in `tests/test_ai_job_service.py` (sets a
   new key; merges alongside an existing `"calls"` list without disturbing it; safe on
   a job with no prior `metrics_json`).
2. Every existing Task 14.11 e2e test in `tests/test_learning_pipeline.py` (dropped-item
   recording, its exact shape) still passes unmodified in behavior, now exercising
   `set_job_metric` under the hood instead of the removed local helper.
3. `--gate <name>` produces evidence under `data/quality_reviews/phase15/<name>/`;
   omitting it reproduces today's default path exactly (smoke-checked via `--help`
   and a dry run, per the established convention for touching this exact script —
   no live matrix run needed for this task).
4. Full suite green; `ruff check app tests scripts` clean.

## Rollback

Pure refactor with no new gating constant — git revert restores the prior state
exactly; no data-shape migration is involved (`metrics_json` is unchanged free-form
JSON either way).

## Execution record

- Plan/decisions before code:
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence: N/A -- this task is a refactor + an additive
  CLI flag, not new gating/threshold logic; correctness is proven by the unchanged
  Task 14.11 test suite passing under the new implementation, not by a
  revert-and-confirm-failure cycle.
- Commit(s):
