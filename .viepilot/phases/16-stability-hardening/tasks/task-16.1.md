# Task 16.1 — Worker Loop Guard + Liveness (BUG-022)

- **Status:** not started
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** none
- **Controlling detail:** plan §4 "16.1", invariant 25; `.viepilot/requests/BUG-022.md`

## Measured problem (do not re-derive)

`app/services/ai_worker.py:92` `_run_loop` has no try/except around `_claim_next()` and
`_process()`. `_process` catches handler exceptions, but its own error transition
(`transition_status(... "error")`, line 127) is unguarded, and so is `_claim_next`'s
write transaction. Any exception ends the task. There is no done-callback, so nothing
logs it and nothing restarts it. `/health` stays green while every job stays `pending`.

## Allowed files

`app/services/ai_worker.py`, `app/api/ai_jobs.py` (health payload only),
`app/core/constants.py`, `tests/test_ai_worker.py`, `tests/test_ai_health_api.py`,
`tests/test_ai_jobs_api.py` (health assertions only), `CHANGELOG.md`.
Anything else → stop and ask the PM.

## Required behaviour

1. A per-iteration `try/except Exception` in `_run_loop`: `logger.exception`, then a bounded
   backoff via `_stop_event` wait (new constant `AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS`),
   then continue. `CancelledError` propagates.
2. The error transition inside `_process`'s `except` is guarded. An illegal transition is
   logged (`ai_worker_error_transition_failed`), not raised.
3. `start()` adds a done-callback that logs at ERROR if the task ends while
   `_stop_event` is unset. A public `is_alive` property.
4. `/api/ai/health` gains `worker_alive: bool`. Existing fields are unchanged.

## Explicitly forbidden

Swallowing `CancelledError`; changing the job transition matrix; restarting the worker
from inside the health route.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending_

## Verification (required)

- `_claim_next` raises once → the loop survives → a later job still completes.
- A handler raises after committing `complete` → the loop survives, and the job stays
  `complete`.
- `stop()` still honours the grace period. Cancellation is not swallowed.
- Health reports `worker_alive: false` for a dead or finished task.
- Revert-and-confirm-failure on the loop-survival test. Full suite. `ruff`.

## Evidence

_pending_
