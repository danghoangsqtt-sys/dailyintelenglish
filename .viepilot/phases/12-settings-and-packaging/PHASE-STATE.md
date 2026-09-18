# Phase 12 State — Settings & Packaging

## Metadata
- **Phase:** 12
- **Slug:** 12-settings-and-packaging
- **Status:** in_progress
- **Started:** 2026-09-18
- **Closed:** (pending — Task 12.2 still open)
- **Milestone Progress:** 1 / 2 tasks done. New scope, requested directly by the user
  (not audit-derived): (1) a Settings page to enter the Gemini API key through the UI
  instead of hand-editing `.env`, and (2) packaging the app as a standalone Windows
  `.exe` so it doesn't require a manual `venv`/`pip install` setup. Both scoped via
  `AskUserQuestion` — user chose "Settings page, save to DB" (with `.env` fallback)
  and "standalone `.exe` via PyInstaller".
- **Test Suite Status:** 640/640 passed (621 + 19 new from Task 12.1), 293.22s, zero
  flakes (2026-09-18).

---

## Tasks Status & Acceptance Evidence

### Task 12.1: Settings page — Gemini API key stored in DB with `.env` fallback — ✅ DONE (2026-09-18)
- **Status:** done
- New `app_settings` DB table + `settings_service.py` resolving a DB-stored Gemini
  API key over `.env` at runtime, applied immediately (no restart) by mutating the
  shared `config.settings` singleton in place. New `/api/settings` router (never
  echoes the raw key — masked preview only) and a new Settings page linked from the
  dashboard topbar. Manually driven end-to-end against the real running server with
  Playwright, not just unit-tested. See `tasks/task-12.1.md` for full evidence.

### Task 12.2: Package as a standalone Windows `.exe` (PyInstaller) — not started
- **Status:** not started
- See `tasks/task-12.2.md` (written once planned).
