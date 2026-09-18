# Task 12.2: Package as a standalone Windows `.exe` (PyInstaller)

## Meta
- **ID**: 12.2 (second task of Phase 12 — Settings & Packaging)
- **Phase**: 12
- **Status**: in_progress
- **Priority**: medium (usability — removes the manual `venv`/`pip install` setup
  step for running a trial)
- **Assignee**: PM (Claude Code), self-implemented per the standing policy
  ([[feedback_self_implement_no_codex]])

## Doc-First Gate

Origin: same user request as Task 12.1, scoped via `AskUserQuestion` — user chose
"standalone `.exe` via PyInstaller" over a simple install script or Docker.

## Current state (read directly before planning)
- Dev run today is `uvicorn app.main:app --reload --port 8000` (README Quick
  Start) — `--reload` spawns a subprocess by re-invoking the running script's file
  path, which does not work the same way once frozen; a frozen build needs a
  programmatic `uvicorn.run(app, reload=False)` entrypoint instead.
- **5 places resolve filesystem paths via `Path(__file__)` walked up to the
  project root**, each independently: `app/main.py` (`PROJECT_ROOT`),
  `app/services/thumbnail_service.py` (`PROJECT_ROOT`),
  `app/services/video_service.py` (`TEMPLATE_DIR`), `app/core/prompt_loader.py`
  (`PROMPTS_DIR`), `app/db/database.py` (`MIGRATIONS_DIR`, relative to its own
  file instead of the project root). None of this is guaranteed to still point at
  real on-disk files once frozen — PyInstaller compiles pure-Python modules into
  an internal archive; `__file__`-based directory walking is only reliable for
  actual data files that were explicitly staged via `--add-data`, at whatever
  internal path they were staged at.
- `Settings.DATA_DIR` (`app/core/config.py`) defaults to the relative path
  `Path("data")` — fragile for a double-clicked `.exe` (depends on the process's
  working directory, which isn't guaranteed to be the exe's own folder for every
  launch method) and wrong for an app installed somewhere a normal user account
  can't write (e.g. under `Program Files`).
- `Settings.FFMPEG_PATH` defaults to `"ffmpeg"`, resolved via `shutil.which` /
  system PATH (`app/core/system_checks.py`, `scripts/check_dependencies.py`) —
  **not bundled** in this task; still expected system-installed. Bundling a real
  ffmpeg binary adds real licensing considerations (build-dependent GPL/LGPL) and
  ~80MB+ to the package; out of scope, documented as a known limitation instead.
- This machine runs Python 3.14.7 — very recent. PyInstaller's Python 3.14
  support is unverified before this task; will be confirmed by actually attempting
  the build (per this project's "must actually run it, not just verify it
  compiles" discipline — see the `run` skill) rather than assumed.
- `requirements.txt` has no `pyinstaller` entry yet.

## Required decisions
1. **Build mode: `--onedir`, not `--onefile`.** A folder with the `.exe` plus its
   dependencies alongside is faster to start (no self-extraction on every launch),
   easier to debug if something's missing, and the standard shape for a "real"
   packaged desktop-style app — matches the recommended option's own framing.
2. **Centralize path resolution** instead of touching each of the 5
   `Path(__file__)`-walking call sites' logic ad hoc: new `app/core/paths.py`
   with a single `get_project_root()` that returns `Path(sys._MEIPASS)` when
   `sys.frozen` is set (PyInstaller's staging directory for every `--add-data`
   resource, both onedir and onefile), else the existing
   `Path(__file__).resolve().parent.parent.parent` computation unchanged. All 5
   call sites switch to calling it — behavior identical when running from source
   (verified: existing test suite must stay green with zero changes needed).
3. **`DATA_DIR` default becomes frozen-aware**: `%LOCALAPPDATA%\DailyIntelEnglish
   Studio\data` when `sys.frozen`, else the existing relative `Path("data")` —
   via a `default_factory`, so `DIE_DATA_DIR` (env/`.env`) still overrides either
   default exactly as today.
4. **New desktop entrypoint**, not a change to `app/main.py` or the dev workflow:
   `app/desktop_launcher.py`, only imported/used by the frozen build. Calls
   `uvicorn.run(app, reload=False)` directly (not the CLI, not `--reload`),
   auto-opens the user's browser once the port actually accepts connections
   (polls with a plain `socket.create_connection` — no new dependency), and if
   the port is already open when it starts (a second double-click of the exe),
   just opens the browser to the existing instance instead of crashing on a bind
   error.
5. **ffmpeg and the OmniVoice model directory are not bundled** — documented
   limitation, not a gap silently left unmentioned. The packaged app's `/health`
   endpoint and `scripts/check_dependencies.py` already report ffmpeg status
   honestly either way.
6. **Build must be actually run**, not just confirmed to compile: launch the
   built `.exe`, hit it with Playwright the same way Task 12.1 was verified,
   confirm the dashboard loads, a page navigates, and the Settings page works
   (proves both static frontend files and the DB path are correctly resolved in
   the frozen build).

## Proposed file-level plan
- `app/core/paths.py` (new): `get_project_root() -> Path`.
- `app/main.py`, `app/services/thumbnail_service.py`,
  `app/services/video_service.py`, `app/core/prompt_loader.py`,
  `app/db/database.py`: switch their `PROJECT_ROOT`/`PROMPTS_DIR`/`TEMPLATE_DIR`/
  `MIGRATIONS_DIR` constants to derive from `get_project_root()`.
- `app/core/config.py`: `DATA_DIR` becomes `Field(default_factory=_default_data_dir)`
  with the frozen-aware logic described above.
- `app/desktop_launcher.py` (new): the packaged app's real entrypoint (`main()`).
- `daily_intel_english_studio.spec` (new, repo root): PyInstaller spec — onedir,
  `app/desktop_launcher.py` as the script, `--add-data` for `frontend/`,
  `prompts/`, `app/db/migrations/` at their matching relative paths, app name
  `DailyIntelEnglishStudio`.
- `scripts/build_exe.ps1` (new): thin wrapper — installs `pyinstaller` if missing,
  runs the spec, prints the output folder path. Reproducible build, not a one-off
  local hack.
- `requirements.txt`: add `pyinstaller` (pinned) under a clearly-labeled packaging
  section, not mixed into the runtime dependency list.
- `README.md`: new "Packaging as a standalone `.exe`" subsection once verified
  working (build command + where the output lands + the ffmpeg/OmniVoice caveat).
- No test file planned up front — this task's real verification is an actual
  build + a Playwright pass against the running packaged exe (documented as
  Implementer Evidence), not a unit test, since PyInstaller's own behavior isn't
  something the existing pytest suite can exercise meaningfully.

## Allowed files
- `app/core/paths.py`
- `app/main.py`
- `app/services/thumbnail_service.py`
- `app/services/video_service.py`
- `app/core/prompt_loader.py`
- `app/db/database.py`
- `app/core/config.py`
- `app/desktop_launcher.py`
- `daily_intel_english_studio.spec`
- `scripts/build_exe.ps1`
- `requirements.txt`
- `README.md`

## Acceptance criteria
- [ ] Existing full test suite stays green with these path-resolution changes
      (proves the non-frozen behavior is byte-for-byte unchanged).
- [ ] `pyinstaller` successfully builds the spec with no errors.
- [ ] The built `.exe`, launched directly (not from a dev shell with the venv
      active), actually serves the app on `http://localhost:8000` and
      auto-opens the browser there.
- [ ] Dashboard, at least one step page, and the new Settings page all load and
      function correctly from the frozen build (verified with Playwright against
      the real running packaged exe, not just curl/health).
- [ ] Launching the exe a second time while the first is still running opens the
      browser to the existing instance instead of crashing.
- [ ] `DATA_DIR` under the frozen build resolves to a real, writable, per-user
      location — confirmed by checking a project actually gets created there.
- [ ] README documents the build command and the ffmpeg/OmniVoice bundling
      limitation honestly.
