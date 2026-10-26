# Audit Report - 2026-10-26 (version 2.0.0 source)

Scope: owner asked for an analysis of the current 2.0 source. Branch `owner-runs/20261001-r9`, HEAD `c7ac334` plus the uncommitted Phase 77 / Edge karaoke work in the working tree.

## Summary

| Tier | Status | Notes |
|---|---|---|
| 1 State | ⚠️ | Phase 77 and the karaoke repair are installed but not in git; phases 39–77 untagged (owner gates by design) |
| 2 Docs | ⚠️ | ROADMAP stale for Phase 49 and Phase 76; README/CHANGELOG match 2.0.0 |
| 3 Stack/code | ✅ after fixes | Full suite 2137 passed / 0 failed (was 18 failed); Ruff, JS syntax, renderer `tsc` clean |
| 4 Framework | skipped | not the ViePilot repo |

Size: backend 142 Python files (~29k lines), frontend 43 JS files (~14.5k lines), renderer 67 TS/TSX files, 190 test modules (~2,124 tests).

## Fixed during this audit (owner request 2026-10-26: remove dead old-version code)

- Deleted the retired OmniVoice engine: `backend/ai/tts/omnivoice_service.py`, `omnivoice_worker.py`, `omnivoice-requirements.txt`, `scripts/setup_omnivoice.ps1`, the `DIE_OMNIVOICE_*` settings, the `OMNIVOICE_*` constants and its `.gitignore` entries.
- Removed the always-empty `LEGACY_TTS_ENGINES` mapping (no-op lookups in `voice.py`, `tts_service.py`, `schemas/project.py`) and the unused `Api.listTtsEngines`.
- Removed tests for deleted features (`test_omnivoice_service.py`, `test_vocal_cue_annotation.py`, cue-synthesis tests); remaining tests now assert that OmniVoice is rejected (422) and that Edge is the only engine.
- **Bug found and fixed:** migration 040 calls Python SQL functions (`retired_cue_text`, ...) that were registered only inside `_apply_migration` for that one filename. Every raw migration replay (the `db` test fixture and 4 test helpers) failed with `no such function: retired_cue_text`. Registration is now `database.register_migration_functions()` / `migration_functions()`, used by every runner.
- Kept on purpose: `vocal_cues.caption_text` (still strips legacy tags from old scripts) and the `tts_engine` / `voice_description` DB columns (removing them needs a migration).

## Open findings

| ID | Severity | Finding |
|---|---|---|
| BUG-051 | high | ✅ fixed 2026-10-26: 15 stale tests updated, 3 real UI bugs fixed (see the request) |
| BUG-052 | high | ✅ resolved 2026-10-26: Phase 77, karaoke repair, cleanup and fixes committed (not pushed) |
| ENH-055 | low | ROADMAP status drift (Phase 49 "5/10", Phase 76 "not packaged") |
| ENH-056 | medium | CORS allows any localhost port with credentials; Step 4 "Listen" shows raw provider error text |

### BUG-051 failures by cause

- Remotion render path (10 tests: `test_video_service_remotion`, `test_video_soundtrack`, `test_voice_cache_invalidation`, `test_activity_video_props`): new `render_audio` code requires `fps` in props (`KeyError: 'fps'`) and a real audio file under the public directory; test mocks predate it. Decide whether production should default `fps` or the tests should supply it.
- Step 1 (5 tests): Phase 77 now always sends `voice_description: ""`, and a `select` stays enabled on read-only projects.
- `test_script_pipeline::test_versioned_script_job_annotates_only_after_validation`: still expects the removed annotation AI call.
- `test_tts_shell_browser::test_inspector_listen_failure_is_friendly_and_unlocks`: `step4_tts.js` shows `error.message` (raw provider text) instead of the friendly message; introduced in `c0f4f58`.
- `test_voice_picker_browser::test_profile_edit_keeps_project_voice...`: needs triage.

### BUG-052 detail

`backend/media/video_renderer_remotion.py` imports the untracked `backend/media/render_audio.py`; `backend/db/database.py` imports the untracked `backend/db/edge_only_restore.py` and applies the untracked migration `040_edge_plain_speech.sql`. A checkout of HEAD plus only the tracked changes fails at import time.

## Stack guardrails (for vp-auto preflight)

- Every migration runner (app and tests) must call `register_migration_functions` before replaying SQL.
- Run the full pytest suite before packaging; Phase 77 shipped with no tests run, and it now has 18 failures.
- Commit new modules together with the tracked files that import them.
- UI error banners show fixed friendly text; provider error text goes to logs only.
- Dynamic `UPDATE ... SET {keys}` stays limited to internally built key sets (currently true).
