# Task 16.1 — Worker Loop Guard + Liveness (BUG-022)

- **Status:** done
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

**1. `_run_loop` per-iteration guard (constants.py + ai_worker.py)**
Add `AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS = 5.0` next to
`AI_WORKER_SHUTDOWN_GRACE_SECONDS` in `app/core/constants.py`. Wrap the loop body
(the `_claim_next()` call and the `job is None` branch's dispatch to `_process()`)
in `try/except Exception`. On catch: `logger.exception("ai_worker_loop_error")`,
then back off via `asyncio.wait_for(self._stop_event.wait(),
timeout=AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS)` (swallowing the resulting
`TimeoutError` the same way the existing poll-wait does), then `continue`.
`asyncio.CancelledError` subclasses `BaseException`, not `Exception`, in the
Python versions this project targets (3.8+), so `except Exception` already lets
it propagate untouched — no special-case re-raise needed. `stop()`'s own
cancel-after-grace-period path is unaffected since it cancels `self._task`
directly, which raises `CancelledError` *inside* whatever the loop is currently
awaiting, not something the new `except Exception` around the loop body would
ever see as `Exception`.

**2. Guard the error-transition write in `_process` (ai_worker.py:126-134)**
Wrap the existing `async with write_transaction(db): await
ai_job_service.transition_status(...)` block (the one already inside
`_process`'s `except Exception as exc:`) in its own nested `try/except
Exception`. On catch (for example an illegal-transition `ValidationError`
because the handler already committed a terminal status before raising, or a
transient `database is locked`): `logger.exception
("ai_worker_error_transition_failed job_id=%s operation=%s", job["id"],
job["operation"])`, and swallow it — `_process` still returns normally either
way, so the outer loop guard from (1) is genuine belt-and-braces, not the
primary defense for this specific path.

**3. Done-callback + `is_alive` (ai_worker.py)**
In `start()`, after `self._task = asyncio.create_task(self._run_loop())`, attach
`self._task.add_done_callback(self._on_loop_done)`. `_on_loop_done(task)` only
logs when the task ended while the worker wasn't told to stop: `if
self._stop_event is not None and not self._stop_event.is_set():` then, if
`task.cancelled()`, `logger.error("ai_worker_task_ended_unexpectedly
reason=cancelled")`; else `logger.error("ai_worker_task_ended_unexpectedly
exc=%r", task.exception())`. Add a public `is_alive` property: `return
self._task is not None and not self._task.done()`.

**4. `worker_alive` on `/api/ai/health` (ai_jobs.py)**
`app/main.py` (not in this task's allowed-files list) constructs the one real
`AIWorker` singleton at module scope (`ai_worker = AIWorker(...)`, `app/main.py:31`)
*after* it imports `app.api.ai_jobs` (`app/main.py:12`) to build the router. A
top-level `from app.main import ai_worker` in `ai_jobs.py` would therefore be a
circular import that fails at process start (app.main is still mid-import when
ai_jobs.py's top-level statements run). Instead, `ai_health()` does the import
lazily, inside the function body, at request time — by then `app.main` has
finished importing and the module attribute exists. This mirrors the existing
pattern of importing `app.main` only from leaf modules (`desktop_launcher.py`,
the test files), just deferred to call time instead of module load time so it
works from a module `app.main` itself imports. Add one field to the returned
dict: `"worker_alive": ai_worker.is_alive`. No existing field changes.

**Test plan**
- `tests/test_ai_worker.py`: (a) `_claim_next`'s dependency
  (`ai_job_service.find_next_pending_job`) raises once via a monkeypatched
  wrapper with a call counter, then a second job still gets claimed and
  completed — proves the loop survives and keeps working, per the card's first
  verification bullet. (b) a handler that transitions its job to `complete`
  itself and then raises — proves `_process`'s guarded error-transition (2)
  logs and swallows the resulting illegal-transition error rather than raising,
  and the job stays `complete`, not `error`. (c) directly `task.cancel()` the
  loop task (bypassing `stop()`) and confirm `CancelledError` propagates
  (`task.cancelled()` is `True`) — proves (1) doesn't swallow cancellation. (d)
  `is_alive` is `True` right after `start()` and `False` after `stop()`. (e) the
  done-callback logs `ai_worker_task_ended_unexpectedly` (via `caplog`) when the
  loop task is cancelled directly instead of through `stop()`.
- `tests/test_ai_health_api.py`: add `worker_alive` to the locked
  `expected_keys` set (`test_health_response_has_no_extra_undeclared_fields`).
  Add one test that it's `True` during normal `TestClient` lifespan, and one
  that monkeypatches the real singleton's private `_task` to `None`
  (`from app.main import ai_worker; monkeypatch.setattr(ai_worker, "_task",
  None)`) and confirms the endpoint then reports `False` — this is the only
  practical way to exercise the "dead task" branch over HTTP without touching
  `app/main.py`, which is outside this task's allowed files.
- `tests/test_ai_jobs_api.py`: no changes expected (its two `/api/ai/health`
  tests assert individual keys present, not a closed set); will confirm during
  implementation and only touch it if something there breaks.
- Revert-and-confirm-failure target: test (a) above (the loop-survival test),
  by temporarily removing the `try/except` around the loop body and confirming
  it fails, then restoring it.

**Known residual (PM note N2, folded in post-approval)**
If the guarded error-transition (2) itself fails for a transient reason (for
example `database is locked`), the job stays `running` rather than reaching
`error`. It's only reclaimed by `recover_abandoned_jobs` at the next
`start()`, once its lease expires. Acceptable for 16.1 — the loop survives and
the job id is logged (`ai_worker_error_transition_failed`) — not in scope to
fix here.

**PM note N1 (folded in post-approval)**
`AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS` is read as a module attribute
(`ai_worker_module.AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS`) at the point of use
inside `_run_loop`, not captured into a default arg or a local at
`__init__`/import time, so test (a) can `monkeypatch.setattr` it to a small
value (e.g. `0.01`) the same way the existing shutdown-grace test patches
`AI_WORKER_SHUTDOWN_GRACE_SECONDS` — no multi-second sleeps in the suite.

## Verification (required)

- `_claim_next` raises once → the loop survives → a later job still completes.
- A handler raises after committing `complete` → the loop survives, and the job stays
  `complete`.
- `stop()` still honours the grace period. Cancellation is not swallowed.
- Health reports `worker_alive: false` for a dead or finished task.
- Revert-and-confirm-failure on the loop-survival test. Full suite. `ruff`.

## Evidence

- Design commit `f925ea5` (approved by PM, with notes N1/N2 folded in, no
  re-approval required). Implementation commit `56bb74b`. PM ACCEPTED
  (TRACKER `7955561`): targeted 19/19, own revert check (loop guard removed →
  both loop tests fail; restored → 12/12), full suite 940 passed, ruff clean.
- Files touched, all within the allowed list: `app/services/ai_worker.py`
  (per-iteration loop guard, guarded error-transition, done-callback,
  `is_alive`), `app/core/constants.py` (`AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS
  = 5.0`), `app/api/ai_jobs.py` (`worker_alive` field on `/api/ai/health`, via
  a lazy `from app.main import ai_worker` inside the route, with a comment
  explaining why), `tests/test_ai_worker.py` (+6 tests),
  `tests/test_ai_health_api.py` (+2 tests, plus the locked key-set updated),
  `CHANGELOG.md`. `tests/test_ai_jobs_api.py` needed no changes (its two
  `/api/ai/health` tests assert individual keys, not a closed set).
- Targeted run: `tests/test_ai_worker.py tests/test_ai_health_api.py
  tests/test_ai_jobs_api.py` → 33 passed.
- Full suite: `./venv/Scripts/python.exe -m pytest -q` → **940 passed** (932
  baseline + 8 new tests: 6 in `test_ai_worker.py`, 2 in
  `test_ai_health_api.py`). No baseline test broke.
- `ruff check app scripts tests` → all checks passed.
- Revert-and-confirm-failure: temporarily removed the `try/except Exception`
  wrapper around `_run_loop`'s body and re-ran
  `test_loop_survives_a_transient_claim_error_and_processes_a_later_job` alone
  → failed as expected (the injected `RuntimeError` propagated out of
  `_claim_next`, ended the task, and the new done-callback correctly logged
  `ai_worker_task_ended_unexpectedly`, confirming that piece too). Restored
  the guard → the same test and the full `test_ai_worker.py` file (12 tests)
  passed again.
- Verification bullets from the card, confirmed by test:
  - `_claim_next` raises once → loop survives → later job completes:
    `test_loop_survives_a_transient_claim_error_and_processes_a_later_job`.
  - A handler raises after committing `complete` → loop survives, job stays
    `complete`:
    `test_process_survives_an_illegal_error_transition_after_handler_already_completed`.
  - `stop()` still honours the grace period: pre-existing
    `test_worker_stop_is_bounded_even_if_a_handler_never_returns`, unmodified
    and still passing.
  - Cancellation is not swallowed:
    `test_run_loop_does_not_swallow_cancellation`.
  - Health reports `worker_alive: false` for a dead task:
    `test_health_reports_worker_alive_false_when_the_worker_task_is_dead`
    (whitebox, clears the real singleton's `_task`) plus the unit-level
    `test_is_alive_reflects_task_lifecycle`.
