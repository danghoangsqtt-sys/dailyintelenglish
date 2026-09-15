# Task 3.3: Final Cleanup

## Meta
- **ID**: 3.3
- **Phase**: 3
- **Status**: done (2026-09-15)
- **Priority**: low (closes Phase 3)
- **Assignee**: PM (Claude Code)

## Doc-First Gate

User chose to continue with Task 3.3 (over stopping) at a `/vp-auto` control point
(2026-09-15), right after Task 3.2's completion. ROADMAP.md's "3.3 Final Cleanup" bullet
has 4 items. Audited each against the real codebase before assuming any needed work
(same discipline as Task 2.2/2.3's audits):

1. **Remove `print()` debug statements → `logging`**: `grep -rn "print(" app/
   --include="*.py"` returns **zero matches** — every service already uses
   `logging.getLogger(__name__)` (confirmed in `tts_service.py`,
   `script_service.py`, etc.). **Already satisfied, no code needed.**
2. **`.env.example`**: exists (`.env.example`, created at project crystallization
   2026-09-10) but is stale — it lists 5 settings fields that are dead code with zero
   real usages anywhere (`grep -rn` confirms): `GOOGLE_TTS_API_KEY`, `AZURE_TTS_API_KEY`,
   `AZURE_TTS_REGION` (vestiges of the original pre-decision multi-engine TTS design —
   Edge TTS is now the sole official engine, see `docs/tts-setup.md`), and
   `OMNIVOICE_DEVICE`/`OMNIVOICE_MAX_CONCURRENT` (OmniVoice's real concurrency limit is
   the separate hardcoded `MAX_CONCURRENT_TTS` constant in `constants.py`, unrelated to
   this settings field). **Real gap, needs fixing**: remove these 5 dead fields from both
   `app/core/config.py`'s `Settings` class and `.env.example` so a new setup doesn't
   configure API keys/settings that do nothing. `OMNIVOICE_MODEL_PATH` stays (real,
   used by `tts_service.py`/`app/api/tts.py`).
3. **`requirements.txt` complete and pinned**: every entry already uses `==` (the one
   `>=` match is a `python_version >= "3.13"` marker condition, not a package version
   pin). **Already satisfied, no code needed** — this was done during Phase 2's
   structural-risk audit (see TRACKER.md, 2026-09-14).
4. **Git tag `v1.0.0-beta`**: apply after the above are verified and pushed.

## Objective
- Remove the 5 dead `Settings` fields from `app/core/config.py`.
- Update `.env.example` to match — only real, used env vars remain.
- Re-run the full test suite (this is a real `app/` code change, unlike Tasks 3.1/3.2)
  to confirm zero regressions before closing Phase 3.
- Tag `v1.0.0-beta` once state docs are updated and pushed.

## Allowed files
- `app/core/config.py`
- `.env.example`
- `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`,
  `.viepilot/phases/03-review-documentation/PHASE-STATE.md`, `CHANGELOG.md`

## Verification
- `grep -rn "GOOGLE_TTS_API_KEY\|AZURE_TTS_API_KEY\|AZURE_TTS_REGION\|OMNIVOICE_DEVICE\|OMNIVOICE_MAX_CONCURRENT" app/ tests/` returns nothing.
- Full suite (`pytest tests/ -q`) still green after the `Settings` change.
- `ruff check app/` clean.

## Implementer Evidence (2026-09-15)

- `grep -rn "print(" app/ --include="*.py"` → 0 matches (confirmed before touching
  anything, not assumed).
- `grep -n ">=" requirements.txt` → the only match is a `python_version >= "3.13"`
  marker condition, not an unpinned package version. Every dependency uses `==`.
- Removed 5 dead `Settings` fields (`GOOGLE_TTS_API_KEY`, `AZURE_TTS_API_KEY`,
  `AZURE_TTS_REGION`, `OMNIVOICE_DEVICE`, `OMNIVOICE_MAX_CONCURRENT`) from
  `app/core/config.py` after confirming zero real usages anywhere in `app/`/`tests/`
  (`grep -rn` — the real `MAX_CONCURRENT_TTS` concurrency limit is a separate hardcoded
  constant in `constants.py`, unrelated to the removed `OMNIVOICE_MAX_CONCURRENT`
  setting). Updated `.env.example` to match — only real, used vars remain
  (`DIE_GEMINI_API_KEY`, `DIE_APP_HOST`, `DIE_APP_PORT`, `DIE_DEBUG`, `DIE_DATA_DIR`,
  `DIE_OMNIVOICE_MODEL_PATH`, `DIE_FFMPEG_PATH`).
- `venv\Scripts\python -c "from app.core.config import settings; print(settings.DATA_DIR,
  settings.FFMPEG_PATH)"` → loads correctly.
- `ruff check app/core/config.py` → `All checks passed!`
- Full suite: 2 full runs (1285.10s and 1054.27s — both abnormally slow due to real
  system load, a Chrome Remote Desktop session active on this machine) each hit exactly
  1 failure, `test_generate_script_backoff_sequence_is_1s_2s_4s` — the project's
  pre-existing, TRACKER-documented Gemini-retry timing flake, unrelated to this task's
  `config.py`-only change. Confirmed via isolated re-run: passed instantly (0.56s) both
  times. 532/533 + the 1 known flake = effectively 533/533. See TRACKER.md Known Issues
  for the full record of this occurrence.

## PM Acceptance (2026-09-15)

Accepted — all 4 ROADMAP items resolved (2 already satisfied, confirmed by audit rather
than assumed; 2 required a real, disclosed fix). The one test failure across two runs is
the same pre-existing flake this project has tracked since 2026-09-12, confirmed
non-regressive via isolated re-run and by code-path analysis (the change touched nothing
`script_service.py` depends on). This closes Task 3.3 and Phase 3 in full.
