# Task 14.1 — Bounded Exponential Backoff for Transient Provider Errors

- **Status:** blocked (awaiting PM amendment -- see Deviations)
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
  - Implement §4.1's two-tier retry directly in `AIRouter`: a single internal
    retry-loop method handles both error classes by checking, per caught
    exception, which tuple it belongs to (`_TRANSIENT_ERRORS` vs
    `_CONTENT_RETRY_ERRORS`) against a shared `attempt` counter — transient
    errors may continue while `attempt < AI_TRANSIENT_MAX_ATTEMPTS` (sleeping
    the capped exponential delay first, subject to the deadline check);
    content errors may continue only while `attempt < 2` (no sleep);
    anything else (incl. `ProviderAuthError`) is not caught and propagates
    immediately. This reproduces the plan's table exactly for pure sequences
    and degrades safely for a mixed sequence (no test requires a specific
    mixed-sequence behaviour, so the simplest rule consistent with both rows
    is used, documented here rather than silently decided in code).
  - `deadline_at = time.monotonic() + request.deadline_seconds` is computed
    once in `generate()` and threaded through `_route`/the retry method, so
    the existing outer `asyncio.wait_for` stays the last-resort guard and the
    inner deadline check (`remaining < delay + AI_BACKOFF_MIN_REMAINING_SECONDS`)
    is what actually prevents starting a sleep the deadline can't afford.
  - `_attempt_with_one_retry` is renamed to `_attempt` (private, no external
    caller/test references it by name) since "one retry" no longer describes
    its behaviour for the transient class.
  - Optional `retry_after_seconds` hint on `ProviderRateLimitError` is **not**
    implemented — the plan marks it optional/not required for acceptance, and
    skipping it keeps `app/core/exceptions.py` and `tests/test_ai_providers.py`
    untouched, which is the smaller diff for the same required behaviour.
  - Existing tests in `test_ai_router.py`, `test_ai_logging.py`, and
    `test_ai_providers.py` (the "no nested retries" ones) that script exactly
    2 `ProviderUnavailableError` outcomes to exhaust the old 1-retry policy
    need updating: either 4 scripted outcomes to reach real exhaustion under
    the new policy, or an assertion change if only 2 outcomes are still
    correct for the scenario being tested (e.g. circuit-breaker streak
    accounting, which cares about failure/success shape, not the literal
    retry count). Any test that would now really sleep gets a local
    `monkeypatch.setattr("app.services.ai.router.sleep", ...)` no-op/recorder
    so the suite stays fast and deterministic.
- Commands and results:
  - `venv\Scripts\python.exe -m ruff check app/services/ai/router.py app/services/ai/contracts.py app/core/constants.py tests/test_ai_router.py tests/test_ai_logging.py tests/test_ai_contracts.py` → All checks passed.
  - `venv\Scripts\python.exe -m ruff check app tests scripts` (full) → All checks passed.
  - `venv\Scripts\python.exe -m pytest tests/test_ai_router.py tests/test_ai_logging.py tests/test_ai_contracts.py -q` → 30 passed.
  - `venv\Scripts\python.exe -m pytest -q` (full suite) → **4 failed, 810 passed** in 451.53s.
    Failures, all outside this task's allowed files:
    - `tests/test_learning_service.py::test_generate_learning_pack_wraps_provider_error`
    - `tests/test_script_service.py::test_generate_script_wraps_provider_error_as_script_generation_error`
    - `tests/test_script_service.py::test_regenerate_line_wraps_provider_error_as_script_generation_error`
    - `tests/test_youtube_service.py::test_generate_package_wraps_provider_error`
- Deviations:
  - **BLOCKED -- stop condition per plan §6 Task 14.1 ("Anything else → stop and ask
    the PM to amend the plan") and §"Work packages" ("A newly discovered required
    file pauses that task ... Coder reports; PM amends; Coder resumes").**
  - Root cause (not a router bug): all 4 failing tests script exactly 2
    `ProviderUnavailableError` outcomes to exercise the pre-14.1 "exhausts after 1
    retry (2 total attempts)" policy -- e.g.
    `tests/test_script_service.py:104-106`:
    `router = _gateway_router(AIMode.GEMINI, [ProviderUnavailableError("down"), ProviderUnavailableError("still down")])`.
    Under 14.1's `AI_TRANSIENT_MAX_ATTEMPTS = 4`, the router now makes a 3rd call,
    the `FakeProvider` runs out of scripted outcomes, and it raises
    `RuntimeError("FakeProvider('fake-gemini') has no more scripted outcomes")`
    instead of the `ProviderUnavailableError` these tests expect to see wrapped
    into `ScriptGenerationError`/`LearningGenerationError`/`YouTubePackageGenerationError`.
    This is the exact same mechanical fix already applied in this task's own
    `tests/test_ai_router.py` and `tests/test_ai_logging.py` (script 4 outcomes
    instead of 2, and patch `app.services.ai.router.sleep` to a no-op so the test
    doesn't really wait out 1s+2s+4s=7s of backoff) -- it is not a design question,
    just a file outside this task's allowed list
    (`app/services/ai/router.py`, `app/services/ai/contracts.py`,
    `app/core/constants.py`, `app/core/exceptions.py`, `tests/test_ai_router.py`,
    `tests/test_ai_contracts.py`, `tests/test_ai_logging.py`,
    `tests/test_ai_providers.py`).
  - Requested PM amendment: add `tests/test_learning_service.py`,
    `tests/test_script_service.py`, `tests/test_youtube_service.py` to Task 14.1's
    allowed files (or confirm the Coder should wait for a separate PM-authored
    amendment task), so the Coder can apply the same 2→4-outcome +
    sleep-patch fix there and get the full suite back to green.
  - Implementation itself (router.py/contracts.py/constants.py) is complete and
    its own tests (`test_ai_router.py`, `test_ai_logging.py`, `test_ai_contracts.py`,
    30 tests) are green; the block is scoped exactly to these 4 pre-existing tests
    in other services' test files.
- Revert-and-confirm-failure evidence:
  - Commented out `await sleep(delay)` in `app/services/ai/router.py` (replaced
    with a comment, `backoff_seconds` still accumulated) and re-ran
    `venv\Scripts\python.exe -m pytest tests/test_ai_router.py::test_delay_sequence_is_one_two_four_on_repeated_transient_errors -q`:
    **1 failed** -- `assert sleep_calls == [1.0, 2.0, 4.0]` became
    `assert [] == [1.0, 2.0, 4.0]` (captured log still showed the three
    `ai_router_backoff` lines, confirming the delay computation ran but the
    actual wait was the thing removed). Restored `await sleep(delay)` and re-ran
    `venv\Scripts\python.exe -m pytest tests/test_ai_router.py -q`: **17 passed**.
- Commit(s): (pending -- not committed while blocked; PM amendment needed first)
