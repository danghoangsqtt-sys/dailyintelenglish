# Task 18.6 — Cloud model chain + speed tuning (D27, Amendment D)

- **Status:** done (pending PM ACCEPTED)
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** Gate B-9 done (`docs/operations/phase18-gate-b9.md`); owner decision D27
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.6" (Amendment D),
  invariants 31–35

## Allowed files

`app/services/ai/openai_compat_provider.py`, `app/services/ai/router.py`, `app/core/config.py`,
`app/core/constants.py`, `.env.example`, `app/services/settings_service.py`,
`app/api/settings.py`, `app/models/settings.py`, `frontend/pages/settings.html`,
`frontend/static/js/settings.js`, and `app/services/script_pipeline.py` /
`app/services/learning_pipeline.py` **for the malformed-JSON local retry only (item 4)**, plus
the matching tests and `CHANGELOG.md`. **PM review C1/C4:** `app/core/exceptions.py` (one new
class, `ProviderDailyQuotaError`) and `app/services/ai_job_service.py` (one new
`_PROVIDER_ERROR_CODES` mapping entry) are added, for exactly that; `app/api/ai_jobs.py` (health
payload only) is added for `circuit_open_until`. See plan §3 "18.6", which is binding otherwise.
Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

1. Model chain via OpenRouter's native `models: [primary, ...fallbacks]` array; record the model
   that actually answered; editable in Settings.
2. Cloud budget 150 → 75s.
3. A daily-cap 429 opens the primary circuit until `X-RateLimit-Reset`, distinguishable from an
   ordinary rate limit.
4. Malformed JSON from a cloud-served result gets one local retry before the normal repair.
5. Tests: MockTransport only, revert checks on 3 and 4.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**PM review — APPROVED with four changes (C1, C2, C3, C4), folded into this implementation, no
re-approval needed:**
- **C1:** both file questions resolved by adding the files, not working around them.
  `ProviderDailyQuotaError(ProviderRateLimitError)` is defined in `app/core/exceptions.py`
  (no local definition in the provider), and `ai_job_service._PROVIDER_ERROR_CODES` gains
  `ProviderDailyQuotaError: "provider_daily_quota"`.
- **C2:** "cloud-served" is decided by the router, not a hardcoded `"ollama"` string comparison —
  new `AIRouter.is_primary_result(result) -> bool`. See point 4 below for the edge case this
  needed to handle (the LOCAL-mode placeholder where `primary is fallback`).
- **C3:** `CircuitBreaker.open_until` caps the computed remaining-open duration at 26 hours from
  now, guarding against a garbled/far-future `X-RateLimit-Reset`. Tested with a reset far in the
  future.
- **C4:** `/api/ai/health` gains `circuit_open_until` (ISO 8601 UTC timestamp, or `null`); the
  Settings page shows "Cloud paused until HH:MM (free daily limit reached)" whenever it's set.

**Original two file-location questions (resolved by C1 above; kept for context):**

- **Q1 — where `ProviderDailyQuotaError` lives.** It needs to be raised by
  `openai_compat_provider.py` and `isinstance`-checked by `router.py`, both allowed files.
  `app/core/exceptions.py` — where every other `Provider*Error` lives today, a flat one-file
  hierarchy — is **not** in this task's allowed-file list. My plan: define it locally as
  `class ProviderDailyQuotaError(ProviderRateLimitError):` inside `openai_compat_provider.py`
  (which already imports `ProviderRateLimitError`), and have `router.py` import it from there
  (`from app.services.ai.openai_compat_provider import ProviderDailyQuotaError`) instead of from
  `app.core.exceptions`. This is the one place in the whole AI package where a `Provider*Error`
  subclass wouldn't live in the central file — I think it's the right call given the file-scope
  constraint (same footprint discipline as 18.1 C1's `upstream_status` staying out of
  `exceptions.py`), but the alternative is a one-line addition to this task's allowed files
  (`app/core/exceptions.py`, one class) to keep the hierarchy flat. Your call — I'll proceed with
  the local-subclass plan unless you say otherwise.
- **Q2 — `ai_job_service.provider_error_code`'s mapping table won't know about
  `ProviderDailyQuotaError`** (that file isn't in this task's allowed files either). Since the
  mapping is keyed by exact `type(exc)`, not `isinstance`, an unmapped subclass falls through to
  the existing generic `"provider_error"` fallback — safe, just less specific in job
  `error_code`/Gate B evidence than a dedicated `provider_daily_quota` code would be. Not fixing
  this now; flagging it as a known gap for a future task if the PM wants the finer-grained code.

### 1. Model chain (point 1)

New setting `OPENAI_COMPAT_FALLBACK_MODELS: str` (`app/core/config.py`), a comma-separated list,
default `"google/gemma-4-26b-a4b-it:free,dots-studio/dots-3-note-preview:free"` (D27). Stored as
a plain string (matching every other `OPENAI_COMPAT_*` field's type), not a pydantic-settings
`list[str]` (which would need JSON-encoded env values, not a plain CSV) — parsed where needed by
a new small helper, `parse_fallback_models(raw: str) -> list[str]` in `openai_compat_provider.py`
(comma-split, `.strip()` each entry, drop empties), exported alongside the existing
`validate_openai_compat_base_url` helper.

`OpenAICompatProvider.__init__` gains `fallback_models: list[str] | None = None`. In `generate()`:
when `fallback_models` is truthy, the payload sends `"models": [self._model, *self._fallback_models]`
**instead of** `"model"` (Amendment D's own wording) — OpenRouter tries each model server-side,
within the one HTTP call, on rate-limit/downtime. When empty/`None` (the primary-only case,
including every existing test), the payload is unchanged (`"model": self._model`) — fully
backward compatible with Task 18.1's existing MockTransport tests, none of which set
`fallback_models`.

"The model that actually answered" (point 1): `GenerationResult.model` changes from the current
hardcoded `model=self._model` to `model=data.get("model") or self._model` — OpenRouter's response
body reports which model in the chain actually served the request; falling back to `self._model`
keeps every existing test (whose mock responses have no `"model"` key) passing unchanged.

`router.build_ai_router_from_settings()` parses `settings.OPENAI_COMPAT_FALLBACK_MODELS` via
`parse_fallback_models` and passes it to `OpenAICompatProvider(...)`.

**Editable in Settings (D24 pattern):** `set_cloud_settings` gains `fallback_models: list[str] |
None = None` — `None` means "leave unchanged" (same convention as `api_key`), a list (including
`[]`, explicitly "primary only, no chain") replaces it. Validated before any write: each entry
non-empty after `.strip()` and ≤ 200 chars (matching the existing `model` field's own limit),
≤ 5 entries total. Stored as `",".join(cleaned)` under a new `openai_compat_fallback_models`
`app_settings` key (`CLOUD_FALLBACK_MODELS_SETTING`), same table, no new migration.
`get_cloud_settings_status` gains `"cloud_fallback_models": list[str]` (not secret, returned in
full). `load_cloud_settings_from_db` gains the matching load-on-startup branch.
`CloudSettingsUpdate` (`app/models/settings.py`) gains `fallback_models: list[str] | None = None`,
unconstrained at the Pydantic level (same C2 rationale as every other field there — real
validation lives in the service). `PUT /api/settings/cloud` passes `payload.fallback_models`
through.

**Settings page:** one new text input, `#cloud-fallback-models`, comma-separated (matching how
the base URL/model fields already work), placed right after the `model` field in the existing
Cloud Provider form/Save button — not a new form, a new field on the existing one.
`settings.js` splits the input on comma into a list client-side before sending (mirrors the
service's own list-shaped parameter), and joins the loaded list back with `", "` for display.

**`test_cloud_connection` deliberately does not use the chain** — it tests one specific
base_url/model/key combination the user is currently editing, not "does the whole chain work";
scope stays exactly as 18.3 built it, no change there.

### 2. Cloud budget 150 → 75s (point 2)

`app/core/constants.py`: `AI_CLOUD_DEADLINE_SECONDS = 150.0` → `75.0`, comment updated (Dots3's
70s smoke-probe latency vs. B-9's 7 timeouts each burning the full 150s). `app/core/config.py`'s
`AI_CLOUD_DEADLINE_SECONDS` field already mirrors this constant as its default
(`_AI_CLOUD_DEADLINE_SECONDS_DEFAULT`) — one source of truth, only `constants.py` changes.

Noted, not acted on: with the model chain (point 1), OpenRouter may try up to 3 models
server-side inside one HTTP call, all within this one 75s budget. Amendment D's own justification
(Dots3 at 70s) already accepts this narrowly for a 2-model chain; a 3rd slow fallback could still
exceed it. This is the plan's own accepted trade-off, not a new risk introduced here — flagging
it for visibility, not proposing a change.

### 3. Daily-cap circuit (point 3)

**New exception (C1):** `class ProviderDailyQuotaError(ProviderRateLimitError):` in
`app/core/exceptions.py`, alongside every other `Provider*Error`, keeping that hierarchy flat as
it's always been. `openai_compat_provider.py` imports it from there, same as its siblings.
Carries a `reset_at_epoch_seconds: float` instance attribute (set the same way `upstream_status`
is — a plain attribute, not a constructor field, consistent with `_raise`'s existing pattern).
`ai_job_service._PROVIDER_ERROR_CODES` gains `ProviderDailyQuotaError: "provider_daily_quota"` —
one dict entry, right after the existing `ProviderRateLimitError` one for readability; Gate B
evidence and job `error_code` can now distinguish a daily-cap failure from an ordinary rate
limit, instead of both falling through to the generic `"provider_error"`.

**Detection**, inside `OpenAICompatProvider.generate()`'s existing `if status == 429:` branch
(the real captured shape is a plain HTTP 429, not the 200-wrapped-error case a few lines above):
parse the body once, check `error.metadata.limit_source == "openrouter_free_tier_daily"` OR
`"free-models-per-day" in error.message` (either alone is sufficient — the metadata check is the
precise signal, the message substring is a backstop in case a future response omits metadata).
If daily-quota: read `X-RateLimit-Reset` (epoch **milliseconds** per Amendment D) from the
response headers, convert to seconds. If the header is missing or unparseable, compute the next
UTC midnight directly in the provider (`datetime.now(timezone.utc)` + 1 day, truncated to
00:00:00) — so the exception **always** carries a valid epoch, the router/circuit side never
handles a `None`. Every other 429 (no daily-quota signal) raises the existing plain
`ProviderRateLimitError`, unchanged.

**No retry-with-backoff on a daily-cap 429** (pointless — the quota will not refill within any
retry window, and B-9 showed each 429 round-trip still costs a request against the same
exhausted counter). `AIRouter._attempt`'s except-clause order gains one new clause, placed
**before** the existing `except _TRANSIENT_ERRORS as exc:` (Python matches in source order, and
`ProviderDailyQuotaError` is a subtype of `ProviderRateLimitError`, which IS in
`_TRANSIENT_ERRORS` — without this it would silently get caught by the backoff branch instead):
```python
except ProviderDailyQuotaError:
    raise  # no backoff -- generate()'s cloud_first branch opens the circuit until reset instead
except _TRANSIENT_ERRORS as exc:
    ...
```

**Opening the circuit until a wall-clock deadline, coexisting with the shared app-lifetime
`CircuitBreaker`** (the PM's explicit question): it's the exact **same** `CircuitBreaker`
instance and the exact same `opened_until` field `is_open()` already checks — a third way to set
it, alongside `record_failure()`'s threshold-based open and `open_immediately()`'s fixed-cooldown
open, not a parallel circuit. New method (C3 cap included):
```python
_MAX_OPEN_UNTIL_SECONDS = 26 * 3600.0  # C3: guards a garbled/far-future X-RateLimit-Reset

def open_until(self, reset_at_epoch_seconds: float) -> None:
    self.consecutive_failures = self.failure_threshold
    remaining = max(0.0, reset_at_epoch_seconds - time.time())
    remaining = min(remaining, self._MAX_OPEN_UNTIL_SECONDS)
    self.opened_until = time.monotonic() + remaining
```
26h (not 24h) covers a `reset_at_epoch_seconds` that's correctly the next UTC midnight but read
close to just-past the *previous* midnight (up to ~24h out) plus slack for clock skew/latency,
while still capping a badly garbled header (e.g. a stray extra digit) from opening the circuit
for months. Tested with a reset epoch far in the future (e.g. +1e9 seconds) asserting the
resulting open duration is capped at exactly 26h, not the uncapped value.

`opened_until`/`is_open()` compare against `time.monotonic()` (a monotonic clock unrelated to
wall-clock epoch) everywhere else in this class — `open_until` is the one place that converts a
wall-clock deadline (`X-RateLimit-Reset`, `time.time()`) into a monotonic-clock offset, computed
**once**, at call time. Nothing else in `CircuitBreaker`/`is_open()` changes. A reset already in
the past (clock skew, a stale header) opens for `max(0.0, ...)` = 0 seconds — closes essentially
immediately next check, never negative/stuck-open.

`AIRouter.generate()`'s cloud_first `except ProviderError as exc:` block gains one branch, ahead
of the existing `ProviderAuthError` check:
```python
if isinstance(exc, ProviderDailyQuotaError):
    self._circuit.open_until(exc.reset_at_epoch_seconds)
elif isinstance(exc, ProviderAuthError):
    self._circuit.open_immediately()
else:
    self._circuit.record_failure()
```
`result.fallback_reason = type(exc).__name__` (unchanged code) now naturally records
`"ProviderDailyQuotaError"`, distinguishable from `"ProviderRateLimitError"` in the fallback-rate
readout's reason breakdown (Task 18.4) with no changes needed there.

### 4. Malformed cloud JSON → one local retry (point 4)

**How this plugs into the call wrapper without touching anything else** (the PM's explicit
question): the retry lives entirely inside each pipeline's existing `_call_router` helper — the
one function every generation/repair call in both files already goes through. Each call site
(`_generate_outline`, `_generate_section`, `_repair_section` in `script_pipeline.py`;
`_generate_pack`, `_repair_pack` in `learning_pipeline.py`) already does its own
`parse_and_validate(result.text, <its own adapter>)` right after calling `_call_router` — the fix
is a **new optional `adapter` parameter on `_call_router` itself**, so the wrapper can do a
look-ahead validation and retry *before* returning, while every call site's own existing
post-call `parse_and_validate(...)` (with its own adapter, its own error handling — `_generate_section`
returns `([], [str(exc)], [])` on failure, `_generate_outline` lets it propagate, learning's two
call sites let it propagate) stays **completely unchanged**. The only edit at each of the 5 call
sites is adding one kwarg to their existing `_call_router(...)` call
(`adapter=_OUTLINE_ADAPTER` / `adapter=_SECTION_LINES_WIRE_ADAPTER` / `adapter=_PACK_ADAPTER`) —
nothing about prompts, repair loops, structural/budget validation, or orchestration changes.

`_call_router`'s new body (both files, same shape — they already duplicate this helper, per
Amendment A #4):
```python
async def _call_router(db, job_id, router, request, *, section_index, is_repair, adapter=None):
    try:
        result = await router.generate(request)
    except ProviderError as exc:
        # unchanged: record outcome="error", re-raise
        ...

    if adapter is not None and router.is_primary_result(result):
        try:
            parse_and_validate(result.text, adapter)
        except SchemaValidationError:
            try:
                result = await router.generate_on_fallback(request)
            except ProviderError as exc:
                # record outcome="error" for this retry attempt, re-raise -- same
                # shape as the block above, so a local-provider failure during the
                # retry still fails the job with a specific error_code
                ...
            result.fallback_used = True
            result.fallback_reason = "SchemaValidationError"

    # unchanged: record outcome="ok" for `result`, return it
    ...
```
**C2:** "cloud-served" is decided by a new `AIRouter.is_primary_result(result)`, not a hardcoded
`result.provider != "ollama"` string comparison — survives a future provider rename. It's not
just `result.provider == self._primary.name` though: `build_ai_router_from_settings()` sets
`primary: Provider = fallback` as a placeholder in `AIMode.LOCAL` mode ("never called when
effective_mode is LOCAL", per its own comment) — so in that mode `self._primary` and
`self._fallback` are literally the same object, and a bare name comparison would wrongly return
`True` for an ordinary local-mode result (nothing to retry against, and `self._mode` is already
known and cheap to check):
```python
def is_primary_result(self, result: GenerationResult) -> bool:
    """True only when `result` was genuinely served by a distinct primary
    provider -- excludes AIMode.LOCAL, where `primary` is a placeholder equal
    to `fallback` (Task 18.6 C2)."""
    return self._mode is not AIMode.LOCAL and result.provider == self._primary.name
```
Exactly **one** telemetry call is recorded either way (never two): if the retry fires, the
recorded call is the retried (local) result, pre-marked `fallback_used=True,
fallback_reason="SchemaValidationError"` — the same shape the router's own internal
primary-failure fallback already produces, so nothing downstream (Task 18.4's aggregates, Gate
evidence) needs a new code path to recognize it. The pre-check re-parses `result.text` with the
same `adapter`; the caller's own unchanged post-call `parse_and_validate` call parses it a second
time on the same (now-good) text — cheap, deterministic, and avoids `_call_router` needing to
know each caller's actual return type just to hand back an already-parsed value.

**New `AIRouter` method**, `router.py`:
```python
async def generate_on_fallback(self, request: GenerationRequest) -> GenerationResult:
    """Force exactly one call on the local fallback, bypassing the primary/circuit
    entirely. Reuses _run_with_budget/_attempt unchanged, so it gets the same
    per-call retry/backoff policy any other fallback-phase call gets."""
    return await self._run_with_budget(self._fallback, request, request.deadline_seconds)
```
Deliberately does **not** touch `self._circuit` — a malformed-JSON content failure says nothing
about the primary provider's *health* (it answered, on time, just with unparseable content), so
it must never count toward the circuit's failure threshold the way an infra error does.

### 6. Health + Settings: `circuit_open_until` (C4)

`CircuitBreaker` gains `opened_until_epoch_seconds(self) -> float | None` — `None` when not
currently open, else the wall-clock equivalent of the monotonic `opened_until` field, computed at
call time: `time.time() + (self.opened_until - time.monotonic())` (both clocks read "now"
together at the moment of the call, so the delta is accurate then; this is for external
reporting only — `is_open()` itself is untouched and never uses this). Applies whenever the
circuit is open for *any* reason (daily quota, ordinary failure threshold, or an
`open_immediately()` auth-error trip), not only the daily-quota case — `circuit_open_until` is a
general "when does this reopen" readout, same as `circuit_open` (Task 18.3) already is a general
"is it open" one.

`app/api/ai_jobs.py`'s `ai_health()` (added to allowed files for this) formats it to ISO 8601 UTC
via `datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()` and adds `"circuit_open_until"`
to the payload (`None` stays `null`). Additive; every existing health field unchanged.

Settings page: `settings.js`'s existing `renderFallbackRate`/`loadFallbackRate` (Task 18.4,
already fetches `/api/ai/health`) gains a sibling render using the same already-fetched `health`
object — no second fetch. New `#circuit-status` line: when `circuit_open_until` is set, shows
"Cloud paused until HH:MM (free daily limit reached)" (local time, parsed from the ISO string);
empty/hidden otherwise. Matches the PM's literal wording — shown whenever the field is set,
without trying to disambiguate the open reason in the UI text (that would need a separate reason
field, not requested).

### 5. Tests (point 5)

MockTransport only throughout (matches Task 18.1's existing pattern in
`tests/test_openai_compat_provider.py`); the N1 session-wide cloud-config neutralization
(`tests/conftest.py`) stays in force and untouched.
- **Model chain:** a mock handler asserting the outgoing request body has `"models": [primary,
  *fallbacks]` and no `"model"` key when `fallback_models` is set; `GenerationResult.model` reads
  the mock response's own `"model"` field when present, falls back to the configured primary
  when absent (locks in backward compatibility with every existing 18.1 test). Settings CRUD:
  `set_cloud_settings` validation (empty entry, > 200 chars, > 5 entries, each rejected with
  nothing written), `None` leaves the stored chain unchanged, `[]` clears it to "primary only."
- **Daily-cap circuit:** a MockTransport response built from Amendment D's real captured shape
  (429, `error.message` containing `"free-models-per-day"`, `error.metadata.limit_source ==
  "openrouter_free_tier_daily"`, `X-RateLimit-Reset` header) with a synthetic reset epoch and a
  synthetic user id (never the real captured body verbatim) — asserts `ProviderDailyQuotaError`
  with the right `reset_at_epoch_seconds`, and a dedicated test proving it is **not**
  backoff-retried (exactly one HTTP call observed by the mock handler, where an ordinary
  `ProviderRateLimitError` in the same harness would retry up to `AI_TRANSIENT_MAX_ATTEMPTS`).
  At the router level: `CircuitBreaker.is_open()` true immediately after, `is_open()` false once
  `time.monotonic()` is advanced past the equivalent offset (monkeypatching `time.monotonic`/
  `time.time` together, keeping their relative offset consistent). A plain 429 with no
  daily-quota signal still raises ordinary `ProviderRateLimitError` and still gets the existing
  backoff/retry treatment, unchanged (regression guard). `ai_job_service.provider_error_code`
  maps `ProviderDailyQuotaError` to `"provider_daily_quota"` (C1).
- **C3:** `open_until` with a reset epoch far in the future (e.g. `time.time() + 1e9`) asserts the
  resulting `opened_until` reflects the capped 26h, not the uncapped multi-year value (compare
  against `time.monotonic() + 26 * 3600`, with a small tolerance for test execution time).
- **C2:** `is_primary_result` returns `True` for a genuine primary-served result in `cloud`/
  `cloud_first` mode, and `False` for a fallback-served result *and* for any result when the
  router's mode is `local` (the `primary is fallback` placeholder case) — the exact edge case
  that ruled out a bare name comparison.
- **Malformed JSON local retry:** a router with a primary mock that returns malformed JSON and a
  fallback (local) mock that returns valid JSON — `_call_router(..., adapter=...)` returns the
  retried, `fallback_used=True`/`fallback_reason="SchemaValidationError"` result, with exactly
  one telemetry call recorded (not two). A second case where the retry's own local call also
  fails (`ProviderError`) — the job fails with that error's specific code, telemetry shows one
  `outcome="error"` record for the retry attempt. A `local`-mode case confirms no retry is
  attempted at all (`is_primary_result` false, nothing to retry against).
- **C4:** `/api/ai/health` includes `circuit_open_until` as `null` by default, and as an ISO
  string once the circuit is forced open (whitebox, same `_ai_circuit.open_immediately()`
  pattern Task 18.3's health tests already use).
- **Revert checks (required on items 3 and 4):** comment out the
  `except ProviderDailyQuotaError: raise` clause → confirm the daily-cap test starts retrying
  with backoff (or a timing/call-count assertion fails); restore. Comment out the `adapter`
  branch in `_call_router` → confirm the malformed-JSON retry test fails (no retry happens, the
  malformed result is returned as-is); restore.

## Verification (required)

Full suite, `ruff`, revert-and-confirm-failure on items 3 and 4 as above, real DB untouched.

## Evidence

- Design commits `e72aec3` (initial) + `d1a81b1`/`b50e3a5` (APPROVED with C1/C2/C3/C4), this
  implementation commit folds all four in per "no re-approval needed."
- **Code:**
  - `app/core/exceptions.py` (C1): new `ProviderDailyQuotaError(ProviderRateLimitError)`,
    alongside every other `Provider*Error`.
  - `app/services/ai_job_service.py` (C1): `_PROVIDER_ERROR_CODES` gains
    `ProviderDailyQuotaError: "provider_daily_quota"`.
  - `app/services/ai/openai_compat_provider.py`: `parse_fallback_models(raw)` helper;
    `__init__` gains `fallback_models`; `generate()` sends `models: [model, *fallback_models]`
    instead of `model` when non-empty; `GenerationResult.model` reads the response's own
    `"model"` field, falling back to the configured primary when absent; new
    `_daily_quota_reset_epoch_seconds(response)` detects OpenRouter's real captured daily-cap
    shape (`error.metadata.limit_source == "openrouter_free_tier_daily"` or a message substring
    backstop) and raises `ProviderDailyQuotaError` with `reset_at_epoch_seconds` (from
    `X-RateLimit-Reset`, or the next UTC midnight if the header is missing/unparseable).
  - `app/services/ai/router.py`: `CircuitBreaker.open_until(reset_at_epoch_seconds)` (C3: capped
    at 26h) and `opened_until_epoch_seconds()` (C4, wall-clock readout) -- same `opened_until`
    field `is_open()` already uses. `_attempt` gains a `ProviderDailyQuotaError` except-clause
    ahead of `_TRANSIENT_ERRORS` (no backoff retry). `generate()`'s cloud_first branch opens the
    circuit via `open_until` on a daily-quota error. New `AIRouter.is_primary_result(result)`
    (C2: excludes `AIMode.LOCAL`'s `primary is fallback` placeholder) and
    `AIRouter.generate_on_fallback(request)` (forces local, never touches the circuit).
    `build_ai_router_from_settings` parses and passes `OPENAI_COMPAT_FALLBACK_MODELS`.
  - `app/core/constants.py`: `AI_CLOUD_DEADLINE_SECONDS` 150.0 → 75.0, comment updated.
  - `app/core/config.py`/`.env.example`: new `OPENAI_COMPAT_FALLBACK_MODELS` setting (default
    Gemma 4 → Dots3), `.env.example`'s `AI_CLOUD_DEADLINE_SECONDS` matches the new default.
  - `app/services/settings_service.py`: `CLOUD_FALLBACK_MODELS_SETTING`; `get_cloud_settings_
    status` gains `cloud_fallback_models`; `set_cloud_settings` gains a `fallback_models`
    parameter (`None` = unchanged, `[]` = explicit clear, validated ≤5 entries/≤200 chars each,
    nothing written on rejection); `load_cloud_settings_from_db` uses `is not None` (not
    truthiness) for this one field so an explicitly-cleared empty chain survives a restart.
  - `app/models/settings.py`: `CloudSettingsUpdate.fallback_models` (unconstrained at the
    Pydantic level, real validation in the service).
  - `app/api/settings.py`: `PUT /api/settings/cloud` passes `fallback_models` through.
  - `app/api/ai_jobs.py` (C4): `ai_health()` adds `circuit_open_until` (ISO 8601 UTC or `null`),
    additive, every existing field unchanged.
  - `frontend/pages/settings.html`/`settings.js`: new `#cloud-fallback-models` input (comma
    round-trip) on the existing Cloud Provider form; new `#circuit-status` line reusing the
    already-fetched health object from Task 18.4's `loadFallbackRate`/`renderFallbackRate` --
    "Cloud paused until HH:MM (free daily limit reached)" whenever `circuit_open_until` is set.
  - `app/services/script_pipeline.py`/`learning_pipeline.py` (item 4 only): `_call_router` gains
    an optional `adapter` parameter -- a cloud-served result (`router.is_primary_result`) that
    fails validation gets one local retry (`router.generate_on_fallback`) before being recorded,
    marked `fallback_used=True, fallback_reason="SchemaValidationError"`. Every call site
    (`_generate_outline`, `_generate_section`, `_repair_section`, `_generate_pack`,
    `_repair_pack`) changed by exactly one added kwarg; nothing else in either file touched.
- **Tests (52 new, 1112 total):**
  - `tests/test_openai_compat_provider.py` (+15): model chain request shape (`models` array vs.
    plain `model`, backward-compat default), the answering model recorded vs. falling back to
    configured, daily-cap detection (real captured shape with a synthetic reset/user id, header
    parsing, next-midnight fallback, message-substring backstop, and a plain-429 regression
    guard), `parse_fallback_models`.
  - `tests/test_ai_router.py` (+18): `build_ai_router_from_settings` reads the fallback chain;
    `CircuitBreaker.open_until`/`opened_until_epoch_seconds` (wall-clock conversion, the 26h cap,
    past-reset immediate close); router-level daily-quota handling (no backoff, circuit opens and
    is respected on the next call, a plain `ProviderRateLimitError` regression guard still
    retries); `is_primary_result` (true/false/LOCAL-placeholder edge case); `generate_on_fallback`
    (calls fallback directly, ignores an open circuit, never touches the circuit).
  - `tests/test_settings_service.py` (+11) / `tests/test_settings_api.py` (+4): fallback-models
    CRUD, validation, `None`-unchanged/`[]`-clears semantics, the load-from-db `is not None` fix.
  - `tests/test_ai_health_api.py` (+2) / allowlist test extended: `circuit_open_until` null by
    default and as ISO when the circuit is forced open.
  - `tests/test_settings_browser.py` (+3): fallback-models field round-trip, circuit-status
    hidden by default, circuit-status shown with the exact wording when set.
  - `tests/test_ai_job_service.py` (+1 parametrize case): `ProviderDailyQuotaError` maps to
    `"provider_daily_quota"`.
  - `tests/test_script_pipeline.py` (+3) / `tests/test_learning_pipeline.py` (+2): the malformed-
    JSON local retry (one telemetry call, correct `fallback_used`/`fallback_reason`), the retry's
    own failure propagating with its own error record, and the LOCAL-mode no-retry case.
- **Revert-and-confirm-failure:**
  - Item 3: commented out the `except ProviderDailyQuotaError: raise` clause in `_attempt` →
    both daily-quota router tests failed (`RuntimeError: FakeProvider('openai_compat') has no
    more scripted outcomes` -- proving it fell into the backoff-retry loop instead); restored,
    46/46 router tests passed again.
  - Item 4: disabled the `adapter`/`is_primary_result` branch in `script_pipeline._call_router` →
    both malformed-JSON-retry tests failed (`assert 'openai_compat' == 'ollama'` and "DID NOT
    RAISE ProviderUnavailableError" -- proving no retry was attempted); restored, 99/99 script
    pipeline tests passed again.
- **Full suite:** **1112 passed** (1060 baseline + 52 new). `ruff check .` → all checks passed.
  Real DB untouched throughout (the conftest guard never tripped).
