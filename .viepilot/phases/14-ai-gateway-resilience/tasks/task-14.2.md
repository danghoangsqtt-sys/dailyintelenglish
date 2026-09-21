# Task 14.2 — Job Telemetry: Repair, Fallback, Provider, Attempts, Error Codes

- **Status:** done
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** 14.1 (uses `GenerationResult.attempts`/`backoff_seconds`)
- **Controlling detail:** plan §4.2, §5, §6 Task 14.2

## Objective

Make every repair, retry, fallback, and provider choice visible on the
`ai_generation_jobs` row and on section checkpoints, and give provider-caused job
failures a specific `error_code`, so Gate B-2 can separate infrastructure failures from
content failures and measure whether repair helps.

## Measured problem (do not re-derive)

PM verified on the Phase 13 trial DB: every script job row has `repair_count=0`,
`fallback_used=0`, `fallback_count=0`, `actual_provider=NULL`, `model=NULL`,
`metrics_json='{}'`. No pipeline writes any of them; the router's `fallback_used` lives
on the in-memory result only. A Gemini 503 ends as `handler_exception` through the
worker's blanket `except`, indistinguishable from a real bug. Phase 13 invariant 5
("fallback is recorded in job state") is not met at the row level.

## Allowed files

`app/services/ai_job_service.py`, `app/services/script_pipeline.py`,
`app/services/learning_pipeline.py`, `app/models/ai_job.py`, `app/api/ai_jobs.py`
(only if the projection needs it), `app/core/constants.py`,
`tests/test_ai_job_service.py`, `tests/test_script_pipeline.py`,
`tests/test_learning_pipeline.py`, `tests/test_ai_jobs_api.py`.

`docs/api.md` is PM-owned — report the new field; the PM documents it.

## Required behaviour

1. `ai_job_service.record_generation_call(db, job_id, call: dict, commit=True)`:
   - one `UPDATE` inside the caller's transaction; legal only while the job is
     `running`/`validating` (raise `ValidationError` on terminal status);
   - appends `call` to `metrics_json["calls"]`, bounded to
     `AI_JOB_MAX_RECORDED_CALLS = 64` (drop oldest);
   - sets `actual_provider`, `model` from the call;
   - when `call["fallback_used"]`: `fallback_used = 1`, `fallback_count += 1`,
     `fallback_reason` = the safe error class name of the local failure if provided;
   - when `call["is_repair"]`: `repair_count += 1`;
   - updates `updated_at`.
2. Call record (safe fields only): `purpose`, `section_index` (nullable), `provider`,
   `model`, `attempt`, `attempts`, `backoff_seconds`, `latency_ms`, `fallback_used`,
   `circuit_open`, `is_repair`, `outcome` (`"ok"`/`"error"`), `error_type` (nullable),
   `at` (ISO-8601 UTC). Never prompt/response text, never a key.
3. Both pipelines record every router call (outline, section, section repair, learning,
   learning repair) inside their existing short `write_transaction` blocks; on a router
   exception they record an `outcome="error"` call, then fail the job with:
   `provider_unavailable` | `provider_timeout` | `provider_rate_limited` |
   `provider_auth` | `provider_invalid_response` | `provider_error` (base class), safe
   message ≤ 200 chars. `handler_exception` stays reserved for real bugs.
4. Section checkpoints' `metrics_json` (via the existing `save_checkpoint` parameter):
   `target_nominal`, `target_effective` (equal to nominal until 14.3), `words`,
   `deviation_pct`, `repaired`, `words_before_repair` (nullable),
   `errors_before_repair`.
5. `AIJobOut.metrics: dict` — parsed `metrics_json`, `{}` on parse failure. Safe by
   construction (item 2).

## Explicitly forbidden

- Holding any transaction across a router call.
- New columns/migrations (all fields already exist from migration 006).
- Writing to a terminal job.

## Verification (all must be in the diff)

1. Service: append/bound/increment semantics; terminal job refused; `fallback_count`
   increments only when reported; `repair_count` only for `is_repair`.
2. Script pipeline (FakeProvider): happy path → `repair_count == 0`, calls == outline +
   sections, each with `outcome == "ok"`; one-repair-then-succeed → `repair_count == 1`,
   repaired section's checkpoint `metrics_json.repaired is True` with
   `words_before_repair` set; hybrid fallback → `fallback_used == 1`,
   `fallback_count >= 1`, `actual_provider == "gemini"`.
3. Learning pipeline: same for its generate/repair calls.
4. Error codes: providers that always raise each `ProviderError` subclass →
   corresponding `error_code`; never `handler_exception`; prior script/learning content
   untouched.
5. API: `GET …/ai-jobs/{id}` returns `metrics.calls[]`; existing secret-absence and
   projection tests still pass; `input_snapshot_json`/lease fields still excluded.
6. Revert-and-confirm-failure on the `repair_count` increment (test 2 must fail).
7. `ruff` clean; full suite green.

## Rollback

Additive. Nothing to reverse; the frontend already renders `job.fallback_used`.

## Execution record (Coder fills in)

- Plan/decisions before code:
  - `ai_job_service.record_generation_call(db, job_id, call, commit=True)`: one
    SELECT (to check status + read current `metrics_json`) + one UPDATE, inside the
    caller's transaction. Terminal status → `ValidationError`. `metrics_json.calls`
    bounded to `AI_JOB_MAX_RECORDED_CALLS` (new constant, `app/core/constants.py`)
    by slicing to the last N entries (drop oldest). `actual_provider`/`model` set
    via `COALESCE(:value, existing)` in the UPDATE, **not** a plain overwrite --
    an `outcome="error"` call has `provider=None`/`model=None` and must never null
    out a value a prior successful call on the same job already set.
    `fallback_used`/`fallback_count`/`fallback_reason` update only when
    `call["fallback_used"]` is truthy; `repair_count` increments only when
    `call["is_repair"]` is truthy.
  - `fallback_reason`: the plan says "the safe error class name of the local
    failure, if provided". The router (14.1, `contracts.py` -- outside this task's
    allowed files) does not currently surface the local provider's failure type on
    `GenerationResult` at all (only `fallback_used: bool`), so the pipeline has no
    such value to give it in this task. `record_generation_call` accepts an
    optional `call["fallback_reason"]` key and sets it when present ("if
    provided"); neither pipeline populates it in 14.2. Left as a candidate for a
    small `contracts.py` addition in a later task if the PM wants it -- flagging
    here rather than silently doing nothing or scope-creeping into 14.1's closed
    file set.
  - `ai_job_service.provider_error_code(exc: ProviderError) -> str`: a lookup
    table (`ProviderUnavailableError`->`provider_unavailable`,
    `ProviderTimeoutError`->`provider_timeout`,
    `ProviderRateLimitError`->`provider_rate_limited`,
    `ProviderAuthError`->`provider_auth`,
    `ProviderInvalidResponseError`->`provider_invalid_response`), falling back to
    `"provider_error"` for the base class or any other subclass (incl.
    `SchemaValidationError`, which the plan's own enumeration excludes from the
    five specific codes -- it is a `ProviderError` subclass but is not expected to
    reach this function in practice: it is raised only by
    `app/services/ai/validation.py:parse_and_validate` *after* a successful
    `router.generate()`, never by the router/provider layer itself in the current
    codebase -- confirmed by `grep -rn SchemaValidationError app/services/ai`).
  - Per-call recording point: a small `_call_router(db, job_id, router, request,
    *, section_index, is_repair)` wrapper added to *each* pipeline module (small,
    intentional duplication -- matches the existing `_fail`/`_cancel`-per-module
    convention rather than adding cross-module coupling for ~15 lines). It calls
    `router.generate(request)` with **no transaction open**, then opens its own
    short `write_transaction` purely to call `record_generation_call` (success or
    `except ProviderError`, then re-raise). This is what keeps a transaction from
    ever spanning the actual inference call (explicitly forbidden). Both
    pipelines' `_generate_*`/`_repair_*` helpers gain `db`/`job_id` parameters to
    route through this wrapper instead of calling `router.generate` directly.
  - Orchestration (`_run_script_job`/`_run_learning_job`) wraps each `_generate_*`
    call in `try/except ProviderError as exc: await _fail_provider(db, job_id,
    exc); return` (a new small helper mirroring the existing `_fail` shape but
    keyed off an exception). `SchemaValidationError` is still caught *first* and
    separately where it already was (raised by `parse_and_validate`, a distinct
    code path from the router-call try/except) -- `except` order matters since
    `SchemaValidationError` is itself a `ProviderError` subclass.
  - Section checkpoint `metrics_json` (script pipeline only -- learning has no
    section concept): computed in the per-section loop from data already in
    scope. `target_effective` is set equal to `target_nominal`
    (`section_spec.target_words`) in this task -- 14.3 is the one that makes them
    differ. `repaired`/`words_before_repair`/`errors_before_repair` are only
    meaningful once a repair actually ran; `words_before_repair` is `None` (not
    `0`) when no repair happened, matching the plan's "(nullable)" annotation.
  - `AIJobOut.metrics: dict`: added via a Pydantic `model_validator(mode="before")`
    that derives `metrics` from the raw `metrics_json` string column (parsed,
    `{}` on any parse failure) when the input dict doesn't already carry a
    `metrics` key. This means **no change to `app/api/ai_jobs.py`** is needed --
    every route already does `AIJobOut.model_validate(job)`, so the derivation
    happens for free at the model layer, and the file's "only if the projection
    needs it" allowance is exercised by *not* touching it.
  - Test-file decision for verification item 5 (API returns `metrics.calls[]`):
    `tests/test_ai_jobs_api.py`'s existing tests are all plain sync `def
    test_(client):` using `TestClient` -- there is no established pattern in this
    codebase for driving an async `ai_job_service` call against the same
    live/shared DB connection from inside that file without event-loop-binding
    risk (see `conftest.py`'s `_reset_write_lock` docstring for the exact hazard
    class). Rather than introduce a first-of-its-kind async/TestClient mixing
    pattern for one field, the deep verification (`metrics.calls[]` actually
    populated, in the exact shape `AIJobOut` -- the same model the route uses --
    produces) lands in `tests/test_ai_job_service.py` (direct, async, no HTTP).
    `tests/test_ai_jobs_api.py` gets one small sync addition confirming a fresh
    job's HTTP response carries `"metrics": {}` and never a raw `metrics_json`
    key, keeping the existing secret-absence/projection tests' own style.
- Commands and results:
  - `venv\Scripts\python.exe -m ruff check app/services/ai_job_service.py app/core/constants.py app/models/ai_job.py app/services/script_pipeline.py app/services/learning_pipeline.py tests/test_ai_job_service.py tests/test_script_pipeline.py tests/test_learning_pipeline.py tests/test_ai_jobs_api.py` → All checks passed (checked incrementally, file by file, as each was written).
  - `venv\Scripts\python.exe -m pytest tests/test_ai_job_service.py -q` → 60 passed.
  - `venv\Scripts\python.exe -m pytest tests/test_script_pipeline.py -q` → 31 passed (22 pre-existing + 9 new).
  - `venv\Scripts\python.exe -m pytest tests/test_learning_pipeline.py -q` → 24 passed.
  - `venv\Scripts\python.exe -m pytest tests/test_ai_jobs_api.py -q` → 14 passed (12 pre-existing + 2 new).
  - `venv\Scripts\python.exe -m ruff check app tests scripts` (full) → All checks passed.
  - `venv\Scripts\python.exe -m pytest -q` (full suite) → **848 passed**, 0 failed, in 349.07s
    (baseline after 14.1 was 814; net +34 across the four touched test files).
- Deviations: none -- all allowed-file edits stayed within `app/services/ai_job_service.py`,
  `app/services/script_pipeline.py`, `app/services/learning_pipeline.py`,
  `app/models/ai_job.py`, `app/core/constants.py`, and their four test files.
  `app/api/ai_jobs.py` was **not** touched (see "Plan/decisions" above: the
  `AIJobOut` `model_validator` derives `metrics` from `metrics_json` without any
  route change). `app/core/exceptions.py` was not touched (not needed --
  `provider_error_code` only imports from it).
- Revert-and-confirm-failure evidence:
  - Commented out the `repair_count = repair_count + 1` clause in
    `ai_job_service.record_generation_call` and re-ran
    `venv\Scripts\python.exe -m pytest tests/test_ai_job_service.py::test_record_generation_call_increments_repair_count_only_for_is_repair tests/test_script_pipeline.py::test_pipeline_repair_sets_repair_count_and_checkpoint_metrics tests/test_learning_pipeline.py::test_pipeline_repair_sets_repair_count -q`:
    **3 failed** -- all three `assert final_job["repair_count"] == 1` /
    `assert after_repair["repair_count"] == 1` became `assert 0 == 1`, confirming
    the increment (not something else, e.g. the pipeline's own repair-trigger
    logic) is what the test actually depends on. Restored the clause and re-ran
    the same three tests: **3 passed**.
- Commit(s):
  - (pending) -- feat(ai): Task 14.2 job telemetry (record_generation_call,
    provider_error_code, AIJobOut.metrics, section checkpoint metrics_json, both
    pipelines' error-code mapping) + this task card's execution record and
    PHASE-STATE update.
