# Task 18.1 — `OpenAICompatProvider`

- **Status:** done
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** none (the phase starts after Phase 17 closes)
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.1", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.1", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

One HTTP call per `generate()` to `{base_url}/chat/completions`. Plain prompt-only JSON (never `response_format`). `reasoning: {exclude: true}`. Fence strip. Error mapping per plan §3 18.1: 200-with-error / 429 / 5xx are transient; 401/402/403/404 are a config error; timeout; invalid shape. The key is never in messages or logs.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**PM review (`85ab8ed`) — C1 and C2 folded in during implementation, no re-approval required
per PM's explicit instruction:**
- **C1:** HTTP `429`, and a `200`-with-error body whose `error.code == 429`, both raise
  `ProviderRateLimitError` — not `ProviderUnavailableError` as originally designed below (the
  plan's table lumped them together; the PM's review called that too loose). `5xx` and any other
  `200`-with-error body still raise `ProviderUnavailableError`. This is the existing transient
  class already in the router's `_TRANSIENT_ERRORS` tuple, kept distinct from
  `ProviderUnavailableError` so 18.4's fallback-rate readout can report "rate-limited" vs
  "overloaded" separately (D22's free-vs-paid decision input).
- **C2:** every exception message this provider raises carries only the HTTP status, the
  upstream `error.code`/`error.message` (truncated to 200 chars) — never the raw response body —
  and is passed through a `_redact()` backstop that strips any literal occurrence of the
  configured API key before the exception is constructed. Reason: some upstreams echo part of
  the request (including the key) back in an error body, so extracting only the `error` field is
  not sufficient on its own. The key-safety test is extended: a `401` whose JSON body's
  `error.message` contains the marker key, asserting the marker is absent from both the raised
  exception message and `caplog.text`. Implemented as two instance helpers, `_format_error`
  (pure string-building + redact, shared) and `_error_message` (parses `response.json()` for the
  non-200 branches; the `200`-with-error branch already has `data` parsed, so it calls
  `_format_error` directly to avoid re-parsing).

**Below is the original (pre-C1/C2) design text, updated in place where C1/C2 changed it —**

**Shape, matching `OllamaProvider`/`GeminiProvider` exactly** (same constructor-args-not-settings
pattern, same one-call-no-internal-retry contract, same `Provider` protocol): a new
`app/services/ai/openai_compat_provider.py`, class `OpenAICompatProvider`, `name = "openai_compat"`.

```python
class OpenAICompatProvider:
    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 180.0) -> None:
        self._base_url = validate_openai_compat_base_url(base_url)
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        ...
```

`timeout=180.0` default: the smoke test's own conclusion #4 recommends "a cloud-specific call
deadline (about 180 s)" from the observed 8–296 s latency spread. This is this provider's own
`httpx` per-request timeout (independent of the router's `deadline_seconds`, same relationship
`OllamaProvider`'s docstring already documents) — a placeholder default for direct construction
and this task's tests; 18.2/18.3 will pass the real value from settings
(`AI_CLOUD_DEADLINE_SECONDS`, a Task 18.2 constant, not added here).

**No API key validation at construction** — mirrors `GeminiProvider` (not `OllamaProvider`,
which has no key). `generate()` raises `ProviderAuthError` if the key is empty, same message
shape as Gemini's.

**`validate_openai_compat_base_url(base_url: str) -> str`** (module-level function, exported
like `ollama_provider.validate_loopback_url`, but not imported from there — `ollama_provider.py`
is outside this task's allowed files, and its check is loopback-only/no-path by design, which is
wrong for this provider: an OpenAI-compatible base URL conventionally already includes an API
path segment, e.g. OpenRouter's `https://openrouter.ai/api/v1`. This task's validator is
therefore intentionally narrower than Ollama's, not a shared helper):
- Reject a URL with `username`/`password` set (no credentials in the URL, plan §3 18.1).
- Accept `scheme == "https"` unconditionally, OR `scheme == "http"` with `hostname` in the same
  loopback set `OllamaProvider` uses (`127.0.0.1`, `localhost`, `::1`) — the plan's "https only,
  except loopback." A local self-hosted OpenAI-compatible server (e.g. for testing) is the only
  legitimate `http` case.
- Otherwise `raise ValueError` (constructor-time, matching `validate_loopback_url`'s own
  contract — a bad base URL is a configuration error, not a per-call `ProviderError`).
- No path/query/fragment restriction (unlike Ollama's validator) — the path is expected and
  meaningful here.
- Returns `base_url.rstrip("/")`; the endpoint is `f"{self._base_url}/chat/completions"`.

**Request payload** (plain prompt-only JSON, per the smoke test — `response_format:
json_schema` returned malformed JSON, `json_object` breaks the array contract):
```python
payload = {
    "model": self._model,
    "messages": [{"role": "user", "content": request.prompt}],
    "reasoning": {"exclude": True},
}
if request.temperature is not None:
    payload["temperature"] = request.temperature
```
`request.json_schema` is **never** read by this provider — deliberate, not an oversight (the
router still validates the caller's Pydantic schema on the returned text downstream, same as
every other provider). Headers: `{"Authorization": f"Bearer {self._api_key}"}`. No key anywhere
in the URL or query string.

**Response handling, in order** (the plan's table, made exact):
1. `httpx.TimeoutException` → `ProviderTimeoutError`. `httpx.RequestError` (e.g. connection
   refused) → `ProviderUnavailableError` — both match the existing `Ollama`/`Gemini` convention,
   not explicitly in the plan's table (which only covers HTTP responses) but consistent with it.
2. `status_code in (401, 402, 403, 404)` → `ProviderAuthError` (message: only the status code,
   no response body — matches `GeminiProvider`'s exact 401/403 message shape). This is the
   plan's "non-transient configuration error, fail fast" row. `ProviderAuthError` is not in
   `router._TRANSIENT_ERRORS` or `_CONTENT_RETRY_ERRORS`, so the router (as it exists today,
   before 18.2's fallback-on-any-`ProviderError` generalization) already gives it zero retries —
   the right behaviour is already available from the existing class, no new one needed. 402 and
   404 aren't literally "auth" failures, but no more specific "config error" class exists yet and
   inventing 4 new ones isn't proportionate for one task; `ProviderAuthError`'s own docstring
   ("message never includes the key itself") already states the exact invariant this task must
   hold, which is a second reason to reuse it here rather than add a parallel type.
3. `status_code == 200`: parse the JSON body first.
   - JSON parse failure → `ProviderInvalidResponseError`.
   - `"error"` key present in the parsed body → `ProviderUnavailableError`, UNLESS the error's
     `code == 429` (C1) → `ProviderRateLimitError` instead (the smoke test's "HTTP 200 with an
     error body" case — e.g. OpenRouter's `{"error": {"message": "... overloaded", "code":
     503}}`). Message includes only the error's own `code`/`message` fields (C2), never the raw
     body, and is redacted before raising.
   - Otherwise extract `data["choices"][0]["message"]["content"]`; missing/empty →
     `ProviderInvalidResponseError` (the plan's "missing choices, or empty content" row).
4. `status_code == 429` → `ProviderRateLimitError` (C1). `500 <= status_code < 600` →
   `ProviderUnavailableError`. (Superseded by C1: the original design below used
   `ProviderUnavailableError` for both, matching the plan's table literally; the PM's review
   said the table was too loose and split them — see the C1/C2 note above.)
5. Any other status → `ProviderInvalidResponseError` (catch-all, matches `Ollama`/`Gemini`'s own
   fallback for an uncategorized non-2xx).

**Fence strip** (module-level `_strip_code_fences(text: str) -> str`, applied to the extracted
`content` before it becomes `GenerationResult.text`):
```python
_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)

def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    return match.group(1).strip() if match else stripped
```
Handles a fenced ` ```json\n[...]\n``` ` block or a bare ` ```\n...\n``` ` block; text with no
fence passes through unchanged (stripped of surrounding whitespace only).

`tokens_used = data.get("usage", {}).get("total_tokens")`. `attempt=1` always (one call, no
internal retry — the plan's explicit requirement; the router owns retry/fallback).

**No changes to `app/core/exceptions.py` or `app/core/constants.py`.** Every error case maps to
an existing `ProviderError` subclass (see above). No default base URL/model/timeout constant is
added here — those are 18.2/18.3's settings-wiring concern (`DIE_OPENAI_COMPAT_*` env vars,
`AI_CLOUD_DEADLINE_SECONDS`), out of this task's scope (provider class only).

**Test plan** (`tests/test_openai_compat_provider.py`, new — `httpx.MockTransport` only, same
`_install_mock_transport(monkeypatch, module, handler)` helper as `tests/test_ai_providers.py`,
never a real network call):
- `validate_openai_compat_base_url`: accepts `https://openrouter.ai/api/v1` (path preserved,
  trailing slash stripped); accepts `http://127.0.0.1:8080/v1` (loopback exception); rejects
  `http://example.com` (http, not loopback); rejects a URL with `user:pass@` credentials.
- Success: 200, valid `choices[0].message.content`, plain (unfenced) JSON — asserts `text`,
  `provider`, `model`, `tokens_used`, `attempt == 1`.
- Fence strip: content wrapped in ` ```json\n...\n``` ` — asserts the returned `text` has no
  fence markers and matches the inner JSON exactly. A second case for a bare ` ``` ` fence with
  no `json` tag.
- Request shape: captures the sent body — asserts `"response_format" not in body` (the plan's
  explicit "never send" requirement), `body["reasoning"] == {"exclude": True}`,
  `body["messages"] == [{"role": "user", "content": <the prompt>}]`, and the `Authorization`
  header is `f"Bearer {api_key}"`.
- 200-with-error-body (code 503) → `ProviderUnavailableError`. 200-with-error-body (code 429,
  C1) → `ProviderRateLimitError`.
- HTTP 429 (C1) → `ProviderRateLimitError`. 500/502/503 (parametrized) → `ProviderUnavailableError`.
- 401, 402, 403, 404 (parametrized) → `ProviderAuthError`.
- Some other non-2xx not in the table (400) → `ProviderInvalidResponseError`.
- Missing `choices` → `ProviderInvalidResponseError`. Empty `content` string →
  `ProviderInvalidResponseError`.
- `httpx.ConnectTimeout` → `ProviderTimeoutError`. `httpx.ConnectError` → `ProviderUnavailableError`.
- No API key configured (`api_key=""`) → `ProviderAuthError`, no HTTP call made.
- **The key-safety test (required by the plan; extended per C2):** a distinctive marker string
  as the API key, triggered through (a) a 401 whose JSON body's `error.message` contains the
  marker itself (C2's specific new case — some upstreams echo request data back) and (b) a
  generic 500 with no key in the body — as two separate test functions (a single test calling
  `_install_mock_transport` twice broke the shared monkeypatch-based mock-transport helper's
  closure chaining; see Evidence) — each asserting the marker is absent from
  `str(exc_info.value)` and from `caplog.text` at `DEBUG` level. A separate assertion in the
  *success* path confirms the marker **is** sent as `Authorization: Bearer <marker>` on the wire
  (proving the key is actually used, not just silently omitted — a provider that never sends the key
  would trivially "pass" a leak test for the wrong reason).
- Prompt never logged (mirrors `test_ollama_provider_never_logs_prompt_body`): a distinctive
  prompt marker, asserted absent from `caplog.text`.
- Revert-and-confirm-failure target: the key-safety tests. Temporarily made `_redact` a no-op
  (return `message` unchanged), re-ran the two key-safety tests alone → the 401-echoes-key test
  failed exactly as expected (the marker appeared in the raised exception message); the plain-500
  test still passed (nothing to redact there, so it can't detect this regression on its own —
  confirms the 401-echo case is the one that actually exercises the backstop). Restored, re-ran →
  both passed.
- Full suite, `ruff`, real DB untouched (read-only per invariant 26 — this task's tests never
  touch `data/app.db`, matching every other provider test file).

## Verification (required)

See plan §3 "18.1". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

- Design commit `85ab8ed` (APPROVED with C1/C2), this implementation commit folds both in per
  "no re-approval needed."
- Code: `app/services/ai/openai_compat_provider.py` (new) — `OpenAICompatProvider`,
  `validate_openai_compat_base_url`, `_strip_code_fences`, `_extract_error_info`, plus the
  instance helpers `_redact`/`_format_error`/`_error_message` added for C2. No changes to
  `app/core/exceptions.py` or `app/core/constants.py`, as designed.
- Tests: `tests/test_openai_compat_provider.py` (new) — **29 tests**, `httpx.MockTransport` only,
  no real OpenRouter call. Covers the URL validator, success + fence-strip (both fenced forms),
  request-shape assertions (no `response_format`, `reasoning` present, exact `messages`/
  `Authorization` shape), every row of the error table including C1's 429-vs-other-transient
  split (HTTP 429 direct, and a 200-with-error body whose `code == 429`), the two C2 key-safety
  tests, the success-path "key really sent" assertion, and prompt-never-logged.
- One test-design issue found and fixed during implementation (not PM-caught): my first draft of
  the key-safety test called the shared `_install_mock_transport` helper twice within one test
  function (401-echo sub-case, then a 500 sub-case). It failed the second sub-case with the
  *first* sub-case's response, traced to the helper's own closure: each call captures
  `real_async_client = httpx.AsyncClient` as whatever `httpx.AsyncClient` currently *is* — after
  the first `monkeypatch.setattr`, that's already the first call's factory, not the true
  original, so the second factory's wrapped call recurses into the first factory, which
  unconditionally overwrites `kwargs["transport"]` back to the first transport. This is a latent
  bug in `_install_mock_transport` itself (copied verbatim from `tests/test_ai_providers.py`,
  where it was never called twice in one test) — not fixed here, since fixing a shared test
  helper is outside this task's allowed files; worked around by splitting into two separate test
  functions instead, each with its own fresh `monkeypatch` fixture instance.
- Targeted run: `tests/test_openai_compat_provider.py` → **29 passed**.
- Full suite: `./venv/Scripts/python.exe -m pytest -q` → **993 passed** (964 baseline after
  Phase 17 close-out + 29 new tests). No other test broke. Real DB untouched (this task's tests
  never open `data/app.db`).
- `ruff check .` → all checks passed.
- Revert-and-confirm-failure: see the test-plan section above (temporarily made `_redact` a
  no-op; the 401-echoes-key test failed as expected, the plain-500 test still passed — confirming
  it doesn't exercise the backstop on its own). Restored → both passed again.
