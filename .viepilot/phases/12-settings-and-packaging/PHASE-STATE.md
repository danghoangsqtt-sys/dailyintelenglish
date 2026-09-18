# Phase 12 State — Settings & Packaging

## Metadata
- **Phase:** 12
- **Slug:** 12-settings-and-packaging
- **Status:** in_progress
- **Started:** 2026-09-18
- **Closed:** (pending)
- **Milestone Progress:** 0 / 2 tasks done. New scope, requested directly by the user
  (not audit-derived): (1) a Settings page to enter the Gemini API key through the UI
  instead of hand-editing `.env`, and (2) packaging the app as a standalone Windows
  `.exe` so it doesn't require a manual `venv`/`pip install` setup. Both scoped via
  `AskUserQuestion` — user chose "Settings page, save to DB" (with `.env` fallback)
  and "standalone `.exe` via PyInstaller".
- **Test Suite Status:** (pending — updated as each task closes)

---

## Tasks Status & Acceptance Evidence

### Task 12.1: Settings page — Gemini API key stored in DB with `.env` fallback — in_progress
- **Status:** in_progress
- See `tasks/task-12.1.md`.

### Task 12.2: Package as a standalone Windows `.exe` (PyInstaller) — not started
- **Status:** not started
- See `tasks/task-12.2.md` (written once Task 12.1 closes).
