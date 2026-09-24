# Task 18.8 — Multi-provider cloud chain (D28, Amendment E)

- **Status:** done (pending PM ACCEPTED)
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** 18.6 accepted (`a17ca11`); owner decision D28
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.8" (Amendment E),
  invariants 31–35

## Allowed files (proposed — the plan has no explicit list for 18.8; see Q2/Q3 below)

`app/services/ai/router.py`, `app/services/ai/openai_compat_provider.py`,
`app/services/ai/contracts.py` (Q2), `app/main.py` (Q3), `app/core/config.py`,
`app/core/constants.py`, `.env.example`, `app/services/settings_service.py`,
`app/api/settings.py`, `app/models/settings.py`, `app/api/ai_jobs.py` (health payload only),
`frontend/pages/settings.html`, `frontend/static/js/settings.js`, and
`app/services/script_pipeline.py` / `app/services/learning_pipeline.py` (the
`is_primary_result` → `is_cloud_result` rename only, one call site each), plus the matching
tests, `tests/conftest.py` (N1 extension only), and `CHANGELOG.md`.

## Required behaviour (summary; the plan is binding)

1. An ordered provider list (openrouter, opencode-zen, gemini), each with its own circuit.
2. Quota-aware circuits per provider (OpenRouter as in 18.6; Gemini `RESOURCE_EXHAUSTED`; Zen
   generic threshold/cooldown).
3. One bounded total cloud budget (~120s) across the whole chain before local gets its own.
4. Settings: per-provider enable, key, models, order. Health: per-provider circuit state.
5. Record provider + model per call, extend the fallback-rate breakdown by provider.
6. Tests: MockTransport only, N1 extended. Revert checks on chain order and the budget bound.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**PM review — APPROVED, Q1–Q3 accepted as proposed, Q4 ruled with explicit semantics, folded
into this implementation, no re-approval needed:**
- **Q4 ruling:** `circuit_open` = `true` **only** when *every* configured cloud provider is
  currently paused (i.e. the app is really running local-only right now) — not "any provider."
  `circuit_open_until` = the **earliest** reopen time among the paused providers, and **only**
  set in that all-paused case; `null` otherwise (even if some individual providers are paused,
  as long as at least one isn't). Per-provider detail always available under the new
  `"providers": {name: {"configured": bool, "circuit_open": bool, "circuit_open_until":
  iso|null}}`. Settings shows the existing "Cloud paused until HH:MM (free daily limit reached)"
  line only in the all-paused case; otherwise a smaller per-provider note naming which one(s) are
  paused and that the others are covering (e.g. "OpenRouter paused until 07:00; using Zen/
  Gemini"). 18.6's own tests for `circuit_open`/`circuit_open_until` are updated to this new
  meaning (a deliberate, called-out change to a field that shipped one task ago, not a silent
  behavior drift).
- Also accepted as proposed: the instance-level `name`; a 240s worst case; reusing
  `OPENAI_COMPAT_*`/`GEMINI_API_KEY` as-is; `GEMINI_MODEL` defaulting to `gemini-2.5-flash`;
  `cloud_provider_order` as a comma list; deferring `get_fallback_rate_stats`'s per-provider
  breakdown (the PM computes it from Gate B-10's own per-call evidence instead).

**Four questions/flags before I write code (none block the rest of the design below, but I want
these confirmed — three are file-scope additions the plan doesn't explicitly grant, the fourth
is a genuine unknown the plan itself calls out as "will be measured"/PM-probed):**

- **Q1 (unverifiable without a real probe):** the plan states OpenCode Zen's free limits are
  unpublished, and Gemini's is documented-format-only (no real captured 429 body the way 18.6 had
  for OpenRouter, per Amendment D's own evidence). I've built the Gemini daily-quota detector from
  Google's documented `google.rpc.Status`-shaped error convention (`error.status ==
  "RESOURCE_EXHAUSTED"`, HTTP 429) — see point 5 — with a message-substring backstop, same
  defensive-OR pattern as 18.6's OpenRouter detector. This is my best-effort shape, not a
  confirmed-real one; the PM's own pre-Gate-B-10 probe (plan §18.7's "before the gate" step) is
  the actual verification. If the probe finds a different real shape, that's a small follow-up
  fix to one function, not a redesign.
- **Q2 — `GenerationResult` needs a new `providers_tried: list[str]` field** (point 5's "record
  provider + model per call... plus a providers_tried list for telemetry" — see point 4).
  `app/services/ai/contracts.py` has never been in any task's allowed files across this whole
  phase (18.1–18.6 all avoided touching it). Requesting it added, for this one field only.
- **Q3 — `app/main.py` needs to change.** The single app-lifetime `_ai_circuit: CircuitBreaker`
  (18.2/18.6) becomes `_ai_circuits: dict[str, CircuitBreaker]`, keyed by provider name, still
  threaded through every per-job-dispatch router rebuild the same way. This is the only place an
  app-lifetime holder for *multiple* circuits (one that survives across a job's router being
  rebuilt on every dispatch) can live — `router.py` itself is rebuilt fresh per call by
  `build_ai_router_from_settings`, so it can't hold this state between calls on its own.
  Requesting `app/main.py` added, for this one variable and its use in `_build_ai_router()`.
- **Q4 — restructuring 18.6's just-shipped `circuit_open`/`circuit_open_until`.** They're
  singular (one circuit's worth), shipped in `a17ca11`, not yet depended on by anything external.
  My plan (point 6) keeps them as an *aggregate* (true / soonest-reopen across any open provider)
  and adds a new per-provider `providers: {name: {...}}` breakdown alongside — additive in
  spirit, but the top-level fields' *meaning* shifts from "the one circuit" to "any circuit."
  Flagging this explicitly since it's a real (if small) behavior change to a field that shipped
  one task ago.

### 1. `ChainEntry` and `AIRouter`'s new shape (point 1)

```python
@dataclass
class ChainEntry:
    name: str            # "openrouter" | "opencode-zen" | "gemini" -- the SAME string used as
                          # the circuits-dict key, the Settings row identifier, and (by
                          # construction, see point 5) provider.name, so a call's telemetry,
                          # its circuit, and its Settings row are always the same string.
    provider: Provider
    circuit: CircuitBreaker
```

`AIRouter.__init__(self, chain: list[ChainEntry], fallback: Provider, mode: AIMode, ...)`
replaces the singular `primary: Provider`/`circuit: CircuitBreaker | None` params entirely (not
additive — every existing single-provider caller/test in 18.1–18.6 already goes through
`build_ai_router_from_settings`, which becomes the one place that adapts "the configured
providers" into a `chain`, so nothing outside `router.py` + that factory needs to know the shape
changed). `AIMode.LOCAL`'s branch is untouched (`_run_with_budget(self._fallback, ...)`, no
chain involved at all).

### 2. Circuits: one dict, app-lifetime, keyed by provider name (Q3)

`app/main.py`:
```python
_ai_circuits: dict[str, CircuitBreaker] = {}
```
Empty at startup — grows on demand, not pre-populated with a hardcoded provider-name list (so a
provider a user disables/never configures never gets a breaker object sitting around unused, and
nothing here needs updating if a provider is ever added/removed later). `_build_ai_router()`
passes `circuits=_ai_circuits` (the same dict object, mutated in place) instead of today's single
`circuit=_ai_circuit`.

`build_ai_router_from_settings(circuits: dict[str, CircuitBreaker] | None = None)`: for each
*configured* provider (has a key — an unconfigured one is skipped entirely, point 1's "no key ->
skipped silently"), gets its breaker via `circuits.setdefault(name, CircuitBreaker(AI_CIRCUIT_
FAILURE_THRESHOLD, AI_CIRCUIT_COOLDOWN_SECONDS))` when `circuits` is given, else a fresh one per
call (matching today's "no circuit passed -> fresh per call" default for the four `*_service.py`
one-off callers, unchanged).

### 3. Dispatch logic for `cloud_first`/`cloud` (points 1, 3)

```python
AI_TOTAL_CLOUD_BUDGET_SECONDS = 120.0  # new constant, app/core/constants.py
```

```
total_deadline = now() + AI_TOTAL_CLOUD_BUDGET_SECONDS
tried: list[str] = []
last_error: ProviderError | None = None

for entry in chain:                                  # chain already excludes unconfigured entries
    if entry.circuit.is_open():
        continue
    remaining_total = total_deadline - now()
    if remaining_total <= 0:
        break
    entry_budget = min(AI_CLOUD_DEADLINE_SECONDS, remaining_total)   # 75s cap, per point 3
    try:
        result = await self._run_with_budget(entry.provider, request, entry_budget)
    except ProviderError as exc:
        tried.append(entry.name)
        last_error = exc
        _update_circuit(entry.circuit, exc)           # daily-quota -> open_until; auth ->
        continue                                       # open_immediately; else -> record_failure
    entry.circuit.record_success()
    tried.append(entry.name)
    result.providers_tried = tried
    return result

# chain exhausted, or the total budget ran out
if self._mode is AIMode.CLOUD:                        # no local fallback -- diagnostic mode
    raise last_error or ProviderUnavailableError("no cloud provider configured or all failed")
result = await self._run_with_budget(self._fallback, request, request.deadline_seconds)
result.fallback_used = True
result.fallback_reason = type(last_error).__name__ if last_error else "no_cloud_provider_configured"
result.providers_tried = tried
return result
```

**Worst-case added latency before local, stated explicitly (point 3's requirement):** bounded by
`AI_TOTAL_CLOUD_BUDGET_SECONDS` = **120s, never more** — each entry's budget is `min(75,
remaining_total)`, so the loop can never spend more than the total budget across however many
entries it tries (one 75s entry plus a partial ~45s second entry is the realistic worst case for
today's 3-provider chain; a 4th entry would get 0s remaining and be skipped). Local then gets its
own **separate, fresh** `request.deadline_seconds` (today's `AI_REQUEST_DEADLINE_SECONDS`,
120s) — never shared with the cloud budget, same "two budgets never share one deadline"
principle Phase 18 established for the single-primary case, now applied at the chain level.
Worst-case total: 120s (cloud, all entries) + 120s (local) = 240s for one call, an increase from
today's single-primary worst case of 75s (cloud) + 120s (local) = 195s — a real, stated
regression in the *worst* case, traded for the *typical* case improving a lot (an unhealthy
provider's circuit opens after its first failure and is skipped on every subsequent call, so the
worst case is rare in practice, hit only when multiple providers fail on the very same request).

### 4. `is_cloud_result` (point 5, replaces 18.6's `is_primary_result`)

```python
def is_cloud_result(self, result: GenerationResult) -> bool:
    return self._mode is not AIMode.LOCAL and result.provider in {entry.name for entry in self._chain}
```
Same LOCAL-mode-placeholder concern 18.6's C2 raised, generalized: `_call_router`'s call sites in
`script_pipeline.py`/`learning_pipeline.py` rename `router.is_primary_result(result)` to
`router.is_cloud_result(result)` — the one-line rename is the only change needed in those two
files (the retry-on-malformed-JSON logic itself, item 4 from 18.6, is otherwise untouched).

### 5. Provider identity: `OpenAICompatProvider.name` becomes per-instance (point 5)

**Found while designing, not in the plan's own text:** `OpenAICompatProvider.name = "openai_compat"`
is a *class* attribute today — every instance (openrouter, zen, gemini) would report the exact
same `.name`, making per-provider telemetry (point 5's "record provider + model per call") and
`is_cloud_result`'s set-membership check both impossible to implement correctly. Fix:
`__init__` gains `name: str = "openai_compat"` (instance attribute, same default as today =
fully backward compatible with every 18.1–18.6 test that never passes it).
`build_ai_router_from_settings` constructs each chain entry as `OpenAICompatProvider(...,
name="openrouter")` / `OpenAICompatProvider(..., name="opencode-zen")` / `OpenAICompatProvider(...,
name="gemini")` — the same string as `ChainEntry.name` and the circuits-dict key, always.

### 6. Per-provider daily-quota detection (point 2)

`OpenAICompatProvider.__init__` gains `vendor: str = "generic"` (`"openrouter" | "gemini" |
"generic"`). `_daily_quota_reset_epoch_seconds` dispatches on it:
- **`"openrouter"`:** unchanged from 18.6 (`metadata.limit_source == "openrouter_free_tier_daily"`
  OR the `free-models-per-day` message substring), reset from `X-RateLimit-Reset`.
- **`"gemini"`** (Q1 — best-effort, PM probe confirms before Gate B-10): HTTP 429 with
  `error.status == "RESOURCE_EXHAUSTED"` (Google's standard `google.rpc.Status` error shape) OR
  the message containing `"RESOURCE_EXHAUSTED"`/`"exhausted"` as a backstop. Reset: the next
  midnight **America/Los_Angeles** (`zoneinfo.ZoneInfo`, per the plan and Google's documented
  Pacific-time quota reset), still passed through the same 26h cap (18.6 C3) as a backstop
  against a DST-transition edge case or a bad detection.
- **`"generic"`** (Zen, unpublished limits): no vendor-specific detection at all — every 429
  raises the plain `ProviderRateLimitError` exactly as OpenRouter itself did *before* 18.6, so
  Zen's circuit opens only via the ordinary `record_failure()` threshold/cooldown path (point 2's
  "anything else uses the threshold/cooldown path").

`build_ai_router_from_settings` passes `vendor="openrouter"` for the openrouter entry,
`vendor="gemini"` for gemini, `vendor="generic"` (the default) for opencode-zen.

### 7. Settings + migration (point 4, and the migration note requested)

**Migration:** the existing `OPENAI_COMPAT_BASE_URL`/`_MODEL`/`_API_KEY`/`_FALLBACK_MODELS`
settings are **not renamed or moved** — they become the `"openrouter"` chain entry's config
as-is, read exactly where they are today. Gemini reuses the *already-existing* `GEMINI_API_KEY`
field (present since before Phase 18, left deliberately unused-but-readable by Amendment B) and
reactivates the *already-present-but-dead* `DIE_GEMINI_MODEL` env var (`.env.example` has had
this line since before Phase 18; `Settings` never declared a matching field, so pydantic-settings
silently ignored it under `extra="ignore"` — this task adds `GEMINI_MODEL: str` to `Settings` for
real). Only OpenCode Zen is genuinely new: `OPENCODE_ZEN_BASE_URL` (default
`https://opencode.ai/zen/v1`), `OPENCODE_ZEN_API_KEY` (new), `OPENCODE_ZEN_MODEL` (blank default
until the PM's probe picks one). A new `GEMINI_BASE_URL` setting is added too (defaulting to
`https://generativelanguage.googleapis.com/v1beta/openai`) for consistency — every provider's
base URL is Settings-editable, none hardcoded only in Python, matching OpenRouter's own existing
pattern.

**Order/enable:** one new `app_settings` key, `cloud_provider_order`, a comma-separated list of
enabled provider names in dispatch order (e.g. `"openrouter,gemini"` to disable Zen and put
Gemini second) — mirrors 18.6's `OPENAI_COMPAT_FALLBACK_MODELS` comma-list precedent exactly
(same parse/validate/store shape, reusing `parse_fallback_models`-style splitting). Default order
`"openrouter,opencode-zen,gemini"` (Amendment E's own listed order). A provider omitted from the
list is simply not dispatched (equivalent to "disabled") — no separate boolean needed.

**Settings page:** one row per provider (3 fixed rows, not a dynamic add/remove table — matches
this Settings page's existing minimal-text-input style, no drag-and-drop): base URL, model(s)
(comma list, reusing 18.6's fallback-models input component), and a write-only key field with
last-4 status, one set per provider. A single `#cloud-provider-order` text input (comma-separated
names, same UI pattern) controls enable+order together.

### 8. Health: per-provider circuit state (point 4, Q4 ruling)

`GET /api/ai/health` gains `"providers": {"openrouter": {"configured": bool, "circuit_open":
bool, "circuit_open_until": iso|null}, "opencode-zen": {...}, "gemini": {...}}` — always present,
per configured-or-not provider (an unconfigured provider still gets an entry, `configured:
false`, `circuit_open: false`, `circuit_open_until: null` — never silently omitted).

**Q4 ruling — `circuit_open`/`circuit_open_until` (18.6) are re-derived, not "any provider":**
- `circuit_open` = `true` only when **every configured** provider's circuit is currently open
  (the app is genuinely running local-only right now). An unconfigured provider doesn't count
  either way — if the only configured provider is paused, that's "all paused," `true`.
- `circuit_open_until` = the **earliest** `circuit_open_until` among the paused providers, set
  **only** in that all-paused case; `null` whenever at least one configured provider is still
  available (even if others are individually paused).

This is a genuine, deliberate change to what these two field names mean, not an additive
extension — 18.6's own health/browser tests for them are updated in this task to the new
semantics (their old assertions, e.g. "any open circuit makes `circuit_open` true," are wrong
under the new meaning and are rewritten, not left stale).

Settings page: the existing "Cloud paused until HH:MM (free daily limit reached)" line is shown
only in the all-paused case (reading the same aggregate `circuit_open_until`). Otherwise, when at
least one provider is up but one or more individually aren't, a smaller per-provider note names
them, e.g. "OpenRouter paused until 07:00; using Zen/Gemini" — built client-side from the
`providers` breakdown (which providers are both configured and paused, versus configured and
not).

### 9. Telemetry: `providers_tried` (point 5, Q2)

`GenerationResult.providers_tried: list[str] = Field(default_factory=list)` — every provider name
attempted for this call, in order, including the eventual winner (empty when nothing was tried,
e.g. `AIMode.LOCAL`). `_call_record` (both pipeline files, already touched for the `is_cloud_
result` rename) adds `"providers_tried": result.providers_tried if result else None` to the safe
call-record shape (a list of provider name strings only — never a response body, matching every
other field there). Task 18.4's fallback-rate readout is **not** changed by this task (out of
scope here) — the plan's "extend the fallback-rate breakdown by provider" is left as a follow-up
read-side aggregate change (a small addition to `ai_job_service.get_fallback_rate_stats`,
deliberately not bundled into this already-large task; flagging it rather than silently dropping
it).

### 10. N1 extension (point 6)

`tests/conftest.py`'s `_neutralize_cloud_config()` gains, alongside the existing
`OPENAI_COMPAT_API_KEY`/`_BASE_URL`/`GEMINI_API_KEY` neutralization:
- `config.settings.OPENCODE_ZEN_API_KEY = ""`
- `config.settings.OPENCODE_ZEN_BASE_URL = "https://opencode-zen.invalid/v1"`
- `config.settings.GEMINI_BASE_URL = "https://gemini.invalid/v1beta/openai"` (new setting, point 7)

`GEMINI_API_KEY` is already blanked by the existing line — confirmed still correct and sufficient
for this task, no change needed there.

### 11. Tests (point 6)

MockTransport only throughout. Chain order (configured entries dispatched in the stored order,
an unconfigured one skipped silently, a mid-chain success stops iteration); each entry's circuit
independent (one provider's circuit opening never affects another's); the Gemini `RESOURCE_
EXHAUSTED` fixture (built from the documented shape, Q1's caveat noted in the test's own
docstring, a synthetic reset date); Zen's generic 429 gets ordinary threshold/cooldown, not a
daily-quota classification; skip-when-no-key (each provider independently, and the "no cloud
provider configured at all" -> local-immediately case); the total-budget bound (multiple slow/
failing entries in sequence, asserting the loop stops once the total budget is spent, never
exceeding it, using a fake clock the same way 18.6's `CircuitBreaker` tests monkeypatch `time.
monotonic`); `providers_tried` correctness (empty, one entry, multiple). Revert checks on chain
order (temporarily ignore the stored order, confirm the order-assertion test fails) and the
budget bound (temporarily drop the `min(..., remaining_total)` cap, confirm the bound test
fails).

## Verification (required)

Full suite, `ruff`, revert-and-confirm-failure on chain order and the budget bound, real DB
untouched.

## Amendment F (PM, mid-implementation; owner's real provider probe)

Arrived after the design above was approved and implementation was already underway (the base
architecture -- `ChainEntry`, `is_cloud_result`, the per-instance provider `name`, the 26h cap,
the Q4 health semantics -- was unaffected; only defaults and Gemini's error handling changed):

1. **OpenCode Zen not in the default order.** Its free tier returned 403 "can only be used from
   within OpenCode" for 6/7 real probed models -- its terms restrict it to that client. The
   generic provider machinery (`vendor="generic"`) is unchanged and still usable if a user adds
   `"opencode-zen"` to `CLOUD_PROVIDER_ORDER` by hand; `CLOUD_PROVIDER_ORDER`'s default became
   `"openrouter,gemini"` (was `"openrouter,opencode-zen,gemini"`). No header/user-agent anywhere
   mimics the OpenCode client.
2. **Gemini defaults + real multi-model structure.** `gemini-2.5-flash` (the original design's
   default) is 404 "no longer available." Real probe results: `gemini-3.1-flash-lite` (201/200
   words, 4s) then `gemini-flash-lite-latest` (182/200, 2.3s) -- both free-tier limits are per
   *model* per project, so Gemini dispatches as **multiple** chain entries sharing one key, each
   with its own circuit (a structural change from the original single-`"gemini"`-entry design):
   new `GEMINI_MODELS` (comma list, replacing a planned singular `GEMINI_MODEL`) expands into one
   `ChainEntry` per model, named after the model id itself (so telemetry/circuits are addressed
   by e.g. `"gemini-3.1-flash-lite"`, not a generic `"gemini"`).
3. **Gemini error handling, from real responses:** `NOT_FOUND`/404 -> config error (already
   handled by the existing generic 401/402/403/404 branch, unchanged); `UNAVAILABLE`/503 ->
   transient (already handled by the existing generic 5xx branch, unchanged);
   `RESOURCE_EXHAUSTED`/429 -> daily quota until the next midnight PT (the Gemini vendor detector
   already built for this). New: some real Gemini error bodies wrap the error object in a JSON
   array (`[{"error": {...}}]`) instead of the plain `{"error": {...}}` every other upstream
   uses -- a new `_unwrap_error_body` helper normalizes both shapes, applied everywhere an error
   body is parsed (`_error_message`, the 200-with-error-body branch, the daily-quota detector),
   not just the Gemini path, since nothing about the fix is Gemini-specific.
4. **Default chain:** `openrouter → gemini-3.1-flash-lite → gemini-flash-lite-latest → local
   qwen`.

## Evidence

- Design commits `cc36c46` (initial) + `f9b89d6`/`5484383` (APPROVED, Q1-Q3 accepted, Q4 ruled),
  this implementation commit folds Amendment F in too, per "no re-approval needed."
- **Code:**
  - `app/services/ai/contracts.py` (Q2): `GenerationResult.providers_tried: list[str]`.
  - `app/services/ai/openai_compat_provider.py`: `name`/`vendor` constructor params (instance-
    level `name`, default `vendor="openrouter"` for full backward compat with every 18.1-18.6
    test); `_daily_quota_reset_epoch_seconds` dispatches on `vendor` to
    `_openrouter_daily_quota_reset` (unchanged logic) or `_gemini_daily_quota_reset`
    (`RESOURCE_EXHAUSTED`, next midnight America/Los_Angeles via `zoneinfo`); new
    `_unwrap_error_body` (Amendment F) normalizes both `{"error": {...}}` and
    `[{"error": {...}}]` shapes, applied in `_error_message`, the 200-with-error-body branch, and
    the daily-quota detector.
  - `app/services/ai/router.py`: new `ChainEntry(name, provider, circuit)`; `AIRouter.__init__`
    accepts `chain=` (the real shape) or `primary=`/neither (a genuine single-entry convenience,
    not a compat shim -- every router-mechanics test keeps working unchanged); `generate()`
    walks the chain respecting each entry's circuit, a shared `total_cloud_budget_seconds`
    (`entry_budget = min(cloud_deadline_seconds, remaining_total)`), and records `providers_
    tried`; `AIMode.CLOUD` raises the chain's last error instead of falling back;
    `is_cloud_result` (renamed from 18.6's `is_primary_result`) checks membership across the
    whole chain; `_run_with_budget`/`_attempt` take an explicit `circuit` param instead of
    comparing `provider is self._primary`. `compute_effective_mode` generalized to
    `any_provider_configured: bool` (was a single api_key/model pair). New
    `_configured_cloud_provider_names`/`_configured_chain_entry_names`/`_build_chain_entries`
    (Gemini expands into one entry per `GEMINI_MODELS` entry, Amendment F)/`_chain_entry`.
  - `app/main.py` (Q3): `_ai_circuit: CircuitBreaker` -> `_ai_circuits: dict[str, CircuitBreaker]`
    (starts empty, grows on demand); `_build_ai_router()` passes `circuits=_ai_circuits`; startup
    `lifespan` gains `load_provider_chain_from_db`.
  - `app/core/constants.py`: new `AI_TOTAL_CLOUD_BUDGET_SECONDS = 120.0`.
  - `app/core/config.py`/`.env.example`: new `OPENCODE_ZEN_BASE_URL`/`_API_KEY`/`_MODEL`,
    `GEMINI_BASE_URL`, `GEMINI_MODELS` (Amendment F; default `gemini-3.1-flash-lite,gemini-
    flash-lite-latest`), `CLOUD_PROVIDER_ORDER` (Amendment F default `"openrouter,gemini"`);
    `ENV_OPENCODE_ZEN_API_KEY` capture, matching `ENV_GEMINI_API_KEY`/`ENV_OPENAI_COMPAT_API_KEY`.
  - `app/services/settings_service.py`: `get_provider_chain_status`, `set_opencode_zen_settings`/
    `clear_opencode_zen_api_key`, `set_gemini_settings`/`clear_gemini_cloud_api_key` (deliberately
    not named `clear_gemini_api_key` -- Task 18.3 deleted that name; a regression test guards
    against ever reintroducing it), `set_cloud_provider_order`, `load_provider_chain_from_db`.
    New `app_settings` keys prefixed `cloud_provider_...` (never reusing any pre-18.3 legacy key
    name). `compute_effective_mode_and_reason` updated for the new `compute_effective_mode`
    signature.
  - `app/models/settings.py`: `OpenCodeZenSettingsUpdate`, `GeminiSettingsUpdate`,
    `CloudProviderOrderUpdate`.
  - `app/api/settings.py`: `GET /api/settings` merges in `get_provider_chain_status`; new
    `PUT`/`DELETE` routes for `/cloud/opencode-zen`, `/cloud/gemini`, `PUT /cloud/order`.
  - `app/api/ai_jobs.py`: health gains a per-provider `"providers"` breakdown; `circuit_open`/
    `circuit_open_until` re-derived per the Q4 ruling (all-configured-providers-paused, earliest
    reopen) instead of one circuit's state.
  - `frontend/pages/settings.html`/`settings.js`: new Gemini and OpenCode Zen provider cards, a
    provider-order field, and `renderCircuitStatus` updated for the Q4 aggregate-vs-per-provider
    wording.
  - `app/services/script_pipeline.py`/`learning_pipeline.py`: `is_primary_result` ->
    `is_cloud_result` rename (one call site each); `_call_record` gains `providers_tried`.
  - `tests/conftest.py`/`tests/test_cloud_config_isolation.py` (N1 extension): `GEMINI_API_KEY`'s
    comment updated (no longer "nothing reads it" -- Gemini chain entries now do), plus
    `GEMINI_BASE_URL`, `OPENCODE_ZEN_API_KEY`/`ENV_OPENCODE_ZEN_API_KEY`/`OPENCODE_ZEN_BASE_URL`
    neutralized the same way; the guard test extended with matching length-only assertions and
    forbidden-pattern entries (PM review N2's no-secret-in-assertion-output discipline preserved).
- **Tests (47 new, 1159 total):**
  - `tests/test_ai_router.py` (+11 new, ~15 existing rewritten for the new constructor/attribute
    shape): chain order, circuit independence, all-fail-falls-back-with-last-error,
    `circuit_open`'s all-paused-only meaning, `AIMode.CLOUD`'s no-fallback behavior, the total
    budget capping a later entry's per-call budget and skipping entries once exhausted,
    `providers_tried` in LOCAL mode. `compute_effective_mode`'s parametrize table and the
    `build_ai_router_from_settings` circuit-sharing tests updated for the new signatures/shapes.
  - `tests/test_openai_compat_provider.py` (+8): Gemini `RESOURCE_EXHAUSTED` (dict and
    array-wrapped shapes), the next-midnight-Los-Angeles reset, `NOT_FOUND`/`UNAVAILABLE` via the
    existing generic branches, a `vendor="generic"` regression guard (an OpenRouter-shaped body
    must NOT be classified as daily-quota for Zen), array-unwrap on a 5xx and a 200 body.
  - `tests/test_settings_service.py` (+17) / `tests/test_settings_api.py` (+9): Zen/Gemini/order
    CRUD, validation, the `clear_gemini_api_key`-is-gone-but-`clear_gemini_cloud_api_key`-exists
    regression guard, `effective_mode` matching when only Gemini (not OpenRouter) is configured.
  - `tests/test_ai_health_api.py` (rewritten for Q4): all-paused-is-true (single configured
    provider), the central two-provider case (one paused, one not -> `circuit_open` stays false,
    per-provider breakdown shows each correctly).
  - `tests/test_settings_browser.py` (+2): the Gemini form round-trip, the provider-order field
    round-trip.
- **Revert-and-confirm-failure:**
  - Chain order: reversed `for entry in self._chain:` to `reversed(self._chain)` ->
    `test_chain_tries_entries_in_order_and_stops_at_the_first_success` failed (`'e3' == 'e2'`,
    wrong entry won); restored, 56/56 router tests passed again.
  - Total budget bound: `entry_budget = min(self._cloud_deadline_seconds, remaining_total)` ->
    `entry_budget = self._cloud_deadline_seconds` (ignoring the shrinking remaining budget) ->
    `test_total_cloud_budget_caps_a_later_entrys_per_call_budget` failed (the second entry got
    its full generous per-entry budget and succeeded instead of timing out under the shrunk
    total); restored, 56/56 passed again.
- **Full suite:** **1159 passed** (1112 baseline + 47 new). `ruff check .` -> all checks passed.
  Real DB untouched throughout (the conftest guard never tripped).

_pending_
