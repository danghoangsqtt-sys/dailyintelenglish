# Task 14.1 — Bounded Exponential Backoff for Transient Provider Errors

- **Status:** pending
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** none (first task of the phase)
- **Controlling detail:** plan §4.1, §5, §6 Task 14.1; ADR-001 amendment A1

## Objective

Make `AIRouter` absorb ordinary transient provider errors (HTTP 503, 429, timeout) by
waiting 1 s → 2 s → 4 s between up to four attempts against the **same** model, entirely
inside the caller's existing 120 s deadline — without re-introducing any multi-model
cascade and without touching provider adapters (they stay single-attempt).

## Measured problem (do not re-derive)

`grep -rn "sleep" app/services/ai/` is empty. `_attempt_with_one_retry` catches a 503 and
re-fires within milliseconds, then the job dies (`handler_exception`,
`ProviderUnavailableError: Gemini is temporarily overloaded (HTTP 503)`). Gemini
diagnostic: 0/2 jobs, dead after 9 s and 24 s; direct probe `200 → 503 → 200`.

## Allowed files

`app/services/ai/router.py`, `app/services/ai/contracts.py`,
`app/core/constants.py`, `app/core/exceptions.py` (only for the optional
`retry_after_seconds` attribute on `ProviderRateLimitError`),
`tests/test_ai_router.py`, `tests/test_ai_contracts.py`, `tests/test_ai_logging.py`,
`tests/test_ai_providers.py` (only if the retry-after hint is implemented).

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

| Error class | Members | Policy |
|---|---|---|
| Transient | `ProviderUnavailableError`, `ProviderRateLimitError`, `ProviderTimeoutError` | up to `AI_TRANSIENT_MAX_ATTEMPTS = 4` attempts; sleep `AI_TRANSIENT_BACKOFF_BASE_SECONDS × 2^(n−1)` capped at `AI_TRANSIENT_BACKOFF_MAX_SECONDS = 4.0` before attempts 2/3/4 → `[1.0, 2.0, 4.0]` |
| Content | `ProviderInvalidResponseError`, `SchemaValidationError` | unchanged: exactly one immediate retry, no sleep |
| Non-retryable | `ProviderAuthError`, other `ProviderError` | no retry |

- Record `deadline_at = time.monotonic() + request.deadline_seconds` on entry to
  `generate()`. Before each sleep: `remaining = deadline_at − now`; if
  `remaining < delay + AI_BACKOFF_MIN_REMAINING_SECONDS (5.0)` → stop, raise the last
  error. Keep the outer `asyncio.wait_for` as-is.
- Hybrid route shape unchanged: local route (≤ 4 attempts) → `record_failure()` once →
  Gemini route (≤ 4 attempts) → `fallback_used = True`. Circuit-open path unchanged.
- `from asyncio import sleep` at module level; call `await sleep(delay)` so tests patch
  `app.services.ai.router.sleep` (never the global `asyncio.sleep`).
- `GenerationResult` gains `attempts: int = 1`, `backoff_seconds: float = 0.0`,
  `transient_errors: list[str] = []` (exception class names only).
- Log lines (safe fields only): `ai_router_backoff provider= purpose= attempt=
  delay_seconds= error=` per sleep; `ai_router_exhausted provider= purpose= attempts=
  backoff_seconds=` when a route gives up.
- Constants added to `app/core/constants.py` with a comment pointing at this task:
  `AI_TRANSIENT_MAX_ATTEMPTS`, `AI_TRANSIENT_BACKOFF_BASE_SECONDS`,
  `AI_TRANSIENT_BACKOFF_MAX_SECONDS`, `AI_BACKOFF_MIN_REMAINING_SECONDS`. Legacy
  `GEMINI_MAX_RETRIES`/`GEMINI_RETRY_BASE_DELAY` stay untouched (later cleanup).
- Optional: honour `retry_after_seconds` as `max(hint, delay)`, still deadline-capped.

## Explicitly forbidden

- Any use of `GEMINI_MODEL_FALLBACKS` or a second model id in routing.
- Retry loops inside `OllamaProvider`/`GeminiProvider`.
- Changing `AI_REQUEST_DEADLINE_SECONDS` (if backoff cannot fit, stop and report).
- A backoff parameter that exists but is never awaited.

## Verification (all must be in the diff)

1. Delay sequence: FakeProvider raising three `ProviderUnavailableError` then succeeding
   → patched sleep recorded `[1.0, 2.0, 4.0]`; result `attempts == 4`,
   `backoff_seconds == 7.0`, `transient_errors == ["ProviderUnavailableError"] * 3`.
2. Exhaustion: four transient errors → the fourth is raised; three sleeps; one
   `ai_router_exhausted` line captured.
3. Deadline: `deadline_seconds = 6.0`, first attempt raises transient, second raises
   transient → the router must not sleep 2.0 s when remaining < 7.0; it raises without
   that sleep (assert recorded sleeps `== [1.0]`).
4. Content class: `SchemaValidationError` → one immediate retry, zero sleeps.
5. Auth: `ProviderAuthError` → zero retries, zero sleeps.
6. Hybrid: local raises transient ×4 → three sleeps, one `record_failure`, Gemini
   succeeds, `fallback_used is True`.
7. Existing tests updated for the new attempt counts; "no nested retries" tests still
   prove providers are called exactly the expected number of times.
8. `tests/test_ai_logging.py`: new log lines contain no prompt text and no key.
9. Revert-and-confirm-failure: comment out the `await sleep(...)` → test 1 fails; restore
   → passes. Record the output in this card.
10. `venv\Scripts\python.exe -m ruff check app tests scripts` clean;
    `venv\Scripts\python.exe -m pytest -q` green (baseline 808).

## Rollback

`AI_TRANSIENT_MAX_ATTEMPTS = 2`, `AI_TRANSIENT_BACKOFF_BASE_SECONDS = 0.0` reproduces
Task 13.7 behaviour without a code revert.

## Execution record (Coder fills in)

- Plan/decisions before code:
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
