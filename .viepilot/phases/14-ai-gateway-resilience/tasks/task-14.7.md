# Task 14.7 — Local-Only Mode, Config-First

- **Status:** pending
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** Amendment D (plan §12, commit `94f5e7b`); Gate B-2 (`docs/operations/phase14-gate-b2.md`)
- **Controlling detail:** plan §12 Task 14.7; ADR-001 amendment A2; brainstorm decisions D9–D12

## Objective

Make `local` the real default for both development and packaged builds, per the owner's
decision to drop Gemini (D9–D12): no API-key UI, no `gemini`/`hybrid` option exposed, the
app requires Ollama to *generate* (not to *start*), and every remaining "Gemini fallback"
UI string is gone. The Gemini provider, its settings plumbing, and its tests stay in the
codebase — dormant, not deleted — so `DIE_AI_ALLOW_CLOUD=true` plus config remains a real,
if unsupported, rollback path (ADR-001 A2).

## Measured problem (do not re-derive)

Gate B-2 (`docs/operations/phase14-gate-b2.md`): Gemini 0/5 (503 storms wider than the
14.1 backoff window; free-tier 20 requests/day exhausted by retries — `quotaId` contained
`PerDay`/`FreeTier`, `retryDelay` 21s). Local 3/5, but **zero infrastructure failures**,
every completed script passed every content check. The owner decided (D9–D12,
`docs/brainstorm/session-2026-09-21.md` §Addendum) to drop Gemini as a supported path
rather than debug cloud quota/billing, and ship local-only.

## Allowed files

`app/core/config.py`, `app/core/constants.py`, `.env.example`, `app/api/ai_jobs.py`
(health payload only), `app/services/settings_service.py`, `app/api/settings.py`,
`app/models/settings.py`, `frontend/pages/settings.html`,
`frontend/static/js/settings.js`, `frontend/static/js/api.js` (only if a call is
removed), `frontend/static/js/step2_script.js`, `frontend/static/js/step3_learning.js`
(only to replace the "using Gemini fallback" copy with Ollama-missing guidance),
`frontend/static/css/style.css`, `scripts/check_dependencies.py`,
`daily_intel_english_studio.spec` (only if imports/data change), `README.md`,
`CHANGELOG.md`, `tests/test_settings_service.py`, `tests/test_settings_api.py`,
`tests/test_ai_health_api.py`, `tests/test_ui_async_browser.py`,
`tests/test_script_jobs_browser.py`, `tests/test_learning_jobs_browser.py`,
`tests/test_ai_router.py` (default-mode assertions only), `tests/conftest.py` (only if
the default-mode change requires a fixture change), and — **Amendment E (PM, 2026-09-21,
plan commit `26dae03`, before any 14.7 code)** — `tests/test_thumbnail_service.py`,
`tests/test_youtube_service.py` (test-only, for action 7's two `FakeProvider` tests;
omitted from the original list by mistake).

`docs/operations/local-ai.md` and `docs/api.md` are PM-owned — report what changed, PM
documents it.

**Amendment E also settles the two choices action 2/3 originally left open:**
(a) the Settings mode selector is **replaced by a read-only status line** — no dead
`gemini`/`hybrid` options shown; the settings API still accepts `local` and, behind
`DIE_AI_ALLOW_CLOUD=true`, `gemini`/`hybrid`. (b) the health payload **drops**
`gemini_fallback_configured` entirely and adds `cloud_enabled: false` — an always-false
field would be misleading. Every frontend reader of the old `gemini_fallback_configured`
field must be updated in the same commit as the API change (no stale reads left behind).

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. `AI_MODE` defaults to `"local"` in `app/core/config.py` and `.env.example`. Remove the
   stale, unused `DIE_AI_CLOUD_FALLBACK` line from `.env.example` — grep first to confirm
   nothing reads it before deleting.
2. Settings page: remove the Gemini API-key section and the `gemini`/`hybrid` options
   from the mode selector, **replacing the selector with a read-only status line**
   (Amendment E — no dead options shown). The settings *API* keeps accepting/storing the
   key (dormancy/rollback path), but the UI no longer exposes it. `set_ai_mode` (in
   `app/services/settings_service.py`) rejects `gemini`/`hybrid` unless the new
   `DIE_AI_ALLOW_CLOUD` env var (default `false`) is `true` — this is the **only** new
   switch; it exists so re-enabling cloud is always an explicit act, never an accident.
3. `GET /api/ai/health` reports `cloud_enabled: false` and **drops**
   `gemini_fallback_configured` entirely (Amendment E — an always-false field would be
   misleading). Every frontend reader of the old `gemini_fallback_configured` field is
   updated to the new field in the same commit — no stale read left behind.
4. Step 2 (`step2_script.js`) / Step 3 (`step3_learning.js`): when `/api/ai/health` says
   Ollama is unreachable or the model is missing, the generate button is disabled and the
   panel shows install/pull guidance naming the exact model tag and digest (copy from
   `docs/operations/local-ai.md` — read it first for the current tag/digest text; do not
   invent new wording). No "Gemini fallback" copy remains anywhere in the DOM.
5. `scripts/check_dependencies.py`: Ollama reachability and model presence become a hard
   requirement with a clear failure message. The Gemini key check becomes informational
   (a note, not a failure) or is removed — Coder's choice, record which.
6. `README.md` / `CHANGELOG.md`: state local-only plainly, document the Ollama
   prerequisite, and record the rollback note verbatim: "Gemini is dormant; re-enable via
   `DIE_AI_ALLOW_CLOUD=true`, `DIE_AI_MODE`, and a key — unsupported."
7. Thumbnail and YouTube generators already route through the shared AI gateway; in local
   mode they call Ollama like everything else. Add exactly one `FakeProvider` test each
   (thumbnail, YouTube) proving they run end-to-end under `AI_MODE=local` — this is a
   wiring/regression check only; real structured-output quality on Ollama for these two
   schemas is measured by the PM in Task 14.9 (one real thumbnail + one real YouTube
   package on the Gate B-3 winning project), not here.

## Explicitly forbidden

- Deleting the Gemini provider, its adapter, or its existing tests — dormant, not removed
  (ADR-001 A2: "remain in the codebase, dormant").
- Any new env var beyond `DIE_AI_ALLOW_CLOUD`.
- Changing `AI_TRANSIENT_MAX_ATTEMPTS`, backoff constants, or any Task 14.1–14.3 behavior
  — this task is UI/config/docs only, not router/pipeline logic (that is Task 14.8's
  narrow scope, not this one's).
- Touching a file outside the allowed list above, including any `docs/**` path other than
  what's explicitly PM-owned per this card.

## Verification (all must be in the diff)

1. `tests/test_settings_service.py` / `tests/test_settings_api.py`: `set_ai_mode` rejects
   `gemini`/`hybrid` when `DIE_AI_ALLOW_CLOUD` is unset/false; accepts them when it's
   `true`; default `AI_MODE` is `local`.
2. `tests/test_ai_health_api.py`: `cloud_enabled: false` present; `gemini_fallback_configured`
   no longer in the payload (grep confirms exactly 2 current references to update:
   `app/api/ai_jobs.py:119` and this test file's own assertion at line 47 — record the
   actual line numbers found at implementation time, these may drift); existing
   secret-absence assertions still pass.
3. `tests/test_ai_router.py`: default-mode assertion(s) updated only if the router's own
   default construction path changed (it should not need behavior changes, only whatever
   default-value assertions reference the old default).
4. Browser tests (`tests/test_ui_async_browser.py`, `tests/test_script_jobs_browser.py`,
   `tests/test_learning_jobs_browser.py`): mock `/api/ai/health` as Ollama-missing, assert
   the generate button is disabled and the install/pull guidance (tag + digest) renders;
   assert no Gemini-fallback copy in the DOM.
5. A case-insensitive grep for `"gemini fallback"` across `frontend/` returns nothing
   after the change (record the exact grep command and its empty output in this card).
6. One `FakeProvider`-backed thumbnail test and one `FakeProvider`-backed YouTube test,
   both running under `AI_MODE=local`.
7. `venv\Scripts\python.exe -m ruff check app tests scripts` clean; full suite green
   (record the exact pass count); JS syntax check (`node --check` on every edited `.js`
   file) clean.
8. Packaged smoke build starts with Ollama stopped and shows guidance instead of crashing
   (if this is practical to verify without a full packaging run, record how; if not,
   record why and what was verified instead — do not claim untested behavior as tested).

## Rollback

`DIE_AI_ALLOW_CLOUD=true` + `DIE_AI_MODE=hybrid` (or `gemini`) + a configured key restores
the Phase 13 hybrid/Gemini behavior without a code revert.

## Execution record (Coder fills in)

- Plan/decisions before code:
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
