# Task 18.2 — Router roles/modes, per-provider budgets, circuit breaker; Gemini provider removed

- **Status:** done
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** 18.1 accepted
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.2", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.2", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

`AIRouter(primary, fallback, mode)` with modes `local | cloud | cloud_first`. The effective mode is `local` when there's no key or the kill switch is off. Separate time budgets (cloud `AI_CLOUD_DEADLINE_SECONDS`, fallback a fresh `AI_REQUEST_DEADLINE_SECONDS`). The circuit breaker is on the primary, and a config error opens it at once. Per-call `fallback_used` / `fallback_reason` (the class name only). Legacy stored modes migrate (`gemini`→`cloud`, `hybrid`→`cloud_first`). `gemini_provider.py` is deleted. Other files' Gemini comments are left untouched.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**PM review (`bf7cdfe`, plan Amendment A) — APPROVED, all 5 points ruled on:**
1. Per-dispatch rebuild + one app-lifetime `CircuitBreaker`: approved. `app/main.py`'s 18.2 scope
   widens from "router builder only" to "router builder + per-dispatch wrapper."
2. `AI_CLOUD_DEADLINE_SECONDS = 150` (configurable): approved as designed.
3. **Lease: no change**, ruling recorded verbatim — `heartbeat()` renews unconditionally;
   `lease_expires_at` is read only by `recover_abandoned_jobs` at worker start, and nothing in
   the API/UI reads it, so a single call outlasting `AI_JOB_LEASE_SECONDS = 90` inside a running
   process is harmless — already true today (120s deadline plus backoff already exceeds 90s).
   Not acted on; `app/core/constants.py`'s `AI_JOB_LEASE_SECONDS` is unchanged.
4. `fallback_reason` persistence: approved. Allowed files gain `app/services/script_pipeline.py`
   and `app/services/learning_pipeline.py`, **the per-call `_call_record` construction only** —
   adding `fallback_used`/`fallback_reason`/`provider`/`model` fields (the first and third
   already exist in `_call_record`; only `fallback_reason` is new — see point 4/5 below). No
   other change to either file.
5. Test file list approved as listed, including the semantic (not mechanical) inversion of the
   `HYBRID`→`CLOUD_FIRST` tests — old vs. new expectation stated per test below.
`GEMINI_*` constants stay in `constants.py` for the two out-of-scope sample scripts, as designed.

**PM review (Amendment B, mid-implementation) — a genuine blocker found and resolved:**
`app/services/script_service.py`, `learning_service.py`, `thumbnail_service.py`, and
`youtube_service.py` (none in the allowed-files list above) each had an identical pre-flight
guard, `if AIMode(settings.AI_MODE) is AIMode.GEMINI and not settings.GEMINI_API_KEY: raise
...("DIE_GEMINI_API_KEY is not configured")`. Once `AIMode.GEMINI` was deleted this became a hard
`AttributeError` on every call into these 4 services — not a cosmetic break, and also not
fixable by a bare rename: the guard also checked the *old* `GEMINI_API_KEY` field, so even a
rename would have made it wrongly reject every `cloud`/`cloud_first` request regardless of a
valid `OPENAI_COMPAT_API_KEY`. Flagged to the PM rather than fixed unilaterally (stop-and-ask,
since none of the 4 files were in scope). Ruling: **delete the guard** in all 4 files (it's now
fully redundant — `build_ai_router_from_settings()`'s `compute_effective_mode`, called one line
later in each function, already silently collapses "cloud mode + no key" to `local`, per
invariant 32 — keeping any form of the old guard would have made it raise in exactly the
scenario invariant 32 says must silently degrade instead). Allowed files widened to add these 4
services, scoped to exactly: deleting the 2-line guard, its "Raises: … not configured" docstring
line, and the now-unused `AIMode` import in each (ruff-flagged, confirmed with `ruff check`) —
plus their test files, only for the guard's own assertions (none asserted the message text
itself via `match="is not configured"`, per the PM's own pre-check, but 3 of the 4 had a
`test_generate_*_missing_api_key_raises_without_calling_router` test whose entire premise — a
missing cloud key must raise — is the guard's exact, now-deleted behaviour; deleted those 3,
not repurposed, since their premise is gone, not just their wording).

**One more test file found during implementation, not in the original enumerated list, and fixed
under the same already-approved "other tests... assert... mode names" carve-out (no new
judgment call — a bare rename, no semantic inversion):** `tests/test_ai_health_api.py` asserts
`"gemini"`/`"hybrid"` as the `mode` field's value in `/api/ai/health` responses, including a PUT
`.../ai-mode` body with `"hybrid"`. Missed it originally because the file title says "health
API," not "settings" — grepping only for `AIMode.GEMINI`/`AIMode.HYBRID` (not plain JSON-body
string literals) missed it, the same way `tests/test_settings_api.py`'s own plain-string PUT
bodies were caught separately. Updated to `"cloud"`/`"cloud_first"`, same as every other file's
treatment; full suite catches it, so it's not silent.

**The PM's required new test** ("with `AI_MODE=cloud_first` and no key, generation proceeds via
the local provider (a fake) and does NOT raise... proves invariant 32 end to end at the service
layer") is `tests/test_script_service.py::test_generate_script_cloud_first_mode_with_no_key_falls_through_to_local_without_raising`
— the one test in this whole task that does **not** inject a `FakeProvider`-backed router (every
other test in these 4 files does); it calls `build_ai_router_from_settings()` for real (no
`router=` argument), with `httpx.MockTransport` patched onto `ollama_provider`'s own
`httpx.AsyncClient` so `OllamaProvider`'s real HTTP call never touches a real network or Ollama
process — proving the full `settings → compute_effective_mode → build_ai_router_from_settings →
AIRouter.generate → OllamaProvider` chain, not just a mocked slice of it.

### 1. Roles, modes, and where the effective mode is computed

`AIRouter.__init__(self, primary: Provider, fallback: Provider, mode: AIMode, failure_threshold=..., cooldown_seconds=..., circuit: CircuitBreaker | None = None)`.
`AIMode` (`contracts.py`) becomes `LOCAL = "local"`, `CLOUD = "cloud"`, `CLOUD_FIRST = "cloud_first"` —
`GEMINI`/`HYBRID` removed (their provider is deleted; keeping a member named `GEMINI` pointing at a
now-generic cloud slot would be actively misleading).

**A pure function computes the effective mode, called by the builder, not by `AIRouter` itself:**
```python
def compute_effective_mode(configured_mode: AIMode, allow_cloud: bool, api_key: str, model: str) -> AIMode:
    if configured_mode is AIMode.LOCAL:
        return AIMode.LOCAL
    if not allow_cloud or not api_key or not model:
        return AIMode.LOCAL
    return configured_mode
```
`AIRouter.mode` is therefore *always already effective* by the time the router exists — `_route()`
never re-derives it, which keeps the three branches (`LOCAL`/`CLOUD`/`CLOUD_FIRST`) simple and
matches today's structure (today's `_route` also just switches on `self._mode` directly).

**Where the setting reaches the router the AIWorker holds (this is the part I want to flag
clearly, since the current code has a real staleness gap):** today, `app/main.py`'s `lifespan`
calls `_build_ai_router()` **once**, at startup, and the resulting `AIRouter` instance is closed
over by `script_pipeline.make_handler(ai_router)` / `learning_pipeline.make_handler(ai_router)`,
which are registered as `AIWorker`'s **permanent** handlers. Both `OllamaProvider` and
`GeminiProvider` freeze their config (`api_key`, `base_url`, `model`) at construction — so even
though `settings_service.set_gemini_api_key`/`set_ai_mode` mutate `config.settings` in place
right now, **that already-built router's providers never see the change**. This isn't a new bug
I'm introducing, but Task 18.3's explicit requirement ("changes take effect without a restart")
and invariant 32 make it a real blocker for 18.2, not a pre-existing curiosity to leave alone.

**Fix: rebuild the router once per job dispatch, not once per app lifetime — but keep the
circuit breaker itself alive for the whole app lifetime, threaded through each fresh build.**
`main.py`'s `_build_ai_router()` factory function is kept (renamed conceptually to "build one
router instance from current settings," same as today), but instead of calling it once in
`lifespan` and handing the *result* to `register_handler`, `lifespan` now registers a **thin
wrapper** that calls `_build_ai_router()` fresh, then delegates:
```python
_circuit = CircuitBreaker(AI_CIRCUIT_FAILURE_THRESHOLD, AI_CIRCUIT_COOLDOWN_SECONDS)  # app-lifetime

def _build_ai_router() -> AIRouter:
    fallback = OllamaProvider(base_url=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL, num_ctx=settings.OLLAMA_NUM_CTX)
    effective_mode = compute_effective_mode(
        AIMode(settings.AI_MODE), settings.AI_ALLOW_CLOUD, settings.OPENAI_COMPAT_API_KEY, settings.OPENAI_COMPAT_MODEL
    )
    primary: Provider = fallback  # placeholder; never called when effective_mode is LOCAL
    if effective_mode is not AIMode.LOCAL:
        try:
            primary = OpenAICompatProvider(
                base_url=settings.OPENAI_COMPAT_BASE_URL, api_key=settings.OPENAI_COMPAT_API_KEY,
                model=settings.OPENAI_COMPAT_MODEL, timeout=settings.AI_CLOUD_DEADLINE_SECONDS,
            )
        except ValueError:
            logger.warning("ai_router_invalid_cloud_base_url -- falling back to local")
            effective_mode = AIMode.LOCAL
    return AIRouter(primary=primary, fallback=fallback, mode=effective_mode, circuit=_circuit)

async def _script_handler(job: dict, worker: "AIWorker") -> None:
    await script_pipeline.make_handler(_build_ai_router())(job, worker)

async def _learning_handler(job: dict, worker: "AIWorker") -> None:
    await learning_pipeline.make_handler(_build_ai_router())(job, worker)

ai_worker.register_handler("script", _script_handler)
ai_worker.register_handler("learning", _learning_handler)
```
This means: (a) every new job reads current settings, so a Settings-page change (18.3) takes
effect on the *next* job with no restart — solves the staleness gap; (b) the circuit breaker
(`CircuitBreaker`, exported from `router.py` — renamed from today's private `_CircuitBreaker`
since it's now constructed outside the package) survives across jobs exactly as it does today
across calls within one job, because the *same* `_circuit` object is passed into every freshly
built router; (c) `AIRouter`'s own constructor is unaffected by this — it still just takes
concrete `primary`/`fallback`/`mode`/optional `circuit`, so every existing test that builds an
`AIRouter` directly (not through `_build_ai_router()`) keeps working with a trivial rename.
`script_pipeline.py`/`learning_pipeline.py` are **not touched** — `make_handler`'s signature and
body are unchanged, this is a `main.py`-only wrapper. The invalid-base-url fallback (`except
ValueError`) is a defensive backstop for a case 18.3's own "test connection" feature should
normally prevent; flagging it since it's a judgment call, not explicitly specified in the plan.

**New `Settings` fields, added here (18.3's allowed files don't include `config.py`/`.env.example`,
so the underlying fields must exist before 18.3 can read/write them via `settings_service.py`):**
- `OPENAI_COMPAT_BASE_URL: str = "https://openrouter.ai/api/v1"` (D22's assumed default provider).
- `OPENAI_COMPAT_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"` (D22's chosen free default).
- `OPENAI_COMPAT_API_KEY: str = ""` (never a non-empty default — matches `GEMINI_API_KEY`).
- `AI_CLOUD_DEADLINE_SECONDS: float = 150.0` (see point 2 for the rationale).
- `ENV_OPENAI_COMPAT_API_KEY` captured once at import time, mirroring `ENV_GEMINI_API_KEY` —
  18.3's future "clear the stored key" needs this same revert-to-env pattern and shouldn't have
  to touch `config.py` itself to get it.
`.env.example` gains `DIE_OPENAI_COMPAT_BASE_URL=`, `DIE_OPENAI_COMPAT_MODEL=`,
`DIE_OPENAI_COMPAT_API_KEY=` (all commented/empty, matching `DIE_GEMINI_API_KEY=`'s style) and an
updated comment on `DIE_AI_MODE` for the new value names.

### 2. Separate time budgets

Today: `generate()` wraps the *entire* `_route()` call (local attempt + Gemini fallback
together) in **one** `asyncio.wait_for(self._route(...), timeout=request.deadline_seconds)` —
exactly how both smoke-test jobs died (the primary ate the whole budget, leaving nothing for the
fallback). Fix: each phase gets its **own** `wait_for`, via a new private helper:
```python
async def _run_with_budget(self, provider: Provider, request: GenerationRequest, budget_seconds: float) -> GenerationResult:
    deadline_at = time.monotonic() + budget_seconds
    try:
        return await asyncio.wait_for(self._attempt(provider, request, deadline_at), timeout=budget_seconds)
    except TimeoutError as exc:
        raise ProviderTimeoutError(f"AI router budget of {budget_seconds}s exceeded for {provider.name}") from exc
```
`_attempt()` itself (retry/backoff loop) is **unchanged** — it already takes a `deadline_at` and
bounds its own backoff against it; only *what budget it's handed* changes.

`generate()`/`_route()`:
- `LOCAL`: `self._run_with_budget(self._fallback, request, request.deadline_seconds)` — **this
  branch is a verbatim copy of today's `AIMode.LOCAL` branch**, just with `self._local` renamed
  to `self._fallback` and the direct `_attempt` call wrapped through the new helper instead of
  inline (behaviour-preserving, not rewritten — see point 7).
- `CLOUD` (diagnostic, no fallback, no circuit interaction — matches today's `AIMode.GEMINI`
  branch exactly): `self._run_with_budget(self._primary, request, AI_CLOUD_DEADLINE_SECONDS)`.
- `CLOUD_FIRST`: circuit open → fallback only (`request.deadline_seconds`, `circuit_open=True`).
  Circuit closed → try primary (`AI_CLOUD_DEADLINE_SECONDS`); on `ProviderError`, record the
  failure (point 3), then fallback (`request.deadline_seconds`), `fallback_used=True`,
  `fallback_reason=type(exc).__name__`.

**`request.deadline_seconds` — meaning changes, value doesn't, so pipeline callers stay
unchanged as asked.** Every existing caller (`script_pipeline.py`, `learning_pipeline.py`, and
the 4 `*_service.py` files) already passes `deadline_seconds=settings.AI_REQUEST_DEADLINE_SECONDS`
into `GenerationRequest`. Under the new design that value becomes **the fallback's own budget**
(and the sole budget in `LOCAL` mode) — exactly the plan's "the fallback gets a fresh
`AI_REQUEST_DEADLINE_SECONDS`" instruction, satisfied by construction with zero caller edits.
Only `GenerationRequest.deadline_seconds`'s **docstring** changes (contracts.py, allowed), not
its name or any caller's value.

**`AI_CLOUD_DEADLINE_SECONDS = 150.0`, rationale:** the smoke test's own conclusion #4 suggests
"about 180s"; the plan's own text says "≈150s". I'm going with the plan's figure (150.0) since
it's the controlling document, but note the tension explicitly rather than silently picking one:
the *default* model (Nemotron 3 Super) measured 8-28s, its larger sibling Ultra measured up to
136s, and the one 296s outlier (nex-agi) isn't the configured default model at all. 150s covers
Ultra's measured worst case with a small margin without being so large that a stuck primary
wastes minutes before falling back. I'll wire `OpenAICompatProvider`'s own `timeout` constructor
arg (18.1's `180.0` placeholder default) to this same `AI_CLOUD_DEADLINE_SECONDS` value in
`_build_ai_router()`, so there's one real source of truth, not two numbers that could drift.

**Flagging a real risk this creates, not fixed here:** a `cloud_first` call's worst-case total
wall time becomes up to `AI_CLOUD_DEADLINE_SECONDS + AI_REQUEST_DEADLINE_SECONDS` ≈ 270s (both
phases can each also spend time on `_attempt`'s own bounded retries within their budget) —
versus today's single ~120s ceiling. `AI_JOB_LEASE_SECONDS = 90` (unchanged, `constants.py`) is
refreshed by explicit `worker.heartbeat(job_id)` calls *between* section/generate calls in
`script_pipeline.py`'s main loop — not *during* one. A single `generate()` call now taking up to
~270s has no heartbeat mid-call, so in principle its lease could go stale before the call
returns. I have not verified whether anything in this single-worker deployment would actually
*act* on that staleness while the same worker is still inside the call (vs. only mattering across
a crash/restart) — flagging it rather than guessing, and not touching `AI_JOB_LEASE_SECONDS`
without your call, since that's a different-shaped concern than this task's router/budget scope.

### 3. Circuit breaker on the primary

`CircuitBreaker` (renamed from `_CircuitBreaker`, otherwise identical: `failure_threshold`,
`cooldown_seconds`, `consecutive_failures`, `opened_until`, `is_open()`, `record_success()`,
`record_failure()`) gains one new method:
```python
def open_immediately(self) -> None:
    """A config error (bad key/model) can't self-resolve on retry -- skip the
    consecutive-failure threshold and open the cooldown window at once."""
    self.consecutive_failures = self.failure_threshold
    self.opened_until = time.monotonic() + self.cooldown_seconds
```
In `_route()`'s `CLOUD_FIRST` branch, on a caught `ProviderError` from the primary:
`isinstance(exc, ProviderAuthError)` → `self._circuit.open_immediately()`; any other
`ProviderError` (the existing transient/content-retry ones) → `self._circuit.record_failure()`
as today. `record_success()` still fires only when the **primary** succeeds (today it only fires
for `self._local`'s success — the role that made a successful call this pass is always the one
the breaker tracks, so this is a rename, not a behaviour change: `if provider is self._primary:
self._circuit.record_success()`, checked inside `_attempt()`'s success path exactly as
`provider is self._local` is checked today).

### 4/5. Per-call metrics — and an open scoping question

`GenerationResult` (contracts.py) gains `fallback_reason: str | None = None`, set in `_route()`
alongside `fallback_used`/`circuit_open` exactly as those two already are — `fallback_reason =
type(exc).__name__` (the class name only, per the plan's explicit "never a message that could
echo a key," matching `transient_errors`' existing same policy one field over).

**Where this needs to land, and the gap I want to flag before implementing:** the plan's
required behaviour #5 says `fallback_used`/`fallback_reason`/`circuit_open` "go into the job
metrics that already exist." That persistence happens in `script_pipeline.py`'s `_call_record`
(and `learning_pipeline.py`'s equivalent) — which already forwards `result.fallback_used` and
`result.circuit_open` into the saved `call` dict, but **neither file is in 18.2's allowed files
list**, and 18.4's allowed files say "`app/services/ai_job_service.py` (read-side aggregate
only)" — read-side, not write-side. So within 18.2's actual scope, I can add `fallback_reason`
to `GenerationResult` and populate it correctly in the router, but I cannot wire it into the
*persisted* job-metrics `call` record without touching a file outside this task's list. Three
options, your call:
(a) leave `fallback_reason` on the transient `GenerationResult` only for this task, and open a
    small follow-up (or amend 18.4's allowed files) to add the one field to `_call_record` in
    both pipeline files;
(b) amend 18.2's own allowed files to add that one line to each `_call_record` (surgical, ~2
    lines total, not a restructuring of either pipeline);
(c) fold it into 18.4 directly (which already needs `fallback_reason` for the fallback-rate
    breakdown, so it has to touch this eventually regardless).
I lean towards (b) — it's the smallest surface, keeps 18.2 self-contained, and doesn't leave a
half-wired field sitting unused for a full extra task — but I'm flagging it rather than silently
picking, since it's a real deviation from the literal allowed-files list either way.

### 6. `GeminiProvider` deletion — files touched (listed before editing, per the plan rule)

**Explicitly allowed by the plan:** `app/services/ai/router.py`, `app/services/ai/contracts.py`,
`app/services/ai/__init__.py`, `app/services/ai/gemini_provider.py` (delete), `app/core/config.py`,
`app/core/constants.py`, `app/main.py` (router builder only), `app/services/settings_service.py`
(mode migration only), `.env.example`, `tests/test_ai_router.py`, `tests/test_ai_providers.py`,
`tests/test_ai_contracts.py`, `CHANGELOG.md`.

**"Other tests" carve-out — construct/assert the Gemini provider or the old mode names:**
- `tests/test_ai_logging.py` — 4× `AIRouter(local=, gemini=, mode=AIMode.HYBRID)`. Needs the
  constructor rename *and* semantic inversion (see below) since these specifically exercise the
  fallback-logging path.
- `tests/test_script_pipeline.py` — `_build_router()` helper (1 line, `AIMode.GEMINI` → `CLOUD`,
  mechanical) + 1 direct `AIMode.HYBRID` construction (needs inversion).
- `tests/test_learning_pipeline.py` — same shape (1 mechanical helper line + 1 inversion).
- `tests/test_script_service.py` — `_gateway_router()` helper + 2 direct constructions, all
  `AIMode.GEMINI` (mechanical: `gemini=` → `primary=`, `local=` → `fallback=`, mode → `CLOUD`).
- `tests/test_learning_service.py` — same `_gateway_router()` pattern + 1 direct construction
  with a `_CapturingProvider()` (mechanical).
- `tests/test_thumbnail_service.py` — `_gateway_router()` helper only (mechanical).
- `tests/test_youtube_service.py` — `_gateway_router()` helper only (mechanical).
- `tests/test_settings_api.py` — `PUT /api/settings/ai-mode` tests currently asserting
  `"gemini"`/`"hybrid"` as valid, storable mode values. These need rewriting to the new mode
  names, plus (new) a case exercising the migration. Its `gemini_api_key`-only tests (CRUD on
  the existing Gemini key setting) are **untouched** — out of scope, 18.3's territory.
- `tests/test_settings_service.py` — every `ai_mode`-specific test (~10, asserting `"gemini"`/
  `"hybrid"` are valid/storable/loadable) needs rewriting to the new names, plus new tests for
  the migration itself (`gemini`→`cloud`, `hybrid`→`cloud_first`, both from env and from a
  DB-stored legacy value, each asserted to log once). Its `gemini_api_key`-only tests are
  **untouched**.

**The "mechanical" vs. "needs inversion" distinction matters and is worth stating plainly:**
under the OLD scheme, `HYBRID` meant "local first, Gemini is the fallback" — so a test's `local=`
FakeProvider held the *primary-attempted-first* outcomes and `gemini=` held the *fallback*
outcomes. Under the NEW scheme, roles invert (D21: cloud first) — the OLD `local=` provider's
role now maps to `fallback=`, and the OLD `gemini=` provider's role now maps to `primary=`. A
test built around `AIMode.GEMINI` (single-provider, no fallback) doesn't have this problem — it's
a pure rename (`gemini=` → `primary=`, mode → `CLOUD`). A test built around `AIMode.HYBRID` does:
its FakeProvider *outcome assignments* (which one gets the success, which gets the failure) must
be swapped, not just the parameter names, to keep testing the same *behaviour* (primary-fails
→ fallback-succeeds, etc.) rather than silently inverting what's being proven. I read every
`HYBRID` test in `test_ai_router.py`/`test_ai_logging.py` before writing this and will re-verify
each one's outcome assignment by hand while rewriting, the same way Task 17.1's carry-cascade
numbers were hand-verified before being trusted.

**Constants and scripts explicitly *not* touched, and why:** `GEMINI_MODEL`,
`GEMINI_MODEL_FALLBACKS`, `GEMINI_MAX_RETRIES`, `GEMINI_RETRY_BASE_DELAY`,
`GEMINI_RATE_LIMIT_RPM` (`app/core/constants.py`) stay, even though `GeminiProvider` itself is
deleted — `scripts/generate_cefr_review_samples.py` and `scripts/generate_sample_episodes.py`
(both outside every task's allowed files so far) import `GEMINI_MODEL`/`GEMINI_RATE_LIMIT_RPM`
directly for their own standalone use, and `tests/test_generate_cefr_review_samples.py` would
catch an import break in the full suite. Only `router.py`'s and `main.py`'s own `GEMINI_MODEL`
imports (used to build the now-deleted `GeminiProvider`) are removed.

### 7. Invariant 32 — proving `local` (no key) is byte-identical to today

Two layers, not just a test:
- **By construction:** the `LOCAL` branch of `_route()` is a verbatim copy of today's
  `if self._mode is AIMode.LOCAL: return await self._attempt(self._local, request, deadline_at)`
  — same single provider, same `_attempt` call, same retry/backoff/circuit-non-interaction
  (`_attempt` only touches the circuit `if provider is self._primary`, so a `LOCAL`-mode call
  through `self._fallback` never records to the breaker at all, exactly as `self._local` never
  interacts with the breaker in `CLOUD`/`GEMINI`-only calls today). The rename
  (`self._local`→`self._fallback`) and the budget-wrapping (`_run_with_budget`, which is
  structurally identical to today's outer `wait_for`, just factored into a helper) are the only
  changes touching this path — not a rewrite.
- **By test:** `compute_effective_mode(AIMode.CLOUD_FIRST, allow_cloud=True, api_key="", model="x")
  == AIMode.LOCAL` (and the `allow_cloud=False` / `model=""` variants) — proves the collapse
  fires correctly. A second test constructs two routers — one via `compute_effective_mode`'s
  collapse (configured `CLOUD_FIRST`, no key), one directly with `mode=AIMode.LOCAL` — runs the
  *same* request through both, and asserts identical `GenerationResult` fields and identical
  `fallback.calls`/`primary.calls` counts (zero primary calls in both) — proving the collapse
  path and the explicit-local path are observably indistinguishable, not just individually
  correct.

## Test plan (new tests, beyond the "other tests" rewrites in point 6)

- `test_compute_effective_mode_*`: local stays local; allow_cloud=false collapses cloud/cloud_first
  to local; empty key collapses; empty model collapses; a configured, fully-enabled cloud/cloud_first
  passes through unchanged.
- `test_router_local_mode_matches_the_effective_local_collapse` (point 7's second proof, above).
- **The required revert-and-confirm-failure target:** "primary exhausts its own budget → the
  fallback still gets its full budget." A slow-but-eventually-successful `FakeProvider` for
  `primary` that consumes most of `AI_CLOUD_DEADLINE_SECONDS` before failing (or a fixed
  `AI_CLOUD_DEADLINE_SECONDS` monkeypatched small in the test, e.g. `0.05`, with the fallback's
  own `AI_REQUEST_DEADLINE_SECONDS` monkeypatched to something clearly larger, e.g. `0.5`) —
  asserts the fallback still gets its own full, undiminished budget and succeeds. Revert: change
  `_run_with_budget` calls back to a single shared `wait_for` around both phases (today's
  behaviour) — re-run → expect failure (the fallback starves). Restore → passes.
- `test_circuit_opens_immediately_on_auth_error` / `test_circuit_records_failure_normally_on_transient_error`.
- `test_fallback_reason_is_the_exception_class_name_not_the_message`.
- `test_legacy_ai_mode_gemini_migrates_to_cloud_from_env` / `..._hybrid_migrates_to_cloud_first_from_env`
  / `..._from_db` (both), each asserting a single log line and no exception.
- `test_set_ai_mode_rejects_gemini_and_hybrid_now` (they're no longer valid *inputs*, only
  migratable *stored* values).
- Full suite, `ruff`, real DB untouched (read-only per invariant 26 — no test in this task's
  scope opens `data/app.db`).

## Verification (required)

See plan §3 "18.2". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

- Design commit `6bc25aa` (APPROVED, plan Amendment A `bf7cdfe`), Amendment B (the 4-service-file
  guard deletion, ruled on mid-implementation, see the Design decisions section above) folded
  into this same implementation commit per the PM's explicit "continue" instruction.
- **Code:**
  - `app/services/ai/contracts.py`: `AIMode` → `LOCAL`/`CLOUD`/`CLOUD_FIRST`;
    `GenerationResult.fallback_reason` added; `deadline_seconds`'s docstring updated for its new
    per-phase meaning.
  - `app/services/ai/router.py`: `compute_effective_mode`; `build_ai_router_from_settings`
    rebuilt around `OpenAICompatProvider`+`OllamaProvider`, takes an optional `circuit`;
    `_CircuitBreaker` → public `CircuitBreaker`, gains `open_immediately()`; `AIRouter`
    constructor renamed `primary`/`fallback`, gains `cloud_deadline_seconds`, `circuit`;
    `generate()`/`_route()` restructured around the new `_run_with_budget()` helper (one
    `wait_for` per phase, not one shared).
  - `app/services/ai/gemini_provider.py`: deleted.
  - `app/core/config.py`: `OPENAI_COMPAT_BASE_URL`/`_MODEL`/`_API_KEY`, `AI_CLOUD_DEADLINE_SECONDS`,
    `ENV_OPENAI_COMPAT_API_KEY`; env-sourced legacy `AI_MODE` migration applied once at import.
  - `app/core/constants.py`: `AI_MODES` → `("local", "cloud", "cloud_first")`;
    `AI_LEGACY_MODE_ALIASES`; `AI_CLOUD_DEADLINE_SECONDS = 150.0`. `GEMINI_*` constants
    untouched (still imported by the two out-of-scope sample scripts).
  - `app/main.py`: router-builder scope widened per Amendment A — `_ai_circuit` (one
    app-lifetime `CircuitBreaker`), `_build_ai_router()` now a thin call into
    `build_ai_router_from_settings(circuit=_ai_circuit)`, `_script_job_handler`/
    `_learning_job_handler` wrapper functions registered instead of a frozen router instance.
  - `app/services/settings_service.py`: `_migrate_legacy_mode()`, applied in
    `get_ai_mode_status`/`load_ai_mode_from_db`; `set_ai_mode`'s docstring/message updated.
  - `app/services/script_pipeline.py`, `learning_pipeline.py`: `_call_record` gains
    `"fallback_reason": result.fallback_reason` / `None` (Amendment A point 4) — no other change.
  - `app/services/script_service.py`, `learning_service.py`, `thumbnail_service.py`,
    `youtube_service.py`: the 2-line `AIMode.GEMINI`/`GEMINI_API_KEY` guard and its docstring
    line deleted (Amendment B); the now-unused `AIMode` import removed from each.
  - `.env.example`: `DIE_OPENAI_COMPAT_BASE_URL`/`_MODEL`/`_API_KEY`,
    `DIE_AI_CLOUD_DEADLINE_SECONDS` added; `DIE_AI_MODE`'s comment updated.
- **Tests touched:** `tests/test_ai_router.py` (rewritten, 18 → 30: every `HYBRID` test
  hand-re-derived for `CLOUD_FIRST`'s inverted roles, not renamed; new
  `compute_effective_mode`/`build_ai_router_from_settings`/circuit-immediate-open/
  separate-budgets coverage), `tests/test_ai_logging.py` (rewritten, semantic inversion),
  `tests/test_ai_providers.py` (Gemini section deleted), `tests/test_ai_contracts.py`
  (mode values, `fallback_reason` default), `tests/test_script_pipeline.py`,
  `tests/test_learning_pipeline.py` (`_build_router` helper mechanical rename + 1 `HYBRID`
  inversion each), `tests/test_script_service.py`, `tests/test_learning_service.py`,
  `tests/test_thumbnail_service.py`, `tests/test_youtube_service.py` (`_gateway_router` helper
  mechanical rename; 3 of the 4 lost their obsolete "missing key raises" test; 1 gained the new
  end-to-end invariant-32 proof), `tests/test_settings_api.py`, `tests/test_settings_service.py`
  (mode names updated; new legacy-rejects-as-input and DB-stored-migration tests, including a
  `caplog`-based "logged once" check), `tests/test_ai_health_api.py` (found during
  implementation, not originally enumerated — see Design decisions).
- **Full suite:** `./venv/Scripts/python.exe -m pytest -q` → **1002 passed** (993 baseline after
  Task 18.1). `ruff check .` → all checks passed. Real DB untouched — every test in this task's
  scope uses the `db` fixture (temp SQLite) or `FakeProvider`/`httpx.MockTransport`, never
  `data/app.db`.
- **Revert-and-confirm-failure** (the PM's specified target): temporarily made `_run_with_budget`
  ignore its `budget_seconds` argument and always use `request.deadline_seconds` (simulating the
  pre-Phase-18 shared-budget behaviour), re-ran
  `test_primary_budget_exhaustion_does_not_starve_the_fallback_budget` alone → failed exactly as
  expected (`AssertionError: assert 'openai_compat' == 'ollama'` — the slow primary's 0.2s
  completed successfully inside the shared 0.5s budget instead of timing out at its own tiny
  0.05s budget and falling back). Restored → the same test and the full file (30 tests) passed
  again; reran the full suite (1002 passed) and `ruff` to confirm no other regression.
