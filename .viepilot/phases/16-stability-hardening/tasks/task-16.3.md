# Task 16.3 — Test-Data Leak: Root Cause, Guard, Cleanup Tool, CHANGELOG (BUG-023)

- **Status:** in_progress
- **Owner:** Coder (investigation, guard, script); PM (dry-run → owner → `--apply` on the real DB)
- **Priority:** P1
- **Dependency:** 16.2 accepted
- **Controlling detail:** plan §4 "16.3", invariant 26, owner decision D19;
  `.viepilot/requests/BUG-023.md`

## Measured problem (do not re-derive)

The real `data/app.db` holds 426 projects. 419 are fixtures:
- "Learning API Test Episode" ×126
- "YouTube API Test Episode" ×107
- "Export API Test Episode" ×98
- "Script API Test Episode" ×88

The newest is from 2026-09-22T09:51:09Z. Every `client` fixture in those test files already
monkeypatches `settings.DATA_DIR`, yet rows leaked. Two split runs on 2026-09-23 (non-browser,
then `-k browser`) leaked nothing. Suspect to confirm or eliminate: the `Database` process
singleton — `connect()` returns an already-open connection, so a test that opened it against
the real path and didn't close it makes later lifespans reuse the real DB.
CHANGELOG `[Unreleased]` has no Phase 15 entry (15.1–15.3 changed code).

## Allowed files

`tests/conftest.py`; the leak-source test files **named in the design section before
editing**; new `scripts/cleanup_test_projects.py`; new `tests/test_cleanup_test_projects.py`;
`CHANGELOG.md`.

**Named per the design section below** (21 files, all `*_browser.py`, each getting the
identical mechanical fix described in Design decision 2): `tests/test_ui_async_browser.py`,
`tests/test_youtube_browser.py`, `tests/test_tts_audio_browser.py`,
`tests/test_responsive_layout_browser.py`, `tests/test_save_indicator_browser.py`,
`tests/test_new_shell_resize_browser.py`, `tests/test_step1_accent_disclosure_browser.py`,
`tests/test_step1_escape_html_browser.py`, `tests/test_step1_config_edit_browser.py`,
`tests/test_thumbnail_shell_browser.py`, `tests/test_step_nav_browser.py`,
`tests/test_youtube_shell_browser.py`, `tests/test_dashboard_browser.py`,
`tests/test_video_studio_browser.py`, `tests/test_video_shell_browser.py`,
`tests/test_tts_shell_browser.py`, `tests/test_quick_wins_browser.py`,
`tests/test_keyboard_shortcuts_browser.py`, `tests/test_learning_shell_browser.py`,
`tests/test_script_jobs_browser.py`, `tests/test_learning_jobs_browser.py`.
**Not touched** (already correct, see Design decision 1): `tests/test_music_library_browser.py`,
`tests/test_music_library_waveform_browser.py`, `tests/test_thumbnail_browser.py`.

## Required behaviour

1. **Investigation (record here):** one full single-process `pytest -q`, with the real DB
   project count read before and after (`sqlite3` `mode=ro` only). Name the leaking test(s)
   and the mechanism.
2. **Guard:** an autouse safeguard in `tests/conftest.py` so that no test can ever open the
   real `data/app.db`. It fails loudly if one tries.
3. **Cleanup script:** dry-run by default (counts per name + ids). `--apply` = backup to
   `data/backups/app-before-cleanup-<UTC>.db` and then delete **exact-name matches of the 4
   names only**, via the same service path as the API delete route (cascaded rows + per-project
   directories). `--db` / `--data-dir` are overridable.
4. CHANGELOG: add the missing Phase 15 entry (15.1 aliases, 15.2 merge fix, 15.3 runner
   `--gate`) plus this task's entry.

## Explicitly forbidden

Running `--apply` against the real DB (PM-only, invariant 26). Opening the real DB
read-write for any reason. Deleting by `LIKE` or any pattern other than the 4 exact names.

## Design decisions (Coder, doc-first — commit before code, PM approves)

**Investigation (required behaviour #1)**

Reproduced with a temporary autouse diagnostic fixture in `tests/conftest.py` (not
committed — reverted before this design commit) that printed the test nodeid at the
exact transition where the process-wide `Database` singleton's connection went from
closed to open-and-still-open, and vice versa. One full single-process `pytest -q -s`
run. Real DB project count read-only before: 446 (`sqlite3` `mode=ro`); after: 454 —
+8, i.e. +4 for this run plus +4 already leaked by an earlier plain diagnostic pass in
the same investigation session (both read via `sqlite3.connect("file:data/app.db?mode=ro", uri=True)`,
never opened read-write). The 4 leaked names and counts read back exactly:
`Export API Test Episode` (105), `Learning API Test Episode` (133),
`Script API Test Episode` (95), `YouTube API Test Episode` (114) — the same 4 names
the plan cites, confirming the mechanism is reliable and reproducible, matching the
PM's own 3 reproductions.

*Mechanism.* `app/db/database.py`'s `Database` is a process-wide singleton
(`Database._instance`), and `connect()` only opens a new `aiosqlite` connection
`if self._connection is None` — it never checks whether `settings.DATA_DIR` changed
since the connection was opened. Every `*_browser.py` Playwright test file has its own
copy-pasted `live_server_url` fixture (`scope="module"`) that starts a **real uvicorn
server** hosting the actual `app` object (`from app.main import app`) in a background
daemon thread, which runs the app's real `lifespan()` — `init_db()` →
`Database.instance().connect()` — exactly like the real, deployed app. Of the 24 such
fixtures, only 3 (`test_music_library_browser.py`, `test_music_library_waveform_browser.py`,
`test_thumbnail_browser.py`) set `settings.DATA_DIR` to an isolated
`tmp_path_factory.mktemp(...)` directory before starting the server, and correctly
restore it plus tear the server down (`server.should_exit = True; thread.join(...)`)
afterward. The other 21 never touch `settings.DATA_DIR` at all, so their live server
opens the connection against whatever `settings.DATA_DIR` actually defaults to —
confirmed literally `"data"` (the real, relative default) in the diagnostic output —
i.e. the exact same `data/app.db` the real app uses. Only 4 of those 21
(`test_learning_jobs_browser.py`, `test_script_jobs_browser.py`,
`test_thumbnail_shell_browser.py`, `test_youtube_shell_browser.py`) even attempt a
`server.should_exit = True; thread.join(...)` teardown (two of them — learning_jobs,
script_jobs — carry a comment already describing this exact class of bug, found once
before against `test_settings_api.py`); the remaining 17 have no teardown at all, so
the daemon thread and its connection simply linger. Empirically (via the transition
diagnostic), even the 4 with a `should_exit`/`join` teardown do not reliably close the
connection before the next module starts — moving on regardless, since the fix below
does not depend on relying on that teardown alone.

Because `settings.DATA_DIR`'s value doesn't matter to `connect()`'s reuse check, the
damage is confined to *whichever test next calls `TestClient(app)`* (any file, in
whatever order pytest collects): that test's own `client` fixture does
`monkeypatch.setattr(settings, "DATA_DIR", tmp_path)` correctly, but its `with
TestClient(app) as test_client:` triggers `init_db()` → `connect()`, which finds the
stale, already-open, real-path connection and **silently reuses it**, ignoring the
monkeypatch entirely. If that test's first action is to create a project (the common
shape for these API test files — see the transition list below), the project lands in
the real `data/app.db`. That single test's own `with TestClient(app)` teardown then
correctly calls `close_db()` (self-healing for every later test), which is exactly why
the leak is bounded to one row per incident rather than spreading forever, and why
only files whose first `client`-fixture test happens to POST a new project (not a
read-only GET, like `test_video_api.py::test_list_templates_returns_three_options` or
`test_thumbnail_api.py::test_templates_endpoint_lists_five_valid_preview_assets`, both
of which also inherited the stale connection per the diagnostic but wrote nothing
visible) show up as named leaks at all. Confirmed open→close transition pairs from the
diagnostic run (abbreviated to the ones landing on one of the 4 leaked names):
`test_keyboard_shortcuts_browser.py` (opens, `data_dir=data`) → closes at
`test_learning_api.py::test_generate_returns_200_and_persists`; `test_quick_wins_browser.py`
(opens) → closes at `test_script_api.py::test_generate_script_returns_200_and_persists`;
`test_video_shell_browser.py` (opens) → closes at
`test_youtube_api.py::test_generate_returns_200_and_persists`; `test_youtube_browser.py`
(opens) → closes at `test_youtube_export_api.py::test_export_returns_a_real_zip_with_all_five_files`.
The other ~9 confirmed-open browser files in this run happened to be followed by a
file whose first `client`-based test doesn't create a project, so they inherited the
stale connection too (confirmed by the diagnostic) but produced no visible row —
still a real bug (any of those files could start leaking the moment its neighboring
file's first test changes), just not one of today's 4 named symptoms.

**1. Guard (`tests/conftest.py`, required behaviour #2)**

A module-level patch (applied once, at `conftest.py` import time — before any test or
fixture runs, so it's active for every module-scoped browser fixture too, not just
function-scoped ones) wraps `Database.connect` so that it raises immediately, loudly,
*before* ever opening a file, if `settings.db_path` resolves to the literal real
`<project_root>/data/app.db` — computed once from `app.core.paths.get_project_root()`,
independent of whatever `settings.DATA_DIR` currently is, so the check can't be fooled
by the very bug it's guarding against. This is preventive, not just detective: no test
can ever cause a real write, and the failure is immediate and points at the exact
call site (a normal Python exception with a traceback), not a silent divergence
discovered hours later by counting rows. Every properly-isolated fixture (the `client`
fixture, the 3 already-correct browser fixtures, and all 21 fixed in decision 2) is
unaffected, since none of them ever point `settings.DATA_DIR` at the real path.
Never restored (`Database.connect` stays patched for the rest of the process) —
correct, since nothing in this suite should ever legitimately open the real DB through
the app's own connection machinery, for the life of the test session.

**2. Root-cause fix: isolate `DATA_DIR` in all 21 broken `live_server_url` fixtures**

Each of the 21 files named above gets the identical mechanical change, matching the
already-correct pattern in `test_music_library_browser.py`:
- Add `from app.core.config import settings` to the imports (none of the 21 currently
  import it).
- The fixture gains a `tmp_path_factory: pytest.TempPathFactory` parameter. Its first
  two lines become `original_data_dir = settings.DATA_DIR` and `settings.DATA_DIR =
  tmp_path_factory.mktemp("<file-slug>-data")` (a distinct slug per file, matching
  the existing `"music-browser-data"` / `"thumbnail-browser-data"` naming), before
  `port = _find_free_port()` and the `uvicorn.Server(...)` construction — so the live
  server's own `init_db()` call, whenever it fires, opens an isolated tmp database,
  never the real one.
- After the `yield f"http://127.0.0.1:{port}"` line: `server.should_exit = True`,
  `thread.join(timeout=10.0)`, then `settings.DATA_DIR = original_data_dir` (the 4
  files with a partial existing teardown keep their `should_exit`/`join` lines as-is
  and gain only the `settings.DATA_DIR` restore after them; the other 17 gain all
  three lines fresh).
- Nothing else in any of these files changes — not the tests, not `MOCK_PROJECTS`/
  payload fixtures, not the Playwright interaction code. The guard in decision 1
  means any file I miss, or any regression later, fails loudly and immediately in
  that file's own tests rather than silently corrupting the real DB — this is the
  safety net that makes fixing 21 near-identical files by hand tractable to verify.

**3. Cleanup script (`scripts/cleanup_test_projects.py`, required behaviour #3)**

`--dry-run` (default): connects read-only-by-convention (opens normally but only
issues `SELECT`s) to `--db` (defaults to the real `settings.db_path`), prints a count
per exact name plus the ids, for the 4 names only
(`Learning API Test Episode`, `YouTube API Test Episode`, `Export API Test Episode`,
`Script API Test Episode`), writes nothing.
`--apply`: first copies the db file to
`data/backups/app-before-cleanup-<UTC-timestamp>.db` (`shutil.copy2`, preserving the
source), then, for each matching project id, calls the same service-layer delete used
by the API's delete route (`project_service.delete_project`, which cascades
speakers/jobs/rows and removes the project's per-project directories) — not a raw
`DELETE FROM projects`, so nothing is left orphaned on disk or in other tables.
`--db`/`--data-dir` are overridable so the script's own tests run it against a tmp
copy, never the real file. Deletion is **exact-name match only** (`WHERE name = ?`,
parameterized, never `LIKE` or any pattern) — the task's explicit prohibition.
The Coder runs `--dry-run` only, against a tmp fixture DB, in this task's own tests;
`--apply` against the real DB is PM-only (invariant 26), after the owner sees the
dry-run output.

**4. CHANGELOG**

Add the missing Phase 15 entry (aliases in 15.1, the consecutive-lines merge fix in
15.2, the `set_job_metric`/runner `--gate` path in 15.3) and this task's own entry,
both under `[Unreleased]`.

**Test plan**
- `tests/conftest.py`: no new test file (the guard is exercised implicitly by every
  existing test that touches `Database`/`client`, plus explicitly by
  revert-and-confirm-failure below).
- Revert-and-confirm-failure target: temporarily monkeypatch `settings.DATA_DIR`
  itself to point at the real `data` directory inside one of the 21 fixed browser
  files' `live_server_url` fixtures (simulating the bug), confirm the guard raises
  loudly and that specific module's tests fail with the guard's own error message
  (not a silent pass), then restore.
- A full single-process `pytest -q` (the actual verification, not a separate unit
  test) must leave the real DB's project count unchanged — read-only, before and
  after, via `sqlite3 mode=ro`. This *is* the guard's own end-to-end proof: if any of
  the 21 fixes is wrong, that file's tests fail immediately (guard trip) rather than
  silently leaking again.
- `tests/test_cleanup_test_projects.py` (new): on a tmp SQLite DB seeded with a mix of
  the 4 fixture names plus at least one real-looking project name: dry-run prints
  counts/ids and writes nothing (file mtime/size unchanged, row count unchanged);
  `--apply` writes exactly one backup file at the expected path, deletes only the 4
  exact-name projects (the real-looking one and any near-miss name like `"Learning API
  Test Episode 2"` or `"learning api test episode"` survive), and confirms cascaded
  rows (speakers) and the per-project directory are gone (via the same
  `project_service.delete_project` path, not a raw SQL count only). A default-`--db`
  safety test confirms the script never touches anything outside an explicitly passed
  `--db`/`--data-dir` when running in the test process (no accidental real-path
  fallback).

## Verification (required)

The guard fails when the leak is reintroduced (revert-and-confirm-failure). A full
single-process `pytest -q` leaves the real project count unchanged. Script tests on a tmp DB:
exact names only, backup written, dry-run writes nothing, directories removed. `ruff`.

## PM run on the real DB (filled by PM)

_pending: dry-run output → owner OK → `--apply` output + backup path + new count_

## Evidence

_pending_
