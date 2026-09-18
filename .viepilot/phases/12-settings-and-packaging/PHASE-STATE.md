# Phase 12 State — Settings & Packaging

## Metadata
- **Phase:** 12
- **Slug:** 12-settings-and-packaging
- **Status:** complete
- **Started:** 2026-09-18
- **Closed:** 2026-09-18
- **Milestone Progress:** 2 / 2 tasks done. New scope, requested directly by the user
  (not audit-derived): (1) a Settings page to enter the Gemini API key through the UI
  instead of hand-editing `.env`, and (2) packaging the app as a standalone Windows
  `.exe` so it doesn't require a manual `venv`/`pip install` setup. Both scoped via
  `AskUserQuestion` — user chose "Settings page, save to DB" (with `.env` fallback)
  and "standalone `.exe` via PyInstaller".
- **Test Suite Status:** 639/640 passed after Task 12.2 (2026-09-18), 322.79s — 1
  failure (`test_youtube_browser.py::test_existing_package_loads_directly_without_generate_click`),
  confirmed passing instantly in isolation, the third distinct one-off
  Playwright-class flake observed this session, not a regression. 640/640 clean
  after Task 12.1.

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

### Task 12.2: Package as a standalone Windows `.exe` (PyInstaller) — ✅ DONE (2026-09-18)
- **Status:** done
- New centralized `app/core/paths.get_project_root()` replaces 5 independent
  `Path(__file__)`-walking constants; frozen-aware `DATA_DIR` default
  (`%LOCALAPPDATA%\DailyIntelEnglishStudio\data`); new `app/desktop_launcher.py`
  entrypoint (auto-opens the browser once the port is live, reuses an existing
  instance instead of crashing on a second launch). First build came out at
  4.5GB from leftover OmniVoice-experimentation ML packages (`torch` etc.) with
  zero real usage in `app/` — excluded, rebuilt to 169MB. Actually built and run
  twice, driven end-to-end with Playwright against the real packaged exe
  (dashboard, `/step1`, `/settings`) from a realistic no-`.env` working
  directory. See `tasks/task-12.2.md` for full evidence.

**This closes Task 12.2 — and Phase 12 (Settings & Packaging) in full.**
