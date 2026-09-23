# Task 18.1 — `OpenAICompatProvider`

- **Status:** in_progress
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
   - `"error"` key present in the parsed body → `ProviderUnavailableError` (the smoke test's
     "HTTP 200 with an error body" case — e.g. OpenRouter's `{"error": {"message": "...
     overloaded", "code": 503}}`). Message includes `str(data["error"])[:200]` — safe (it's the
     *server's* text, never our key).
   - Otherwise extract `data["choices"][0]["message"]["content"]`; missing/empty →
     `ProviderInvalidResponseError` (the plan's "missing choices, or empty content" row).
4. `status_code == 429` or `500 <= status_code < 600` → `ProviderUnavailableError` (the plan's
   other transient row — deliberately the *same* exception class OpenRouter's 429 and its
   200-with-error case both use, not split into `ProviderRateLimitError` the way `GeminiProvider`
   splits 429 — the plan's table literally says "transient (`ProviderUnavailableError`)" for
   both rows together, so this task follows that instruction exactly rather than the older
   Gemini precedent).
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
- 200-with-error-body → `ProviderUnavailableError`.
- 429 → `ProviderUnavailableError`. 500 and 503 (parametrized) → `ProviderUnavailableError`.
- 401, 402, 403, 404 (parametrized) → `ProviderAuthError`.
- Some other non-2xx not in the table (400) → `ProviderInvalidResponseError`.
- Missing `choices` → `ProviderInvalidResponseError`. Empty `content` string →
  `ProviderInvalidResponseError`.
- `httpx.ConnectTimeout` → `ProviderTimeoutError`. `httpx.ConnectError` → `ProviderUnavailableError`.
- No API key configured (`api_key=""`) → `ProviderAuthError`, no HTTP call made.
- **The key-safety test (required by the plan):** a distinctive marker string as the API key,
  triggered through a 401 response AND a generic 500 response (two sub-cases in one test) —
  asserts the marker is absent from `str(exc_info.value)` in both cases, and absent from
  `caplog.text` at `DEBUG` level across the whole call. A separate assertion in the *success*
  path confirms the marker **is** sent as `Authorization: Bearer <marker>` on the wire (proving
  the key is actually used, not just silently omitted — a provider that never sends the key
  would trivially "pass" a leak test for the wrong reason).
- Prompt never logged (mirrors `test_ollama_provider_never_logs_prompt_body`): a distinctive
  prompt marker, asserted absent from `caplog.text`.
- Revert-and-confirm-failure target: the key-safety test. Temporarily change the 401 branch's
  message to include `self._api_key` directly (a deliberate regression), re-run the key-safety
  test alone → expect it to fail. Restore, re-run → passes.
- Full suite, `ruff`, real DB untouched (read-only per invariant 26 — this task's tests never
  touch `data/app.db`, matching every other provider test file).

## Verification (required)

See plan §3 "18.1". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

_pending_
