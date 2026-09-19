# Task 13.2 — Provider-Neutral AI Gateway

- **Status:** pending
- **Dependency:** 13.0; Gate A may run in parallel conceptually
- **Controlling detail:** implementation plan §8, Task 13.2

## Objective

Create a typed async provider contract, normalized safe errors, Ollama and Gemini
adapters, one retry/deadline/fallback policy, shared validation, and fake-provider seams.

## Allowed files

`app/services/ai/**`, `app/core/config.py`, `app/core/constants.py`,
`app/core/exceptions.py`, `requirements.txt`, `tests/test_ai_contracts.py`,
`tests/test_ai_providers.py`, `tests/test_ai_router.py`, `tests/test_ai_validation.py`.

## Constraints

No legacy service is switched before contract tests pass. Async client lifetime follows
app lifespan. Ollama URL is HTTP loopback without credentials. No nested retries, full
prompt logging, response dumping, or hard dependency on Gemini remote-background APIs.

## Verification and exit

Contract/error/timeout/cancel/429/5xx/malformed cases pass; auth/400 are non-retryable;
total attempts/deadline are bounded; logs exclude key and full prompt; ruff passes.

## Plan (written before implementation)

### Live pre-checks done before locking design (2026-09-19)

- Re-verified `gemini-3.8-flash` live via `GET
  https://generativelanguage.googleapis.com/v1beta/models` (real API key, real HTTP
  200): listed as `models/gemini-3.8-flash`, displayName "Gemini 3.8 Flash", **no**
  `-preview` suffix. Cross-checked against `ai.google.dev/gemini-api/docs/models`
  (fetched live): still the current stable/recommended Flash model, no deprecation
  notice. `models.list` also shows several genuinely preview models on this account
  (`gemini-3-flash-preview`, `gemini-3.1-flash-lite-preview`,
  `gemini-3.1-flash-image-preview`, `gemini-3.1-flash-tts-preview`) — none of these
  are used; the gateway's Gemini adapter only ever uses the existing
  `app.core.constants.GEMINI_MODEL` constant (`gemini-3.8-flash`), not a new setting,
  so there is exactly one selectable stable model and no route to a preview model.

### Paths

New:
- `app/services/ai/__init__.py`
- `app/services/ai/contracts.py`
- `app/services/ai/ollama_provider.py`
- `app/services/ai/gemini_provider.py`
- `app/services/ai/fake_provider.py`
- `app/services/ai/validation.py`
- `app/services/ai/router.py`
- `tests/test_ai_contracts.py`
- `tests/test_ai_providers.py`
- `tests/test_ai_router.py`
- `tests/test_ai_validation.py`

Edited:
- `app/core/exceptions.py` — add typed provider errors.
- `app/core/config.py` — add `AI_MODE`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`,
  `OLLAMA_NUM_CTX`, `AI_REQUEST_DEADLINE_SECONDS` settings.
- `app/core/constants.py` — add `AI_MODES`, circuit-breaker threshold/cooldown
  constants. `GEMINI_MODEL`/`GEMINI_MODEL_FALLBACKS` stay untouched (legacy
  `script_service.py`/`learning_service.py` still own them until Task 13.4/13.5
  migrate those call sites — not in this task's scope).

Not touched: `requirements.txt` (no new dependency — `httpx.MockTransport`, already
part of the pinned `httpx==0.28.1`, covers provider tests; Pydantic `TypeAdapter`,
already used by `script_service.py`, covers schema validation — no new JSON-Schema
library needed).

### File-level plan

**`app/core/exceptions.py`** — add, after the existing `AppError` subclasses:
`ProviderError(AppError, status_code=502)` as the common base, plus
`ProviderTimeoutError`, `ProviderAuthError` (message never includes the key),
`ProviderRateLimitError`, `ProviderUnavailableError` (connection refused, model
missing, non-loopback/misconfigured URL), `ProviderInvalidResponseError` (malformed
JSON / unexpected shape), `SchemaValidationError` (structurally valid JSON that fails
Pydantic validation) — all provider errors, mirroring the existing
`ScriptGenerationError`-style pattern so the current global `AppError` handler needs
no change.

**`app/services/ai/contracts.py`** — `AIMode(str, Enum)` = `gemini|local|hybrid`
(matches `ADR-001`'s `DIE_AI_MODE` kill switch); `GenerationRequest` (Pydantic model:
`prompt: str`, `schema: dict | None`, `temperature: float | None`,
`deadline_seconds: float`, `purpose: str` for logging/metrics — never raw
project/script content beyond the prompt itself, which is never logged); `Provider`
`typing.Protocol` with `name: str` and `async def generate(request) ->
GenerationResult`; `GenerationResult` (Pydantic model: `text`, `provider`, `model`,
`tokens_used: int | None`, `latency_ms: float`, `attempt: int`, `prompt_hash: str`,
`fallback_used: bool`, `circuit_open: bool`) — `prompt_hash` (sha256, first 16 hex
chars, matching `script_service.py`'s existing convention) is what gets logged, never
the prompt text itself.

**`app/services/ai/validation.py`** — `parse_and_validate(text: str, adapter:
TypeAdapter) -> Any`: `json.loads` then `adapter.validate_python`, wrapping
`json.JSONDecodeError`/`pydantic.ValidationError` into `SchemaValidationError` with a
short, non-prompt-content message (field paths / error count only). This is the one
shared primitive Task 13.4/13.5 will reuse instead of each service re-implementing
the same `try/except json.loads` + `try/except PydanticValidationError` pair
currently duplicated in `script_service.py`'s `generate_script`/`regenerate_line`.

**`app/services/ai/ollama_provider.py`** — `OllamaProvider(base_url, model, num_ctx,
timeout)`. Reuses the same loopback-URL rule already enforced by
`scripts/qualify_local_ai.py::validate_loopback_url` (HTTP only, loopback host, no
credentials/query/fragment/path, explicit port) — re-implemented here as a small
local function rather than importing from `scripts/` (a diagnostic script, not
product code; Task 13.1's allowed files did not include `app/`). One
`httpx.AsyncClient.post("/api/generate", json={..., "stream": False, "think": False,
"format": request.schema, "options": {"num_ctx": ...}, "keep_alive": "5m"})` call —
**exactly one attempt, no internal loop** (the router owns retry policy, per this
task's "no nested retries" verification requirement). Maps: `httpx.ConnectError`/
`httpx.ConnectTimeout` → `ProviderUnavailableError`; `httpx.TimeoutException` →
`ProviderTimeoutError`; HTTP 404 → `ProviderUnavailableError` (model missing, matches
the real 404 behavior confirmed live in Task 13.1's Gate A evidence); other
non-2xx → `ProviderInvalidResponseError`; successful response routed through
`validation.parse_and_validate` when `request.schema` is set.

**`app/services/ai/gemini_provider.py`** — `GeminiProvider(api_key, model=
constants.GEMINI_MODEL, timeout)`. Same one-call shape as
`script_service._call_gemini` (`responseMimeType`/`responseJsonSchema`,
`params={"key": ...}`) but **exactly one attempt** — no internal retry/backoff loop
and no multi-model fallback chain here (that 6-model chain stays legacy-only in
`script_service.py`/`learning_service.py` until Task 13.4/13.5 decide whether to
migrate it; the ADR's "one visible stable Gemini fallback" is a single model by
design, not the existing quota-spreading chain). Maps: HTTP 401/403 →
`ProviderAuthError` (message never includes the key or its value — status code and a
fixed string only); HTTP 429 → `ProviderRateLimitError`; HTTP 503 →
`ProviderUnavailableError`; other non-2xx → `ProviderInvalidResponseError`;
`httpx.TimeoutException` → `ProviderTimeoutError`; `httpx.RequestError` →
`ProviderUnavailableError`.

**`app/services/ai/fake_provider.py`** — `FakeProvider(name, responses:
list[GenerationResult | Exception])`: pops one scripted outcome per call (raises if
it's an exception, returns it otherwise), records call count/received requests for
assertions. Used by `tests/test_ai_router.py` so router retry/fallback/circuit-state
logic is tested deterministically with zero network calls, per the plan's "ordinary
tests don't call network/model real" invariant.

**`app/services/ai/router.py`** — `AIRouter(local: Provider, gemini: Provider, mode:
AIMode, failure_threshold: int, cooldown_seconds: float)`. In-memory circuit-breaker
state (consecutive local-provider failures + an "opened until" timestamp — this is
process-local, not persisted; Task 13.3's durable job layer is the real persistence
boundary, out of scope here). `generate(request)`:
- `mode=local`: call `local` once; on a retryable error class
  (`ProviderTimeoutError`/`ProviderUnavailableError`/`SchemaValidationError`/
  `ProviderInvalidResponseError`), retry `local` exactly once more (the ADR's "at
  most one … infrastructure retry"); no Gemini fallback (needed as-is for Task
  13.9's Gate B "local-only, fallback OFF" trial).
- `mode=gemini`: call `gemini` once, same one-retry-on-retryable-error policy, no
  local involvement.
- `mode=hybrid`: if the circuit is open, skip `local` entirely and go straight to
  `gemini` (recording `circuit_open=True`); otherwise call `local` once, retry once
  on a retryable error, and on continued failure fall back to `gemini` exactly once
  (`fallback_used=True`) — never more than 1 local attempt + 1 local retry + 1
  gemini attempt for one `generate()` call, which is what
  `tests/test_ai_router.py` asserts as the "no nested retries" bound. A
  non-retryable error (`ProviderAuthError` or an unexpected exception) fails fast
  with zero retry, falling back to `gemini` immediately in hybrid mode (an auth/
  config mistake on the local side should not block the user from at least trying
  Gemini). Every attempt logs `provider`, `model`, `prompt_hash`, `latency_ms`,
  `tokens_used`, `attempt` — never the prompt or response text, matching
  `script_service.py`'s existing `gemini_call`/`gemini_retryable_error` log line
  convention.
- Total wall-clock budget bounded by `request.deadline_seconds`
  (`asyncio.wait_for` around the whole `generate()` body) so a hung provider can't
  block a caller indefinitely — this is what "deadlines" means in the task's
  Objective, independent of each provider's own `httpx` timeout.

**`app/core/config.py`** — `AI_MODE: str = "gemini"` (packaged default stays Gemini
per ADR-001 until onboarding is proven — not `hybrid`), `OLLAMA_BASE_URL: str =
"http://127.0.0.1:11434"`, `OLLAMA_MODEL: str = "qwen3.5:9b"`, `OLLAMA_NUM_CTX: int =
16384`, `AI_REQUEST_DEADLINE_SECONDS: float = 120.0` (generous enough to cover Gate
A's measured 33.4s cold-load plus real generation time; Task 13.4's per-section
checkpoint deadlines are a separate, smaller-grained concern, not this task's).

**`app/core/constants.py`** — `AI_MODES = ("gemini", "local", "hybrid")` (for
Pydantic/route validation later), `AI_CIRCUIT_FAILURE_THRESHOLD = 3`,
`AI_CIRCUIT_COOLDOWN_SECONDS = 60.0`.

### Best practices applied

CR-01 (type hints + docstrings on every public function/class), AR-04-style typed
exceptions instead of ad hoc `Exception`, CR-02 (no magic numbers — thresholds/
deadlines named in `constants.py`/`config.py`), Gemini Rules (never log full prompt
or the key; log model/tokens/latency/prompt_hash), AR-02 (everything `async def`,
`httpx.AsyncClient` per-call — this task does not yet wire app-lifespan client
lifetime, since no route uses the gateway yet; that lands with the actual migration
in Task 13.4/13.5, matching this task's own "no legacy service is switched before
contract tests pass" constraint).

### Verification commands

```
venv\Scripts\python.exe -m ruff check app\services\ai tests\test_ai_contracts.py tests\test_ai_providers.py tests\test_ai_router.py tests\test_ai_validation.py app\core\config.py app\core\constants.py app\core\exceptions.py
venv\Scripts\python.exe -m pytest tests\test_ai_contracts.py tests\test_ai_providers.py tests\test_ai_router.py tests\test_ai_validation.py -v
venv\Scripts\python.exe -m pytest tests\ -x -q
git diff --check
```

Expected: new AI test files all pass; full suite has no new failures beyond the
already-documented Gemini-retry timing flake class (rerun any flake in isolation and
record it, per standing project discipline); ruff clean; no legacy route/service
behavior changed (this task adds files and two config/constants/exceptions edits
only — no route wiring yet).
