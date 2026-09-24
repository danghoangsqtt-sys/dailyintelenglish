# Task 18.3 — Settings (key/URL/model, test connection), health fields, privacy note

- **Status:** done
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** 18.2 accepted
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.3", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.3", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

The Settings API and page hold base URL, model and a write-only key (status: set + last 4 characters; clearable), a mode selector, a Test-connection button, and the privacy note. DB values override the `.env` defaults and take effect without a restart. The old `gemini_api_key` row is ignored. `/api/ai/health` adds `cloud_configured`, `cloud_model`, `effective_mode` and `circuit_open`, with no key material.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**PM review — APPROVED with three changes (C1, C2, C3), folded into this implementation, no
re-approval needed:**
- **C1:** dropped the regex-based HTTP-status extraction from `OpenAICompatProvider`'s exception
  *message* text; instead `OpenAICompatProvider` (Task 18.1's own file, added to this task's
  allowed files for this one attribute) now sets a structured `upstream_status: int | None`
  instance attribute directly on every exception it raises (its own `_raise()` helper, extended
  with a `cause` param along the way to keep `raise ... from exc` chaining clean). Deliberately
  not `ProviderError.status_code` (that field already means the HTTP status *this app's own API*
  returns, a different thing). `test_cloud_connection` reads `getattr(exc, "upstream_status",
  None)`. One assertion per existing 18.1 error-mapping test now checks `upstream_status` too.
- **C2:** `set_cloud_settings` validates fully before any write — `base_url` through
  `validate_openai_compat_base_url` (https-or-loopback, no credentials), `model` non-empty after
  `.strip()` and ≤ 200 chars, a provided `api_key` non-empty after `.strip()`. Invalid input
  raises `ValidationError` (422 via the existing envelope) with nothing stored; tested explicitly
  (prior values unchanged after a rejected update, both at the service and API layers).
- **C3:** `GET /api/settings` gained `effective_mode`/`effective_reason` (reusing `router.
  compute_effective_mode` via a new `settings_service.compute_effective_mode_and_reason`, never
  touching key material) — the page shows the effective mode next to the selected one, with a
  reason ("no API key configured" / "cloud disabled by DIE_AI_ALLOW_CLOUD") whenever they
  differ. Browser test covers the PM's exact scenario: select cloud_first with no key → shows
  effective Local with the "no API key" reason.

**Amendment C folded in:** `app/core/config.py`/`.env.example` gain the one `AI_ALLOW_CLOUD`
default flip (`False` → `True`) and its comment, nothing else in those files. `AI_MODE` stays
defaulting to `"local"` — untouched here, flips to `"cloud_first"` only at Phase 18 close-out
after Gate B-9 passes.

**Current state, read before designing (matters — it's not what "Task 12.1" might suggest):**
Task 14.7 (ADR-001 A2, local-only release path) already stripped the Settings page down to a
*read-only* AI-mode status line — `frontend/pages/settings.html`/`settings.js` have no key
input, no mode selector, no test-connection button at all today. This task is not "extend an
existing form," it's building the interactive Settings UI from that stripped-down baseline.

### 1. Storage and the overlay-to-next-job path

Same `app_settings` key/value table (`004_app_settings.sql`, no new migration — a plain KV table
was deliberately built for exactly this), three new rows: `openai_compat_base_url`,
`openai_compat_model`, `openai_compat_api_key`. Same DB-overrides-env precedence and
mutate-`config.settings`-in-place pattern `set_ai_mode`/`set_gemini_api_key` already established:
a `set_cloud_settings(db, base_url, model, api_key=None)` writes the DB row(s) and immediately
sets `config.settings.OPENAI_COMPAT_BASE_URL`/`_MODEL`/`_API_KEY` in place — no new propagation
mechanism needed, since 18.2's `_build_ai_router()` (`app/main.py`) already rebuilds a fresh
router from live `settings.*` **on every job dispatch** (not once at startup). A change made
through Settings is picked up by the very next job with zero restart, exactly the same way an
`AI_MODE` change already is. `load_cloud_settings_from_db(db)` mirrors `load_ai_mode_from_db`,
called once from `app.main`'s `lifespan` (startup-loading scope, allowed).

`api_key=None` in `set_cloud_settings` means "don't change the stored key" — lets a user update
just the base URL or model without re-entering the key (the key field is write-only/masked, so
forcing re-entry on every unrelated change would be poor UX). Empty string `""` is rejected
(`ValidationError`, same as the old Gemini-key setter), distinct from `None`/omitted.

### 2. Key handling

Write-only. `get_cloud_settings_status(db)` returns `{"cloud_configured": bool, "cloud_last4":
str | None, "cloud_source": "database" | "env" | "none", "cloud_base_url": str, "cloud_model":
str}` — `base_url`/`model` aren't secret, returned in full; only the key is ever masked, and only
to its last 4 characters (no prefix, unlike the old Gemini `_mask()`'s 6-char-prefix format —
matching the plan's literal `{set, last4, source}` shape, not reusing `_mask()`). A new
`_last4(key: str) -> str` helper (`"•" * max(0, len(key) - 4) + key[-4:]` for len > 4, fully
masked for shorter). `clear_cloud_api_key(db)` deletes the `openai_compat_api_key` row only
(base_url/model rows untouched) and reverts `config.settings.OPENAI_COMPAT_API_KEY` to
`config.ENV_OPENAI_COMPAT_API_KEY` (already captured in `config.py` during Task 18.2, exactly
mirroring `ENV_GEMINI_API_KEY`'s existing pattern). Never returned by any endpoint, never logged
(matches `OpenAICompatProvider`'s own `_redact` invariant 31 backstop — this is the second layer,
at the settings-storage boundary, not a substitute for it), never in `/api/ai/health`.

### 3. The old Gemini settings: removed, not migrated

Per the plan ("ignored and never reused... removed from the UI and API") and the PM's own
Amendment-B-era note ("18.3 retires the settings side and `check_dependencies`"), this task
**deletes** the old Gemini-key settings surface, not just stops calling it:
- `app/api/settings.py`: `PUT /api/settings` (the old `update_gemini_api_key`) and
  `DELETE /api/settings/gemini-api-key` routes are removed. `GET /api/settings` stops merging in
  `gemini_status` — the response is `ai_mode`/`ai_mode_source` (unchanged) plus the new cloud
  status fields (point 2) only.
- `app/services/settings_service.py`: `get_gemini_api_key_status`, `set_gemini_api_key`,
  `clear_gemini_api_key`, `load_gemini_api_key_from_db`, `_mask`, `GEMINI_API_KEY_SETTING` are
  deleted (nothing left calls them once the routes and the startup loader call site are gone).
- `app/models/settings.py`: `GeminiApiKeyUpdate` deleted.
- `app/main.py` (startup loading only, allowed): the `await
  settings_service.load_gemini_api_key_from_db(...)` call in `lifespan` is removed (replaced by
  `load_cloud_settings_from_db`).
- `settings.GEMINI_API_KEY`/`config.ENV_GEMINI_API_KEY` themselves are **not** touched (outside
  `config.py`'s one allowed `AI_ALLOW_CLOUD` line) — `scripts/generate_cefr_review_samples.py`
  (out of scope for every task so far) still reads `settings.GEMINI_API_KEY` directly. This
  leaves that one field readable-but-unused by the active app, which is fine: it was already
  true in practice, just not yet formalized by deleting the app-facing plumbing around it.

### 4. Test connection

`POST /api/settings/cloud/test-connection`, body `{base_url: str, model: str, api_key: str |
None}` (all three optional/nullable — an omitted field falls back to the *currently effective*
`settings.OPENAI_COMPAT_*` value, so a user can test "does my saved key still work with this new
model" without retyping the key, or "is this base URL even reachable" with their saved key
as-is). Never persists anything — a pure probe.

Constructs one `OpenAICompatProvider(base_url=..., api_key=..., model=..., timeout=15.0)`
directly (no `AIRouter` — a raw diagnostic probe, not a routed call; 15s: generous for a live
button click, far short of the 150s job budget) and calls `.generate()` once with a minimal
`GenerationRequest(prompt="Reply with the single word: ok.", deadline_seconds=15.0,
purpose="settings_test_connection")`. On success: `{"ok": true}`. On `ProviderError`: `{"ok":
false, "error": type(exc).__name__, "status": <int | None>}` — never the key, never the response
body/message text.

**The HTTP status extraction, explicit since it's a real design choice:** `OpenAICompatProvider`'s
own exceptions don't carry a structured status code today (Task 18.1 baked it into the message
text via `_format_error`, e.g. `"... (HTTP 401, code=401): ..."`). Rather than widen this task's
allowed files to add a `status_code` attribute to `ProviderError`/`OpenAICompatProvider` (a
plausible alternative, but out of scope today), this handler extracts it with a small, tightly
-scoped regex (`re.search(r"HTTP (\d+)", str(exc))`) against 18.1's own message format — an
internal coupling to code in this same repo that I wrote and can keep stable, not a fragile
external dependency. `None` when no match (timeouts/`httpx.RequestError` never had a real HTTP
status to begin with). Documented inline at the call site so a future change to
`_format_error`'s message shape doesn't silently break this without a visible comment pointing
back here.

Tests use `httpx.MockTransport` only (same pattern as `tests/test_openai_compat_provider.py`) —
never a real OpenRouter call, matching every prior task in this phase.

### 5. Health

`/api/ai/health` (`app/api/ai_jobs.py`, health payload only, allowed) adds:
- `cloud_configured`: `bool(settings.OPENAI_COMPAT_API_KEY and settings.OPENAI_COMPAT_MODEL)`.
- `cloud_model`: `settings.OPENAI_COMPAT_MODEL` (not secret, always returned, even when
  `cloud_configured` is false — matches `model`'s existing unconditional-return pattern).
- `effective_mode`: `compute_effective_mode(AIMode(settings.AI_MODE), settings.AI_ALLOW_CLOUD,
  settings.OPENAI_COMPAT_API_KEY, settings.OPENAI_COMPAT_MODEL).value` (reuses 18.2's own
  function directly — no duplicated logic).
- `circuit_open`: reads the app-lifetime breaker's *current* state,
  `app.main._ai_circuit.is_open()`, via the same deferred-import pattern this file already uses
  for `ai_worker` (`from app.main import ai_worker` inside the handler, to dodge the circular
  import `app.main` constructing this router creates — `_ai_circuit` is imported the same way,
  `from app.main import _ai_circuit`). No key material in any of these four fields.
No changes to the existing `mode`/`ollama_reachable`/`model`/`model_present`/`model_digest`/
`cloud_enabled`/`worker_alive` fields — all four new fields are additive.

### 6. Settings page: mode selector, privacy note, form

**Mode selector offers exactly 2 options, `local` and `cloud_first`** — not `cloud` (the
no-fallback diagnostic mode isn't a normal user-facing toggle; it stays reachable only via direct
API/env for testing, matching the plan's own "diagnostic" framing for it). A radio pair (not a
free-text mode field): "Local only" / "Cloud-first (recommended)". When
`settings.AI_ALLOW_CLOUD` is `false` (an explicit env override, now the *minority* case since
Amendment C flips the default to `true`): the "Cloud-first" option is rendered disabled with an
inline note, "Cloud is disabled by `DIE_AI_ALLOW_CLOUD=false` — ask whoever manages this
install's `.env` to enable it." (from `GET /api/settings`'s existing implicit signal: `set_ai_mode`
rejecting a `cloud_first` PUT with a `DIE_AI_ALLOW_CLOUD` message — surfaced proactively in the UI
via a new `allow_cloud: bool` field added to `GET /api/settings`'s response, read directly from
`settings.AI_ALLOW_CLOUD`, not secret).

**Privacy note** (invariant 35), matching the page's existing English copy, placed directly under
the cloud provider form fields: *"Topics and generated content are sent to your configured cloud
provider. Don't include personal data in a project's topic when cloud mode is on."*

**Form fields** (base URL, model, key — password-type input, key masked-preview + "Clear" button
matching the old Gemini form's now-deleted UX pattern), a "Test connection" button (calls point
4's endpoint, shows "OK" or `error (status)`, never blocks saving), and a Save button. No new
shared CSS framework — page-specific layout stays in `settings.html`'s own existing inline
`<style>` block (matching how it already does the `.settings-card`/`.current-status` rules); only
genuinely reusable new primitives (a masked-key input row, a labeled radio pair, an inline
status/error line) go into `style.css` under one new, clearly-marked `/* Settings (Task 18.3) */`
comment block — the plan's "settings block only" scope.

### 7. Browser test

New `tests/test_settings_browser.py` (mirrors `tests/test_dashboard_browser.py`'s
`browser_instance`/`live_server_url` fixture pattern). Covers: page loads and shows current
status; saving base URL + model + key round-trips through a reload (masked, last 4 only);
clearing the key reverts the displayed status to env/none; the mode radio pair reflects
`AI_ALLOW_CLOUD` (enabled vs. disabled-with-note, exercised via the `client`/settings-API-level
monkeypatch this suite's other settings tests already use, not by editing `.env` mid-test); test
connection shows OK against a mocked success and shows an error class + status against a mocked
failure (patches the same `httpx.MockTransport` pattern at the `openai_compat_provider` module
level, reached indirectly through the real `POST .../test-connection` endpoint — not a fake
router, since this endpoint constructs its own provider directly per point 4).

### 8. `check_dependencies.py`

`PLACEHOLDER_API_KEY`/`check_env_file` (the old Gemini-key check) removed. New
`check_cloud_provider()`, informational only (never fails the overall check, matching the
existing Gemini check's informational status): reports whether
`settings.OPENAI_COMPAT_API_KEY`/`_MODEL` are configured, using the same `settings.*`
source-of-truth pattern `check_env_file` already used (never re-parses `.env` by hand). The
`informational_checks` list's one entry is replaced, not added to.

## Test plan

- `tests/test_settings_service.py`: `set_cloud_settings`/`get_cloud_settings_status`/
  `clear_cloud_api_key`/`load_cloud_settings_from_db` — persists, applies immediately, `api_key=
  None` leaves the stored key unchanged, empty string rejected, `_last4` masking (short-key edge
  case), clear reverts to `ENV_OPENAI_COMPAT_API_KEY`. Confirms the deleted Gemini functions are
  actually gone (`AttributeError`/`ImportError` on the old names — a real regression guard, not
  just "no longer tested").
- `tests/test_settings_api.py`: `GET /api/settings` includes the new cloud fields and `allow_cloud`,
  never the raw key, in the response body text; `PUT /api/settings/cloud` round-trip; `DELETE
  /api/settings/cloud/api-key`; the old `PUT /api/settings` / `DELETE /api/settings/gemini-api-key`
  routes now 404/405.
- New `tests/test_settings_test_connection_api.py` (or folded into `test_settings_api.py` --
  decided during implementation by file size): `httpx.MockTransport`-backed success/every error
  class from the plan's table (reusing 18.1's own table, not re-deriving it), confirming `status`
  extraction for each. **The required key-safety test, reconsidered against what's actually new
  here:** `OpenAICompatProvider` already redacts the key from its own exception messages
  (Task 18.1's `_redact` backstop) before this endpoint ever sees the exception, so re-testing
  *that* specific mechanism here would just be re-proving 18.1. `api_key` is deliberately given
  no Pydantic `Field()` constraints (plain `str | None`), so it can't fail request validation and
  get echoed back in a 422 body either. What 18.3's own handler *could* still get wrong is simply
  putting the key into its own response by mistake (e.g. a debug echo, or `str(exc)` where `exc`
  somehow captured it) -- the direct test: `POST .../test-connection` with a distinctive marker
  key, for both a mocked success and every mocked error class, asserting the marker is absent
  from the raw HTTP response body in every case. Revert-and-confirm-failure target: temporarily
  have the handler include `payload.api_key` in the returned error dict (a deliberate regression)
  -- confirm the test catches it, then remove.
- `tests/test_ai_health_api.py`: the 4 new fields, `circuit_open` reflecting a forced-open breaker
  (via the same `app.main._ai_circuit` import the handler itself uses, from the test side).
- `tests/test_check_dependencies.py`: `check_cloud_provider` replaces the deleted
  `check_env_file`'s test coverage.
- `tests/test_settings_browser.py` (new): the page-level flow, point 7.
- Revert-and-confirm-failure target: the test-connection key-safety test described above.
- Full suite, `ruff`, real DB untouched.

## Verification (required)

See plan §3 "18.3". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

- Design commit `d40e9c3` (APPROVED with C1/C2/C3), this implementation commit folds all three
  in per "no re-approval needed."
- **Code:**
  - `app/core/config.py`: `AI_ALLOW_CLOUD` default `False` → `True` (plan Amendment C) and its
    comment. `.env.example`: matching comment/default update.
  - `app/services/ai/openai_compat_provider.py` (C1): `_raise()` helper gains `upstream_status`
    (set on every raised exception) and a `cause` param (keeps `raise ... from exc` chaining
    clean without a nested try/except). The `200`-with-error-body branch uses the body's own
    numeric `code` as `upstream_status`, not the literal `200`.
  - `app/services/settings_service.py`: rewritten — the old Gemini-key section (`get_/set_/
    clear_gemini_api_key`, `load_gemini_api_key_from_db`, `_mask`, `GEMINI_API_KEY_SETTING`)
    deleted; new cloud-settings section (`get_cloud_settings_status`, `set_cloud_settings` (C2
    validation), `clear_cloud_api_key`, `load_cloud_settings_from_db`, `test_cloud_connection`,
    `_last4`, `compute_effective_mode_and_reason` (C3)). The AI-mode section is unchanged from
    18.2 except its docstrings' `set_cloud_settings` cross-references.
  - `app/models/settings.py`: `GeminiApiKeyUpdate` deleted; `CloudSettingsUpdate`,
    `CloudTestConnectionRequest` added (both deliberately unconstrained at the Pydantic level —
    C2's real validation lives in the service).
  - `app/api/settings.py`: rewritten — `PUT /api/settings` and `DELETE /api/settings/gemini-api-key`
    removed; `PUT /api/settings/cloud`, `DELETE /api/settings/cloud/api-key`,
    `POST /api/settings/cloud/test-connection` added; `GET /api/settings` merges cloud status +
    ai-mode status + `allow_cloud` + `effective_mode`/`effective_reason` (C3).
  - `app/api/ai_jobs.py` (health payload only): `cloud_configured`, `cloud_model`,
    `effective_mode`, `circuit_open` added, reading `app.main._ai_circuit`/`compute_effective_mode`
    via the same deferred-import pattern already used for `ai_worker`. No existing field changed.
  - `app/main.py` (startup loading only): `load_gemini_api_key_from_db` → `load_cloud_settings_from_db`.
  - `scripts/check_dependencies.py`: `check_env_file`/`PLACEHOLDER_API_KEY` removed;
    `check_cloud_provider()` (informational) added; the `informational_checks` entry replaced.
  - `frontend/pages/settings.html`: rebuilt from Task 14.7's read-only status line into the full
    interactive form (mode radios, cloud fields, test-connection button, privacy note).
  - `frontend/static/js/settings.js`: rewritten — load/render status, mode-change handler, save/
    clear/test-connection handlers, effective-mode-with-reason rendering (C3).
  - `frontend/static/js/api.js` (settings calls only): `updateAiMode`, `updateCloudSettings`,
    `clearCloudApiKey`, `testCloudConnection` added.
  - `frontend/static/css/style.css` (settings block only): one new `/* Settings (Task 18.3) */`
    block — `.settings-field-label`, `.settings-input`, `.settings-radio-row`/`-option`,
    `.settings-inline-note` (+ `.is-success`/`.is-error`). Page-specific layout stays in
    `settings.html`'s own inline `<style>`, as designed.
- **A real bug found and fixed during testing, not by the PM:** my first draft of
  `tests/test_settings_browser.py` registered `page.route("**/api/settings*", handle)` — a
  single trailing `*` only matches within one path segment (no `/`), so it silently missed nested
  paths like `.../cloud/test-connection`. A debug script (`page.on("requestfailed"/"console")`,
  read-only, no data written) showed the mock never intercepting that endpoint and the
  unmocked request reaching the **real** OpenRouter API (a real `503` came back) — exactly what
  "tests use MockTransport only, never the real API" forbids. Fixed to `"**/api/settings**"`
  (trailing `**` matches across `/`), reverified with the same debug script showing both routes
  intercepted, then confirmed no other test in the file had the same gap. Documented inline in
  the test file's comment at the fixed line so this doesn't quietly regress.
- **Amendment C ripple effect, found by the full suite, not anticipated in the design:**
  flipping `AI_ALLOW_CLOUD`'s default broke `tests/test_ai_jobs_api.py::
  test_ai_health_never_exposes_the_gemini_key`, which asserted `cloud_enabled is False` without
  pinning the setting itself (implicitly relying on the old global default). Fixed within this
  test file's explicitly-allowed "health assertions only" scope: pinned `AI_ALLOW_CLOUD=False`
  explicitly (matching the fix already applied to every other settings-adjacent test file), and
  extended the same test to also assert the new cloud key is never leaked (it's the key this
  endpoint could plausibly expose now, not the retired Gemini one).
- **Tests touched/added:** `tests/test_settings_service.py` (43 tests — old Gemini-key tests
  replaced by cloud-settings/test-connection/effective-mode-and-reason coverage, plus
  `test_old_gemini_key_functions_are_gone` as a real regression guard), `tests/test_settings_api.py`
  (27 — cloud PUT/DELETE/test-connection routes, old routes now 404/405, C2's
  "nothing stored on invalid input" at the API layer, C3's effective-mode/reason fields),
  `tests/test_ai_health_api.py` (14 — 4 new health fields including a whitebox `circuit_open`
  test via `app.main._ai_circuit`), `tests/test_check_dependencies.py` (5 — `check_cloud_provider`
  replaces the deleted Gemini check's coverage), `tests/test_settings_browser.py` (7, new — page
  load, save round-trip, clear, disabled-mode note, test-connection OK/error, and C3's exact
  required scenario), `tests/test_openai_compat_provider.py` (29 — `upstream_status` assertion
  added to every existing error-mapping test, C1), `tests/test_ai_jobs_api.py` (14 — one test
  fixed per the ripple-effect note above).
- **Full suite:** `./venv/Scripts/python.exe -m pytest -q` → **1045 passed** (1002 baseline after
  Task 18.2 + N1). `ruff check .` → all checks passed. Real DB untouched — every test in this
  task's scope uses the `db`/`client`/`live_server` fixtures (temp SQLite, isolated `DATA_DIR`),
  never `data/app.db`.
- **Revert-and-confirm-failure** (the key-safety test on `test_cloud_connection`, as specified):
  temporarily added `"key": effective_key` to the returned error dict — both
  `tests/test_settings_service.py::test_cloud_connection_never_includes_the_key_in_its_result`
  and `tests/test_settings_api.py::test_post_test_connection_reports_error_class_and_status_never_the_key`
  failed exactly as expected, showing the marker key in the assertion diff. Restored (`git diff`
  on the file returned empty relative to the pre-revert state) → both tests, the full file(s),
  and the full suite passed again.
