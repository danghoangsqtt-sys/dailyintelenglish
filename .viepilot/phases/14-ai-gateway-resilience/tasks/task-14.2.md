# Task 14.2 — Job Telemetry: Repair, Fallback, Provider, Attempts, Error Codes

- **Status:** pending
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
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
