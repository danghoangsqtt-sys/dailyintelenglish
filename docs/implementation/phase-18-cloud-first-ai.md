# Phase 18 Implementation Plan — Cloud-First AI with Local Fallback (ENH-011)

**Status:** Controlling plan, PM, 2026-09-23. **Starts after Phase 17 closes.** Gate B-8 must first
record the local-qwen baseline that 18.5 compares against.
**Authority:** owner decisions D21–D24 (`docs/brainstorm/session-2026-09-23.md`). D21 supersedes
D9/D11 as the default.
**Evidence:** `docs/operations/enh011-nemotron-smoke.md` (the smoke test of OpenRouter free models).

## 1. Goal

AI text generation (script, learning, thumbnail and YouTube text) runs on an OpenAI-compatible
cloud model first. Local qwen3.5:9b is the automatic fallback, so a cloud outage, rate limit or
expired free tier degrades a job instead of failing it. The dedicated Gemini provider is replaced
by the generic one.

## 2. Invariants (in addition to Phases 13–17)

31. **The key never leaves the machine except in the provider's auth header.** It is never
    logged, never returned by any API (masked status only), never written to evidence, and never
    committed. `.env` stays gitignored.
32. **The fallback is always there.** If the cloud is not configured (no key or model), fails,
    is rate-limited or times out, the local provider runs within its **own** time budget. With
    no key set, the app behaves exactly like today's local-only mode.
33. **Kill switch.** `DIE_AI_ALLOW_CLOUD=false` (or mode `local`) means zero cloud calls. This is
    tested.
34. **Thresholds unchanged.** Every script, learning and media threshold stays pinned. This phase
    changes *who* writes, never what passes.
35. **No personal data guidance.** The Settings UI states that topics are sent to a third-party
    model and must not contain personal data (free-tier data policy).

## 3. Tasks

Order: **18.1 → 18.2 → 18.3 → 18.4** (Coder, doc-first, PM-approved designs) **→ 18.5** (PM gate)
**→** close-out. Session partition and messaging are as in Phase 16 §6.

### 18.1 — `OpenAICompatProvider` (Coder, P0)

**Allowed files:** new `app/services/ai/openai_compat_provider.py`, `app/core/exceptions.py`
(only if a new error subclass is needed), `app/core/constants.py`, new
`tests/test_openai_compat_provider.py`, `CHANGELOG.md`.

**Required behaviour** (the smoke-test findings are the spec):
- `POST {base_url}/chat/completions`, Bearer key, one call per `generate()` with **no internal
  retry** (the router owns retries), the same shape as `OllamaProvider`.
- **Plain prompt-only JSON.** Never send `response_format`: `json_schema` returned malformed JSON
  and `json_object` broke arrays. Strip markdown fences from the content.
- Send `reasoning: {"exclude": true}`.
- Error mapping:

  | Response | Error raised |
  |---|---|
  | HTTP 200 **with an `error` body**, or HTTP 429 / 5xx | transient (`ProviderUnavailableError`) |
  | HTTP 401 / 402 / 403 / 404 | a **non-transient configuration error** (fail fast, straight to fallback) |
  | Timeout | `ProviderTimeoutError` |
  | Missing `choices`, or empty content | `ProviderInvalidResponseError` |

- `https` only, except loopback. No credentials in the URL. The key comes from the constructor
  and never from the URL.

**Verification:** a fake HTTP transport (`httpx.MockTransport`) covering every row of the table
above, a fence strip, an assertion that the request body never contains `response_format`, and a
test that the key never appears in any exception message or log record. Full suite, `ruff`.

### 18.2 — Router roles, modes, per-provider budgets; Gemini removed (Coder, P0)

**Allowed files:** `app/services/ai/router.py`, `app/services/ai/contracts.py`,
`app/services/ai/__init__.py`, `app/services/ai/gemini_provider.py` (**delete**),
`app/core/config.py`, `app/core/constants.py`, `app/main.py` (router builder only),
`app/services/settings_service.py` (the mode migration only), `.env.example`,
`tests/test_ai_router.py`, `tests/test_ai_providers.py`, `tests/test_ai_contracts.py`, and other
tests **only where they construct or assert the Gemini provider or mode names** (list them in the
card before editing), `CHANGELOG.md`.

**Required behaviour:**
1. **Roles instead of names:** `AIRouter(primary=…, fallback=…, mode=…)`.
2. **Modes** `local | cloud | cloud_first`:

   | Mode | Behaviour |
   |---|---|
   | `local` | Ollama only |
   | `cloud` | Cloud only, no fallback (diagnostic) |
   | `cloud_first` | Cloud, then Ollama. **Default when `AI_ALLOW_CLOUD` is true and a key is configured**; otherwise the effective mode is `local` (invariant 32) |

   Stored legacy values migrate: `gemini` → `cloud`, `hybrid` → `cloud_first`. This is logged
   once and never raised.
3. **Separate time budgets:** the primary gets `AI_CLOUD_DEADLINE_SECONDS` (default ≈ 150 s; the
   exact value, with its rationale from the smoke latencies, goes in the card). The fallback gets
   a fresh `AI_REQUEST_DEADLINE_SECONDS` budget. They never share one deadline, because a shared
   deadline is exactly how both smoke jobs died.
4. **Circuit breaker on the primary** (the existing threshold and cooldown constants): while it
   is open, calls go straight to the fallback. A configuration error (401/402/403/404) opens it
   immediately.
5. **Per-call record:** `provider`, `model`, `fallback_used`, `circuit_open` and `fallback_reason`
   (the error class name, never a message that could echo a key) go into the job metrics that
   already exist.
6. `GeminiProvider` is deleted. **Comments and docstrings elsewhere that mention Gemini are not
   touched in this task.** A sweep, if wanted, is a separate docs task (scope guard for D23).

**Verification:** router tests for each mode × {success, transient, config error, timeout}.
Required cases: "primary exhausts its own budget → the fallback still gets its full budget"; the
circuit opens and closes; the kill switch makes zero cloud calls; no key → effective `local`;
the legacy mode migration; revert-and-confirm-failure on the separate-budget test. Full suite,
`ruff`.

### 18.3 — Settings, health, key storage (Coder, P1)

**Allowed files:** `app/api/settings.py`, `app/models/settings.py`,
`app/services/settings_service.py`, `app/api/ai_jobs.py` (health payload only), `app/main.py`
(startup loading only), `frontend/pages/settings.html`, `frontend/static/js/settings.js`,
`frontend/static/js/api.js` (settings calls only), `frontend/static/css/style.css` (settings
block only), `scripts/check_dependencies.py`, `tests/test_settings_api.py`,
`tests/test_settings_service.py`, `tests/test_ai_health_api.py`,
`tests/test_ai_jobs_api.py` (health assertions only), and a settings browser test file named in
the card, `CHANGELOG.md`.

**Required behaviour:**
- Settings API and page:
  - base URL, model id and API key. The key is **write-only**: the status shows only whether it
    is set, plus the last 4 characters. It can be cleared.
  - a mode selector (`cloud_first` / `local`), plus "Test connection", which makes one tiny call
    and reports OK or the error class, never the key.
  - DB values override the `.env` defaults (`DIE_OPENAI_COMPAT_BASE_URL`, `_MODEL`,
    `_API_KEY`), and changes take effect without a restart.
- The old `gemini_api_key` row is **ignored and never reused** as a cloud key, and removed from
  the UI.
- The privacy note (invariant 35).
- `/api/ai/health` adds `cloud_configured`, `cloud_model`, `effective_mode` and `circuit_open`.
  No key material appears in it.
- `check_dependencies.py` reports cloud-configured as informational (not required).

**Verification:** API tests for set, clear and status (asserting the key never appears in any
response), test-connection with a fake provider, and a browser test of the page flow. Full suite,
`ruff`.

### 18.4 — Fallback-rate readout + runner support (Coder, P1)

**Allowed files:** `app/services/ai_job_service.py` (read-side aggregate only),
`app/api/ai_jobs.py`, `frontend/pages/settings.html` / `frontend/static/js/settings.js` (a display
line only), `scripts/run_ai_operational_trial.py`, the matching tests, `CHANGELOG.md`.

**Required behaviour:**
- `fallback_rate` over the last N completed jobs: the share of AI calls served by the fallback,
  and the share of jobs with any fallback. It is shown in health and on the Settings page. This
  is D22's decision input.
- The trial runner gains `--matrix cloud_first` and records, per run, provider/model per call,
  the fallback count, and the reasons.

**Verification:** aggregate tests on seeded job rows, and a runner unit test on a recorded
evidence shape. Full suite, `ruff`.

### 18.5 — Gate B-9: A/B cloud_first vs local (PM, Coder idle)

The Gate B-8 protocol, run with `--matrix cloud_first` (free `nvidia/nemotron-3-super-120b-a12b:free`)
and compared against B-8 (local). Report `docs/operations/phase18-gate-b9.md`, including:
- completion and content checks;
- repairs per job;
- wall time;
- the **fallback rate** and its reasons;
- the observed free-tier request cap;
- media duration and A/V (word counts will change, so re-check the pace).

**Pass (cloud_first):** B1 8-min 5/5 complete, **with no regression against B-8** on any gate.
The fallback rate is reported, not gated (D22). The owner then decides whether to stay free or
move to paid.

## 4. Stop conditions and rollback

- As in Phase 16 §5.
- **Rollback without a revert:** set the mode to `local` (in Settings or `.env`), which restores
  local-only behaviour. 18.2 keeps the local path's behaviour byte-for-byte when the effective
  mode is `local`.

## 5. Version

This is a behaviour-level feature, so on Phase 18 close the version moves `1.0.0-beta` →
`1.1.0-beta` (the first bump since v1.0.0-beta), recorded in the CHANGELOG and TRACKER.

## 6. Amendments

**Amendment A (PM, 2026-09-23, on approving the 18.2 design `6bc25aa`):**
1. **Router rebuilt per job dispatch.** A thin wrapper in `app/main.py` builds a fresh router for
   each job from the current settings. **One app-lifetime `CircuitBreaker`** is shared across
   builds. This is approved, and `app/main.py`'s 18.2 scope widens from "router builder only" to
   "router builder + per-dispatch wrapper". Rationale: today the worker's handlers capture a
   router built once at startup, so a Settings change would never reach job processing (a
   pre-existing gap that 18.3's no-restart requirement exposes).
2. **`AI_CLOUD_DEADLINE_SECONDS = 150`** (configurable). The default model (Nemotron 3 Super)
   answered in 8–28 s in the smoke test, and 150 still covers Ultra's observed 136 s. Models
   slower than that (Nex 296 s, Lightning > 180 s) are not suitable as the primary.
3. **Lease: no change.** `heartbeat()` renews unconditionally. `lease_expires_at` is read only by
   `recover_abandoned_jobs` at worker start, and no API or UI reads it. A single call outlasting
   `AI_JOB_LEASE_SECONDS = 90` is therefore harmless inside a running process; that is already
   true today (a 120 s deadline plus backoff). Recorded, not acted on.
4. **`fallback_reason` persistence.** 18.2's allowed files gain `app/services/script_pipeline.py`
   and `app/services/learning_pipeline.py`, **the per-call `_call_record` construction only**,
   adding `fallback_used` / `fallback_reason` / `provider` / `model` fields. No other change to
   either file.
5. **Test file list approved** as listed in the card, including the HYBRID-mode tests whose
   primary/fallback expectations **invert semantically** under CLOUD_FIRST (not a rename).
   `GEMINI_*` constants stay in `constants.py` for the two out-of-scope sample scripts.

