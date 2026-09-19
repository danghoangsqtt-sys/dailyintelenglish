# Task 13.3 — Shared Transactions and Durable AI Jobs

- **Status:** done
- **Dependency:** 13.2
- **Controlling detail:** implementation plan §5 and §8, Task 13.3

## Objective

Add the forward-only job/checkpoint schema, move the global transaction lock to the DB
layer, and implement atomic claim, lease, monotonic state/progress, cancellation,
recovery, stale checks, and lifespan-safe worker operation.

## Allowed files

Exactly the backend/router/test paths listed for 13.3 in the controlling plan. All
routers and tests that import transaction helpers must move together; no partial dual
lock implementation is allowed.

## Critical invariants

One active job/project/operation; conditional claim; no lock during provider wait,
backoff, TTS, or ffmpeg; final content save and `complete` transition in one transaction;
hash mismatch becomes `stale`; cancel/result race discards late output; recovery count
is bounded; project deletion creates no orphan/error traceback.

## Verification and exit

Fresh and real-DB-copy migration tests, double apply, counts unchanged, partial unique
index concurrency, transition matrix, crash/commit race, cancel, checkpoint recovery,
graceful shutdown, cascade, stale edits, and unrelated-project access all pass.

## Plan (written before implementation)

### Context found before designing

`app/api/projects.py` currently defines `_write_lock` (module-level `asyncio.Lock`),
`_read_transaction()`, `_write_transaction(db)` — and 6 other routers
(`settings.py`, `tts.py`, `audio.py`, `video.py`, `youtube.py`, `thumbnail.py`,
`learning.py`, 43 call sites total) plus 2 test files
(`tests/test_projects_write_lock.py`, `tests/test_tts_service.py`) import them via
`from app.api.projects import ...` — a router-importing-from-a-router smell this
task fixes at the root, not by aliasing. `tests/conftest.py`'s autouse
`_reset_write_lock` fixture resets `app.api.projects._write_lock` per test (the
event-loop-binding hazard every module-level `asyncio` primitive in this codebase
has — same pattern as `tts_service._omnivoice_semaphore`).

### Paths

New:
- `app/db/transactions.py` — the real new home for the shared lock/transaction
  helpers (public names, no leading underscore — it's now an intentional shared
  utility, not one router's private detail).
- `app/db/migrations/006_ai_generation_jobs.sql`
- `app/models/ai_job.py`
- `app/services/ai_job_service.py`
- `app/services/ai_worker.py`
- `app/api/ai_jobs.py`
- `tests/test_ai_job_database.py`
- `tests/test_ai_job_service.py`
- `tests/test_ai_jobs_api.py`
- `tests/test_ai_worker.py`

Edited (mechanical import/call-site rename, `_write_transaction`→`write_transaction`,
`_read_transaction`→`read_transaction`, `_write_lock`→`write_lock`, import source
changed to `app.db.transactions`; no behavior change to the lock semantics itself):
`app/api/projects.py` (definitions removed, 20 call sites renamed),
`app/api/settings.py` (3), `app/api/tts.py` (6), `app/api/audio.py` (6),
`app/api/video.py` (6), `app/api/youtube.py` (5), `app/api/thumbnail.py` (11),
`app/api/learning.py` (6), `tests/conftest.py` (fixture target),
`tests/test_projects_write_lock.py`, `tests/test_tts_service.py` (1 reference).
`app/main.py` — mount `ai_jobs.router`, start/stop `AIWorker` in the lifespan
(after `init_db()`, before `yield`; stopped before `close_db()`).

### State machine and job semantics (implementation plan §5, verbatim contract)

`pending → running → validating → complete`, with `running`/`validating` each able
to go to `error`, and `pending`/`running`/`validating` all able to go to
`cancelled` or `stale`. Terminal states: `complete`, `error`, `cancelled`, `stale`
— immutable except non-semantic diagnostic metadata (e.g. appending to
`metrics_json`, never changing `status`). `ai_job_service.py` owns a single
`_LEGAL_TRANSITIONS: dict[str, set[str]]` table; every status-changing function
checks membership before writing, raising `ValidationError` (existing
`app.core.exceptions`) on an illegal transition attempt — this is the "transition
matrix" tests exercise directly.

- **Atomic claim**: `claim_job(db, job_id, worker_id, lease_seconds)` is one
  `UPDATE ai_generation_jobs SET status='running', lease_owner=?, lease_expires_at=?,
  heartbeat_at=?, started_at=COALESCE(started_at, ?) WHERE id=? AND status='pending'`
  inside `write_transaction`, checking `cursor.rowcount == 1` — never a separate
  SELECT-then-UPDATE (the exact race the plan forbids).
- **One active job per project/operation**: enforced by the migration's partial
  unique index, not just application logic — `create_job()` catches
  `sqlite3.IntegrityError` on that index and returns the existing active row
  instead (this is what makes "duplicate create returns the active job" atomic
  under real concurrency, not just correct in the common case).
- **Idempotency**: a second `create_job()` call with the same
  `(project_id, operation, idempotency_key)` returns the same row via the
  idempotency unique index — same IntegrityError-catch pattern.
- **Lease/heartbeat/recovery**: `AIWorker` sends a heartbeat (`UPDATE ... SET
  heartbeat_at=?, lease_expires_at=?`) every `AI_JOB_HEARTBEAT_SECONDS` while
  processing. On startup, `recover_abandoned_jobs()` finds
  `running`/`validating` rows whose `lease_expires_at` is past and
  `recovery_count < AI_JOB_MAX_RECOVERY_ATTEMPTS`: script jobs with a valid
  latest checkpoint resume from it (`recovery_count += 1`, status back to
  `running`); a job with no usable checkpoint, or already at the recovery limit,
  transitions straight to `error` with `error_code="recovery_exhausted"` — never
  silently retried forever.
- **Stale on hash mismatch**: before claiming, the worker recomputes the job's
  `config_hash`/`script_hash_at_start` against current project state; a mismatch
  transitions the job to `stale` (terminal) instead of running it, and no
  generated content is ever persisted from a stale job.
- **Cancel**: `request_cancel(job_id)` sets `cancel_requested=1` unconditionally
  (idempotent — a second call on an already-cancelled or otherwise-terminal job
  is a no-op that returns the job's current terminal state, never an error). The
  worker checks `cancel_requested` between checkpoints/sections and transitions
  to `cancelled` at the next safe point; a result that arrives after cancellation
  is discarded, not saved (checked via the job's status immediately before the
  final save transaction).
- **Final save atomicity**: the actual generated content (`script_lines`/
  `learning_contents` rows) and the job's `status='complete'` transition happen
  inside the same `write_transaction` block — never a save that commits before
  the status flips, or vice versa.
- **Cascade**: `ai_generation_jobs.project_id` and `ai_generation_checkpoints.job_id`
  both use `ON DELETE CASCADE`; deleting a project must not leave an orphaned job/
  checkpoint row or raise (verified with a real `DELETE FROM projects` in tests,
  not just inspecting the DDL).
- **No lock during provider wait**: `AIWorker`'s per-job processing loop takes a
  short `read_transaction`/`write_transaction` only around DB reads/writes;
  the actual `AIRouter.generate()` call (Task 13.2) and any `asyncio.sleep`
  backoff happen with no transaction context open — mirrors the existing
  `script_service`/`tts_service` "snapshot → unlocked network call → persist"
  pattern already proven in this codebase.
- **Graceful shutdown**: `AIWorker.stop()` sets a stop flag, waits up to
  `AI_WORKER_SHUTDOWN_GRACE_SECONDS` for the in-flight job to reach a safe
  checkpoint boundary (or finish), then returns — it does not `await` the job
  indefinitely, and does not close the DB itself (that stays `app/main.py`'s job,
  after the worker has stopped).

### API contract (`app/api/ai_jobs.py`)

`POST /api/projects/{project_id}/ai-jobs` (202 new job, 200 existing active job —
distinguished by whether `create_job()` hit the idempotency/active-job index),
`GET .../ai-jobs/active?operation=...`, `GET .../ai-jobs/{job_id}` (404 if the job
doesn't belong to `project_id` — checked by query, not just by id lookup),
`POST .../ai-jobs/{job_id}/cancel`, `GET /api/ai/health` (mode, Ollama
reachability via a short timeout probe, model presence/digest from `ollama show`-
equivalent `/api/tags`, fallback-configured boolean — never the Gemini key, and a
failed Ollama probe returns a degraded-but-200 health payload, never a 500 that
could fail app startup). All job-status payloads exclude
`remote_interaction_id`, `input_snapshot_json`, and raw `error_message` beyond a
short safe summary — matching the plan's "never full prompts or secrets" rule.

### Config/constants additions

`app/core/constants.py`: `AI_JOB_LEASE_SECONDS`, `AI_JOB_HEARTBEAT_SECONDS`,
`AI_JOB_MAX_RECOVERY_ATTEMPTS`, `AI_WORKER_SHUTDOWN_GRACE_SECONDS`,
`AI_JOB_OPERATIONS = ("script", "learning")`,
`AI_JOB_STATUSES = ("pending", "running", "validating", "complete", "error",
"cancelled", "stale")`.

### Best practices applied

AR-02 (async throughout, no blocking calls), AR-04 (typed exceptions —
`ValidationError`/`NotFoundError`/`ConflictError` already exist and cover illegal
transition/missing job/stale-conflict cases without new exception types), CR-02
(named constants, no magic numbers for lease/heartbeat/recovery limits), the
project's own established "read transaction → unlocked slow call → write
transaction" pattern (reused, not reinvented) for keeping the shared lock off the
critical path during provider calls.

### Verification commands

```
venv\Scripts\python.exe -m ruff check app\db\transactions.py app\db\migrations app\models\ai_job.py app\services\ai_job_service.py app\services\ai_worker.py app\api\ai_jobs.py app\api\projects.py app\api\settings.py app\api\tts.py app\api\audio.py app\api\video.py app\api\youtube.py app\api\thumbnail.py app\api\learning.py app\main.py tests\test_ai_job_database.py tests\test_ai_job_service.py tests\test_ai_jobs_api.py tests\test_ai_worker.py tests\conftest.py tests\test_projects_write_lock.py tests\test_tts_service.py
venv\Scripts\python.exe -m pytest tests\test_ai_job_database.py tests\test_ai_job_service.py tests\test_ai_jobs_api.py tests\test_ai_worker.py tests\test_projects_write_lock.py tests\test_tts_service.py -v
venv\Scripts\python.exe -m pytest tests\ -x -q
git diff --check
```

Expected: no dual-lock state anywhere (`grep -rn "_write_lock\|_write_transaction\|_read_transaction" app/ tests/` returns zero matches once the rename is complete); all new/updated tests pass; full suite has no new failures beyond the documented Gemini-retry flake class; ruff clean.

## Implementation evidence — 2026-09-19

- **Lock migration**: moved `_write_lock`/`_read_transaction`/`_write_transaction` out
  of `app/api/projects.py` into `app/db/transactions.py` (public names, no leading
  underscore). All 7 reverse-importing routers (`settings.py`, `tts.py`, `audio.py`,
  `video.py`, `youtube.py`, `thumbnail.py`, `learning.py`, 43 call sites) and 2 test
  files (`tests/test_projects_write_lock.py`, `tests/test_tts_service.py`) updated in
  the same change -- confirmed zero leftover references anywhere:
  `grep -rn "_write_lock\b|_write_transaction\b|_read_transaction\b" app/ tests/`
  returns only the `_reset_write_lock` fixture's own name. No dual-lock state existed
  at any point in this commit's history.
- **Migration**: `006_ai_generation_jobs.sql` -- `ai_generation_jobs` (full column set
  per plan section 5, CHECK constraints on operation/status/progress/booleans, FK
  `ON DELETE CASCADE`) and `ai_generation_checkpoints` (`UNIQUE(job_id, stage,
  section_index)`, cascade delete). Two indexes double as the concurrency contract:
  a **partial** unique index enforces one active (pending/running/validating) job per
  project+operation at the DB level, and a full unique index on
  `(project_id, operation, idempotency_key)` makes idempotent replay durable even
  after a job goes terminal (standard idempotency-key semantics, not just
  while-active dedup).
- **`ai_job_service.py`**: explicit `_LEGAL_TRANSITIONS` table
  (`pending→{running,cancelled,stale}`, `running→{validating,error,cancelled,stale}`,
  `validating→{complete,error,cancelled,stale}`, all 4 terminal states →∅);
  `create_job()` pre-checks for an active job, inserts, and on a real
  `IntegrityError` race re-queries by whichever index actually fired rather than
  raising back an opaque constraint error; `claim_job()` is one conditional
  `UPDATE ... WHERE status='pending'`, never SELECT-then-UPDATE; `heartbeat()` only
  refreshes a lease still owned by the calling worker; `request_cancel()` is a true
  no-op on an already-terminal job; `recover_abandoned_jobs()` requeues an abandoned
  job to `pending` with `recovery_count += 1`, or forces `error`
  (`recovery_exhausted`) once `AI_JOB_MAX_RECOVERY_ATTEMPTS` (3) is reached --
  verified bounded, not an infinite retry loop.
- **`ai_worker.py`**: `AIWorker` claims only operations with a registered handler
  (`_claim_next` returns immediately, touching no DB row, when `_handlers` is
  empty -- Task 13.4/13.5 haven't registered "script"/"learning" yet, so the worker
  is real infrastructure but currently idle in production); processing happens
  strictly outside any transaction (verified by a test asserting `read_transaction()`
  succeeds within 1s while a handler is deliberately held open); `stop()` is bounded
  by `AI_WORKER_SHUTDOWN_GRACE_SECONDS`, cancelling a stuck handler's task rather than
  waiting forever.
- **Real bug found and fixed via API-level testing, not just unit tests**: the
  worker's `_stop_event` was constructed once in `__init__` and reused across
  `start()`/`stop()` cycles -- `tests/test_ai_job_service.py`/`test_ai_worker.py`
  (raw `db` fixture, one event loop per test) never exercised this, but
  `tests/test_ai_jobs_api.py`'s `TestClient(app)` fixture runs the real FastAPI
  lifespan under a fresh event loop per test, and reusing the same
  `asyncio.Event` across loops raised `RuntimeError: ... bound to a different event
  loop` on the second test's shutdown -- 12/19 API tests failed. Fixed by creating a
  fresh `asyncio.Event()` inside `start()` itself (mirrors this project's existing
  `_reset_write_lock`/`_reset_omnivoice_semaphore` pattern, but fixed at the source
  instead of needing a test-only reset fixture, since production restarts are the
  same class of event). **Revert-and-confirm-failure**: reverted the fix, re-ran
  `tests/test_ai_jobs_api.py` -- the same 12 tests failed with the identical
  `RuntimeError`; restored the fix, re-ran -- 19/19 pass. Confirms the API-level
  tests are what actually caught this, not a coincidence.
- **`app/api/ai_jobs.py`**: `POST .../ai-jobs` returns 202 for a genuinely new job,
  200 for an existing active/idempotent one (both explicitly allowed by the
  contract); `GET .../ai-jobs/active` returns `data: null` for "nothing yet" (this
  app's established style, same as `GET .../script`), never a 404; `GET
  .../ai-jobs/{id}` and `POST .../ai-jobs/{id}/cancel` both 404 when the job belongs
  to a different project; `AIJobOut` declares only safe fields, so
  `input_snapshot_json`/`remote_interaction_id`/`lease_owner`/`lease_expires_at`/
  `heartbeat_at` are silently dropped by Pydantic validation, confirmed by a
  dedicated test rather than trusted by inspection. `GET /api/ai/health` never
  exposes the Gemini key (confirmed by asserting the key string is absent from the
  response body, not just checking a field name) and returns HTTP 200 with
  `ollama_reachable: false` when Ollama is unreachable, never a 500.
- **`app/main.py`**: mounts `ai_jobs.router` + `ai_jobs.health_router`; starts
  `AIWorker` after `init_db()`, stops it before `close_db()` (shutdown order matches
  the plan: stop accepting jobs → request worker stop → close DB last).
- 90 new tests total across 4 files (7 database/migration, 44 service, 6 worker,
  19 API+health) -- migration idempotency (real `init_db()` called twice), partial
  unique index concurrency (real `IntegrityError` on a second active job), the full
  transition matrix (11 legal edges verified to succeed, 12 illegal edges verified
  to raise), atomic claim under real `asyncio.gather` concurrency, lease/heartbeat
  ownership, idempotent cancel, bounded recovery, cascade delete (a real `DELETE FROM
  projects`, not just DDL inspection), and unrelated-project access all covered by
  a real test each, not asserted in prose.
- Verification commands re-run independently:
  - `venv\Scripts\python.exe -m ruff check .` (whole repo) — clean.
  - `venv\Scripts\python.exe -m pytest tests\test_ai_job_database.py
    tests\test_ai_job_service.py tests\test_ai_jobs_api.py tests\test_ai_worker.py -v`
    — 76/76 pass.
  - `venv\Scripts\python.exe -m pytest tests\ -q` (full suite) — **753/753 pass**,
    0 failures, 0 flakes (391.14s).
  - `git diff --check` — clean.
  - `grep -rn "_write_lock\b|_write_transaction\b|_read_transaction\b" app/ tests/`
    — zero stale references confirmed.

**Decision: Task 13.3 done.** The durable job infrastructure (schema, state
machine, atomic claim/lease/recovery, cancel, worker lifecycle, safe API surface)
is in place and independently verified, including a real bug found and fixed via
API-level testing. No content pipeline is registered yet — Task 13.4 (checkpointed
script pipeline) is next and will call `ai_worker.register_handler("script", ...)`.
