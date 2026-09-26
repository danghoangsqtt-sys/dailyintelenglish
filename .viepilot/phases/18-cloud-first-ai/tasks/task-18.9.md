# Task 18.9 — Vendor-aware requests + chain order (D30, Amendment G)

- **Status:** not started
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** Gate B-10 FAIL (`docs/operations/phase18-gate-b10.md`); owner decision D30
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.9" (Amendment G)

## Allowed files

`app/services/ai/openai_compat_provider.py`, `app/services/ai/router.py`,
`app/core/exceptions.py`, `app/core/config.py`, `app/core/constants.py`, `.env.example`,
`app/services/ai_job_service.py` (error-code mapping only), the matching tests, a new opt-in
`scripts/live_provider_contract_check.py`, and `CHANGELOG.md`. See plan §3 "18.9", binding.

## Required behaviour (summary; the plan is binding)

1. Vendor-aware request body: `reasoning`/`models` array OpenRouter-only; Gemini/generic get
   plain fields. Contract test on the exact key set per vendor.
2. HTTP 400/`INVALID_ARGUMENT` → new non-transient `ProviderRequestRejectedError`: no retry,
   that entry's circuit opens immediately, mapped error code.
3. Fallback-reason label: `all_cloud_circuits_open` vs `no_cloud_provider_configured`.
4. Default order (D30): `gemini,openrouter`.
5. Opt-in `scripts/live_provider_contract_check.py`, never collected by pytest, PM-run only.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**Root cause, restated precisely (so the fix targets the actual bug):**
`OpenAICompatProvider.generate()` unconditionally sent `reasoning: {"exclude": true}` (and, when
a fallback chain was configured, OpenRouter's `models` array) to every vendor, including Gemini.
Gemini's OpenAI-compat endpoint rejects any unknown field with HTTP 400. That 400 fell through
to `generate()`'s final catch-all, which raised `ProviderInvalidResponseError` — a *content*
error in the router's classification, so `_attempt` gave it one immediate retry before the
entry's circuit ever got a chance to open. Two wasted calls per Gemini request, every time.

### 1. Vendor-aware payload (point 1)

`generate()`'s payload construction:
```python
payload: dict[str, object] = {"messages": [{"role": "user", "content": request.prompt}]}
if self._vendor == "openrouter":
    payload["reasoning"] = {"exclude": True}
    if self._fallback_models:
        payload["models"] = [self._model, *self._fallback_models]
    else:
        payload["model"] = self._model
else:
    payload["model"] = self._model
if request.temperature is not None:
    payload["temperature"] = request.temperature
```
Gated on `self._vendor`, not on whether `fallback_models` happens to be empty — defensive: even
if a future caller mistakenly passed `fallback_models` to a Gemini/generic entry, the `models`
array and `reasoning` still never reach a non-OpenRouter vendor. `max_tokens` (mentioned in the
plan as an optional OpenAI-compat field): not added here — nothing in this app sets it today for
any vendor, so there is nothing to gate; if a future task adds it, this same `if self._vendor ==
"openrouter"` split is where it would need the same treatment if it turns out to be
OpenRouter-specific too.

**Scope boundary:** this only changes the *outgoing request* shape. The `200`-with-embedded-
error-body branch (`error.code` inside an HTTP-200 response) is unchanged — Gate B-10's failure
was a real top-level HTTP 400, not a 200-wrapped one, and the plan doesn't ask for that path to
change.

**Contract test** (new, MockTransport): for each vendor (`"openrouter"` with and without
`fallback_models`, `"gemini"`, `"generic"`), capture the outgoing JSON body and assert its exact
key set — `{"messages", "reasoning", "model"}` / `{"messages", "reasoning", "models"}` for
OpenRouter, `{"messages", "model"}` (plus `"temperature"` when set) for Gemini/generic, and
explicitly assert `"reasoning"`/`"models"` are **absent** for the latter two — a test that would
fail immediately if `reasoning` were ever sent to Gemini again (the PM's requested revert check).

### 2. `ProviderRequestRejectedError` (point 2)

New class in `app/core/exceptions.py`, alongside `ProviderAuthError` (config-shaped errors that
can't self-resolve on retry):
```python
class ProviderRequestRejectedError(ProviderError):
    """Raised on HTTP 400 -- the request itself was malformed (e.g. an unknown
    field the upstream doesn't accept). Never worth retrying (the same bad
    request would just be rejected again), and never resolved by backoff --
    it's a code/config bug on this app's side, not a transient upstream
    condition."""
```
`OpenAICompatProvider.generate()` gains one new branch, checked alongside the existing
401/402/403/404 branch:
```python
if status == 400:
    self._raise(
        ProviderRequestRejectedError(
            self._error_message(response, "OpenAI-compatible endpoint rejected the request")
        ),
        status,
    )
```
Any HTTP 400, from any vendor — the transport-level code itself is the universal signal ("the
client sent something wrong"), not tied to Gemini's specific `INVALID_ARGUMENT` body wording, so
this stays correct for a future vendor that phrases its 400 differently.

**No retry, immediate circuit-open:** `ProviderRequestRejectedError` subclasses `ProviderError`
directly — **not** `ProviderInvalidResponseError` (which `_CONTENT_RETRY_ERRORS` in `router.py`
already retries once) and **not** `ProviderRateLimitError` (which `_TRANSIENT_ERRORS` backs off
on). Because it matches neither tuple, `_attempt`'s existing `except _TRANSIENT_ERRORS`/`except
_CONTENT_RETRY_ERRORS` clauses simply never catch it — no new exclusion clause needed there
(unlike `ProviderDailyQuotaError` in 18.6, which needed one because it's a genuine subtype of an
already-caught class). `AIRouter.generate()`'s per-entry exception handler gains one branch,
alongside the existing `ProviderDailyQuotaError`/`ProviderAuthError` checks:
```python
if isinstance(exc, ProviderDailyQuotaError):
    entry.circuit.open_until(exc.reset_at_epoch_seconds)
elif isinstance(exc, (ProviderAuthError, ProviderRequestRejectedError)):
    entry.circuit.open_immediately()
else:
    entry.circuit.record_failure()
```
`ai_job_service._PROVIDER_ERROR_CODES` gains `ProviderRequestRejectedError: "provider_request_rejected"`.

### 3. Fallback-reason label (point 3)

`generate()`'s fallback path currently sets `result.fallback_reason = type(last_error).__name__
if last_error is not None else "no_cloud_provider_configured"` — the `else` branch is reached
both when the chain was empty from the start AND when every entry was skipped for being
circuit-open (both leave `last_error is None`), which is exactly the mislabelling Gate B-10 found
(58 calls read `no_cloud_provider_configured` when every entry was actually open). Fixed by
reusing the same `bool(self._chain)` check `result.circuit_open` already computes:
```python
if last_error is not None:
    result.fallback_reason = type(last_error).__name__
elif self._chain:
    result.fallback_reason = "all_cloud_circuits_open"
else:
    result.fallback_reason = "no_cloud_provider_configured"
```

### 4. Default chain order (point 4, D30)

`app/core/config.py`: `CLOUD_PROVIDER_ORDER: str = "gemini,openrouter"` (was
`"openrouter,gemini"`). `.env.example`'s `DIE_CLOUD_PROVIDER_ORDER` updated to match. No other
code change — the dispatch loop already respects whatever order string is configured; this is
purely a default-value flip, per Gate B-10's own evidence (Gemini ~4s/1.00x word target vs.
OpenRouter's 16 real 75s timeouts that run).

### 5. Opt-in live contract check (point 5)

`scripts/live_provider_contract_check.py` — reuses `router.py`'s own
`_configured_cloud_provider_names`/`_build_chain_entries` (already allowed-file code, not
duplicated) to build the exact same `Provider` instances the real app would dispatch to, then
calls each one's `generate()` directly (bypassing `AIRouter` entirely — this is a raw one-shot
probe, not a routed call, so it never touches any circuit) with a tiny fixed prompt
(`"Reply with the single word: ok."`, 15s deadline). Per entry, prints **only**:
```
<entry-name>: OK
<entry-name>: FAIL (HTTP <upstream_status or "-">, <ExceptionClassName>)
```
Never the exception message text (even though `_redact` already scrubs the key from it, this
script prints strictly less than that as a second layer — vendor name, status, pass/fail, full
stop), never the request/response body, never the key. Module docstring states plainly: **opt-in,
PM-run only, never collected by pytest** (its filename matches neither `test_*.py` nor
`*_test.py`, and `pytest.ini` has no `python_files`/`testpaths` override that would sweep
`scripts/`, so it's already safe from accidental collection by construction — the docstring is
belt-and-suspenders documentation, not a functional guard). `if __name__ == "__main__":` guard;
importing the module does nothing on its own. The Coder tests its **offline** parts only —
`_build_probe_request()`-style pure helpers, if any, via MockTransport-style unit tests exactly
like every other provider test — and never executes it against a real endpoint; the PM runs it
for real.

### 6. Tests (all points)

MockTransport only for everything except the new opt-in script (untestable-live by design,
covered only at the "does it build the right request" level, offline). New:
- Per-vendor payload key-set contract tests (point 1) — the PM's named revert check: temporarily
  send `reasoning` to a Gemini-vendor provider → this test fails.
- `ProviderRequestRejectedError` on HTTP 400 — no retry (a MockTransport handler that counts
  calls, asserting exactly one), immediate circuit-open at the router level, mapped to
  `"provider_request_rejected"` in `ai_job_service`. The PM's named revert check: temporarily map
  400 back to `ProviderInvalidResponseError` → the no-retry test fails (it would then observe 2
  calls, the old content-retry behavior).
- `all_cloud_circuits_open` vs `no_cloud_provider_configured` — a chain with entries, all
  circuit-open, asserts the former; an empty chain asserts the latter (regression guard on the
  exact Gate B-10 mislabelling).
- Default `CLOUD_PROVIDER_ORDER` reads `"gemini,openrouter"` from a fresh `Settings()` (no env
  override) — locks in D30's default.
- `scripts/live_provider_contract_check.py`'s offline-testable pieces, if the implementation
  yields any pure helper worth isolating (e.g. request-building) — via MockTransport, same
  pattern as every other provider test; no real endpoint calls, ever, from this suite.

## Verification (required)

Full suite, `ruff`, revert-and-confirm-failure on the vendor-payload contract test (`reasoning`
sent to Gemini) and the 400-no-retry test (mapped back to `ProviderInvalidResponseError`), real
DB untouched.

## Evidence

_pending_
