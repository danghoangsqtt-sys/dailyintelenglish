# Task 12.1: Settings page — Gemini API key stored in DB with `.env` fallback

## Meta
- **ID**: 12.1 (first task of Phase 12 — Settings & Packaging)
- **Phase**: 12
- **Status**: done (2026-09-18)
- **Priority**: medium (usability — removes the need to hand-edit `.env` for the
  single most common first-run blocker)
- **Assignee**: PM (Claude Code), self-implemented per the standing policy
  ([[feedback_self_implement_no_codex]])

## Doc-First Gate

Origin: user directly asked "sao không tạo một ô nhập API key trong phần cài đặt"
(why isn't there an input field for the API key in settings) right after being told
the project was ready for trial. Scoped via `AskUserQuestion`: user chose "Settings
page riêng, lưu vào DB" (a dedicated Settings page, saved to the database) over the
lighter "just edit `.env` through the UI" or "no UI, better docs" options.

## Current state (read directly before planning)
- `app/core/config.py`'s `Settings` (pydantic-settings `BaseSettings`) reads
  `GEMINI_API_KEY` from the process env / `.env` once at import time into a
  module-level `settings` singleton instance.
- 4 service modules read `settings.GEMINI_API_KEY` as a plain attribute at call time
  (`script_service.py`, `learning_service.py`, `thumbnail_service.py`,
  `youtube_service.py`) — none of them currently touch the database for this.
- DB schema uses a numbered-migration system (`app/db/migrations/*.sql`, tracked in
  `schema_migrations`, applied once each via `Database`/`init_db()` in
  `app/db/database.py`) — no existing app-level (non-project) key/value settings
  table.
- `app/api/projects.py` defines module-level `_write_lock` /
  `_read_transaction` / `_write_transaction` helpers; other routers (`tts.py`,
  confirmed via grep) already import these directly rather than each rolling its
  own lock — this task's router follows the same pattern.
- Every page (`dashboard.html`, `step1..7`, `music_library.html`) has its own
  inline `<header class="topbar">` markup — no shared JS-rendered nav shell exists
  to hook into once. Scoping decision: add the Settings entry point to
  `dashboard.html`'s topbar only (the app's landing page — `GET /` — and the
  natural first stop before starting a trial run), not all 9 pages. Documented here
  rather than silently narrowed.

## Required decisions
1. **Storage**: new `app_settings` key/value table (migration
   `004_app_settings.sql`), not a new column on an existing table — this setting is
   app-global, not per-project.
2. **Precedence + live effect**: on startup (after `init_db()`), if a DB-stored key
   exists, overwrite the in-memory `settings.GEMINI_API_KEY` with it (pydantic
   `BaseSettings` instances are plain mutable objects here — no `frozen=True` in
   `model_config`). Saving through the Settings page updates both the DB row and
   the in-memory `settings.GEMINI_API_KEY` immediately, so it takes effect without
   an app restart. A new `config.ENV_GEMINI_API_KEY` constant captures the original
   `.env`/environment-sourced value once at import time (before any DB override can
   run), so "clear the stored key" can revert to it instead of going blank.
3. **Never echo the raw key back to the browser.** `GET /api/settings` returns a
   masked value (`"AIzaSy••••…1a2b"`-shaped: first 6 + last 4 chars, `••••` between)
   plus a `source` field (`"database" | "env" | "none"`) — never the full key.
4. **No existing service call site changes.** All 4 services keep reading
   `settings.GEMINI_API_KEY` exactly as today; the DB-vs-env resolution happens once,
   centrally, not by touching 4 files' Gemini-call logic.

## Proposed file-level plan

### Backend
- `app/db/migrations/004_app_settings.sql` (new): `CREATE TABLE IF NOT EXISTS
  app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)`.
- `app/core/config.py`: add `ENV_GEMINI_API_KEY = settings.GEMINI_API_KEY` right
  after `settings = Settings()` — the pre-DB-override snapshot used for "clear".
- `app/services/settings_service.py` (new): `get_gemini_api_key_status(db) ->
  dict` (masked value + source), `set_gemini_api_key(db, raw_key: str) -> dict`
  (validate non-empty/stripped, upsert into `app_settings`, mutate
  `config.settings.GEMINI_API_KEY` in place, return the new masked status),
  `clear_gemini_api_key(db) -> dict` (delete the DB row, reset
  `config.settings.GEMINI_API_KEY = config.ENV_GEMINI_API_KEY`, return status),
  `load_gemini_api_key_from_db(db) -> None` (startup-time loader).
- `app/api/settings.py` (new router, `prefix="/api/settings"`): `GET ""` (status),
  `PUT ""` (body `{gemini_api_key: str}`, calls `set_gemini_api_key` inside
  `_write_transaction`), `DELETE "/gemini-api-key"` (calls `clear_gemini_api_key`
  inside `_write_transaction`). Imports `_read_transaction`/`_write_transaction`
  from `app.api.projects`, matching `tts.py`'s existing pattern.
- `app/main.py`: mount the new router; in `lifespan`, after `await init_db()`, call
  `await settings_service.load_gemini_api_key_from_db(Database.instance().connection)`;
  add `GET /settings` route serving `frontend/pages/settings.html`.

### Frontend
- `frontend/pages/settings.html` (new): password-type input (with a show/hide
  toggle button, matching existing icon-button style), Save / Clear buttons, a
  status line showing the masked key + source, a "← Back to Dashboard" link. Reuses
  `/static/css/style.css` — no new stylesheet.
- `frontend/static/js/settings.js` (new): fetch current status on load via
  `api.js`'s existing fetch helper, wire Save (`PUT`)/Clear (`DELETE`), render the
  masked value and source, surface backend validation errors through the existing
  `error-banner`/toast pattern already used elsewhere (grep `dashboard.js` for the
  exact convention before writing this).
- `frontend/pages/dashboard.html`: add a `⚙️ Settings` icon-button to the
  `.actions` div in the topbar (next to the existing theme toggle), linking to
  `/settings`.

### Tests
- `tests/test_settings_service.py` (new): DB round-trip (set → get masked+source
  `"database"`, clear → get masked+source falls back to `"env"`/`"none"`
  correctly), masking format on a few key lengths, and a real
  revert-and-confirm-failure check proving `load_gemini_api_key_from_db` actually
  changes `settings.GEMINI_API_KEY` (not a vacuous test).
- `tests/test_settings_api.py` (new): full HTTP round-trip via `TestClient` for
  `GET`/`PUT`/`DELETE`, including a rejection case (empty/whitespace-only key).

## Allowed files
- `app/db/migrations/004_app_settings.sql`
- `app/core/config.py`
- `app/services/settings_service.py`
- `app/api/settings.py`
- `app/main.py`
- `frontend/pages/settings.html`
- `frontend/static/js/settings.js`
- `frontend/pages/dashboard.html`
- `tests/test_settings_service.py`
- `tests/test_settings_api.py`

## Acceptance criteria
- [x] `app_settings` migration applies cleanly on a fresh DB and on an
      already-migrated one (idempotent per the existing migration-tracking system).
- [x] Saving a key through `PUT /api/settings` takes effect immediately (no restart)
      — proven by a test that saves a key and then calls a function that reads
      `settings.GEMINI_API_KEY` directly.
- [x] `GET /api/settings` never returns the raw key in any response body.
- [x] Clearing the stored key correctly reverts to the original `.env`-sourced
      value, not an empty string (when `.env` had a value).
- [x] Full test suite still green; new tests independently confirmed meaningful via
      a real revert-and-confirm-failure check.
- [x] Settings page reachable from the dashboard, visually consistent with the rest
      of the app (reuses existing CSS classes, no new stylesheet).

## Implementer Evidence

All 10 files from the plan created/edited exactly as scoped (`git status --short`
confirmed no out-of-scope files touched). Key implementation notes:

- `config.ENV_GEMINI_API_KEY` is captured once at import time, before any DB
  override can run — `settings_service.clear_gemini_api_key` reverts to it.
- `settings_service.set_gemini_api_key`/`clear_gemini_api_key` mutate
  `config.settings.GEMINI_API_KEY` in place (a plain mutable pydantic
  `BaseSettings` instance, not frozen) — the 4 existing Gemini-calling services
  needed zero changes.
- `_mask()` shows first 6 + last 4 chars for keys longer than 10 chars, otherwise
  fully masks — the raw key is never sent to the browser in any response.
- Settings entry point scoped to the dashboard topbar only (documented in the task
  card's "Current state" section) — not all 9 pages, to keep the diff proportional
  to the request.

**Real bug caught by the tests themselves, not just written to pass**: the first
version of `test_delete_reverts_to_env_source` failed for real — its fixture only
monkeypatched `settings.GEMINI_API_KEY`, not `config.ENV_GEMINI_API_KEY` (a separate
constant captured once at process import time), so `clear_gemini_api_key` correctly
reverted to *this machine's real, live `.env` Gemini key* instead of the test's fake
value — and the assertion failure printed that real key (masked) into the test
output. This was a test-isolation bug, not a service bug: the service's "revert to
the true original `.env` value" behavior is exactly the intended design. Fixed by
also monkeypatching `config.ENV_GEMINI_API_KEY` in the API test fixture (the
service-level test file already did this correctly the first time). Documented here
because it's a real, reusable lesson for this codebase: any test touching
`config.ENV_GEMINI_API_KEY`-dependent behavior must isolate both module attributes,
not just `settings.GEMINI_API_KEY`.

Full test suite: 640/640 passed (621 + 19 new), 293.22s, zero flakes. Both new test
files independently confirmed meaningful via a real revert-and-confirm-failure check
(`git stash` the entire implementation, all 19 new tests failed with `AttributeError`
as predicted since the module/router don't exist yet, `git stash pop` restored).

**Manually run and driven end-to-end** (not just unit-tested) against the real dev
server on a throwaway port (8123), per this project's "actually launch and interact"
discipline: started `uvicorn`, used Playwright to open `/settings`, confirmed the
real `.env`-sourced key showed masked and correctly labeled `"From .env file"`,
saved a fake test key, confirmed the UI updated immediately and the change survived
a full page reload (proving real DB persistence, not just an in-memory mutation),
toggled the show/hide button, cleared the stored key, and confirmed it reverted
back to the real `.env` value — screenshot reviewed, layout consistent with the
rest of the app. Also clicked the new ⚙️ Settings link from the dashboard topbar
and confirmed it navigates to `/settings`. Afterward, directly queried the real
`data/app.db`'s `app_settings` table and confirmed it was left empty (no test
pollution of the user's real database) and `GET /api/settings` on the real server
still reports the user's real key, unaffected.

## PM Acceptance
Self-implemented and self-reviewed (per the standing policy —
[[feedback_self_implement_no_codex]]). Verified 2026-09-18: full diff read against
the plan (all 10 files in scope, nothing extra), both new test files independently
confirmed meaningful via a real revert-and-confirm-failure check, ruff clean on all
new/modified files, full suite 640/640 green, and the feature manually driven
end-to-end against the real running server with Playwright (not just unit tests) —
including confirming no pollution was left in the real local database afterward.
**Accepted.**
