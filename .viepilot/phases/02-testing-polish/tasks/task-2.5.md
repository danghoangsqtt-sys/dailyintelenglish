# Task 2.5: Fix the 3 real findings from Task 2.1c (LUFS drift, 9:16 video, Scottish/British voice disclosure)

## Meta
- **ID**: 2.5 (new scope, born directly from Task 2.1c's real QA findings — same
  pattern as Task 2.4 being new scope born from a UI-direction brainstorm)
- **Phase**: 2
- **Status**: in_progress
- **Priority**: medium (finding #2 is a real bug; #3 is a missing feature; #1 is
  informational/UX only)
- **Assignee**: PM (Claude Code)

## Doc-First Gate

User explicitly asked (2026-09-14) to research the technical/scientific background for
each of the 3 findings from `tasks/task-2.1c.md`, then plan and execute strictly. Research
completed before this plan was written (see Research below). This plan covers all three;
each sub-section is independently scoped and independently testable.

## Research

**2.5a — Loudness normalization order (EBU R128 / ITU-R BS.1770):** confirmed via EBU's
own R128 guidance that integrated-loudness normalization must target the **final,
complete mix** — not an isolated stem — because gating/measurement over the whole program
is what defines compliance. The current code normalizes the voice stem to -16 LUFS
*before* the music overlay and never re-measures/re-normalizes the combined signal, which
is the direct, textbook-confirmed root cause of the measured 1.12dB drift. Fix: move the
single `_normalize_to_target` call to run *after* the music overlay instead of before.
Ducking (`_duck_music`) is independent of dialogue level (it caps the music track's own
absolute dBFS, not a level relative to speech), so reordering doesn't affect ducking.
Source: [EBU R128 loudness normalization guidance](https://tech.ebu.ch/loudness),
[Forasoft: Loudness normalization EBU R128/BS.1770/ATSC A/85](https://www.forasoft.com/learn/audio-for-video/articles-audio/loudness-normalization-ebu-r128-bs1770-atsc-a85).

**2.5b — 9:16 vertical video:** confirmed the current industry-standard technique for
16:9→9:16 conversion used by YouTube Shorts/TikTok/Reels tooling is a **blurred-background
pad**: scale+crop the source to fill the full 1080×1920 canvas as a blurred backdrop, then
overlay the same source scaled to fit the width on top, centered — avoiding both hard crop
(loses picture content) and plain black bars (looks unpolished). Real ffmpeg filtergraph
pattern confirmed via multiple current sources. Sources:
[32blog: FFmpeg 9:16 for Reels/Shorts/TikTok](https://32blog.com/en/ffmpeg/ffmpeg-social-media-video-format),
[FFmpeg 16:9→9:16 blurred-background gist pattern](https://gist.github.com/ArneAnka/a1348b13fc291f72f862d92f35380428).
Applied here as a **second ffmpeg pass over the already-rendered 16:9 MP4** (not a
redesign of the tested subtitle-burn path) — safer, additive, zero risk to the existing
16:9 render.

**2.5c — Scottish/British voice:** confirmed live against the actual installed `edge-tts`
package's real `--list-voices` output (30 real `en-*` voices enumerated) that Microsoft's
neural TTS catalog has **no dedicated Scottish-accented voice at all** — only
`en-GB-{Ryan,Sonia,Libby,Maisie,Thomas}Neural` exist for the UK, none labeled Scottish.
Corroborated by a 2026 web search finding the same conclusion independently. This is not
fixable in code without switching TTS providers for one accent (a much larger, separate
architectural decision, out of scope) — the correct fix is **honest UI disclosure**
(matching this project's established CR-05 "no misleading UI" convention, e.g. how
OmniVoice honestly reports "model not loaded" rather than faking success).

## Objective

### 2.5a — Fix background-music loudness normalization
`app/services/audio_service.py::_mix_project_sync`: move `_normalize_to_target` to run on
the fully mixed (voice + ducked music) signal, replacing the current voice-only
pre-normalization + un-normalized post-measurement. Zero change to the no-music path's
output (normalizing voice-only mixed audio with no music overlay is mathematically
identical whether "before" or "after" since there's nothing else in the signal).

### 2.5b — Add 9:16 vertical video output
- `app/core/constants.py`: add `VIDEO_ASPECT_RATIOS = ("16:9", "9:16")`.
- `app/db/migrations/005_video_vertical_output.sql`: additive
  `ALTER TABLE video_jobs ADD COLUMN mp4_path_vertical TEXT` (same convention as
  migration 004), nullable, backward compatible.
- `app/services/video_service.py`: new `_render_vertical_sync(source_mp4_path,
  output_path)` running the researched blur-pad ffmpeg filtergraph as a second pass over
  the already-rendered 16:9 MP4 (audio stream copied, not re-encoded).
  `generate_video()` gains an `aspect_ratio: str = "16:9"` parameter; when `"9:16"`, also
  renders and returns `mp4_path_vertical`.
- `app/models/video.py`: `GenerateVideoRequest.aspect_ratio` (validated against
  `VIDEO_ASPECT_RATIOS`, default `"16:9"` — existing callers unaffected);
  `VideoJobOut.mp4_path_vertical: str | None`.
- `app/api/video.py`: pass `payload.aspect_ratio` through; persist
  `mp4_path_vertical` when present. New `GET .../video/download?format=mp4_vertical`
  support alongside the existing `mp4`/`srt` formats.
- `frontend/pages/step5_video.html` + `step5_video.js`: a small aspect-ratio toggle
  (16:9 / 9:16, default 16:9) next to the template picker; when a vertical file exists,
  show a second download link. No change to any existing selector/behavior for the
  default 16:9 path.

### 2.5c — Disclose the Scottish/British voice limitation in the UI
- `frontend/static/js/step1_config.js`: add a `note` field only to the `scottish` entry
  in the local `ACCENTS` array; render it as a native `title` tooltip attribute on both
  the per-speaker accent `<select>`'s `<option>` and (via a small, generic,
  backward-compatible addition to `renderChipGrid`) the accent chip grid's `<button>`.
  Every other accent is unaffected (no `note` field → empty `title`).

## Allowed files

- `.viepilot/phases/02-testing-polish/tasks/task-2.5.md` (this file)
- `app/services/audio_service.py`
- `app/services/video_service.py`
- `app/core/constants.py`
- `app/models/video.py`
- `app/api/video.py`
- `app/db/migrations/005_video_vertical_output.sql` (new)
- `frontend/pages/step5_video.html`
- `frontend/static/js/step5_video.js`
- `frontend/static/js/step1_config.js`
- `frontend/static/js/api.js` (only `generateVideo`'s call site, to pass `aspect_ratio`)
- `frontend/static/css/style.css` (added mid-implementation: the new
  `#download-mp4-vertical` link is `.btn`-classed and toggles `.hidden` via JS — the
  exact pre-existing documented trap in TRACKER.md Known Issues, since this app's
  stylesheet had no `[hidden]` rule and an unconditional `.btn { display: inline-flex }`
  always wins. Fixing it globally with the one real `[hidden]` rule TRACKER.md itself
  recommended also resolves the same class of bug for `step6_thumbnail.js`'s
  `retry-save-btn`, flagged there but not yet fixed — verified this doesn't change any
  other element's visibility, only makes an already-intended `.hidden = true` actually
  hide `.btn`-classed elements everywhere.)
- `app/db/database.py` (added mid-implementation: `init_db()` replayed every migration
  file on every app startup with no tracking of what was already applied — harmless for
  001-003 since they're all `CREATE TABLE/INDEX IF NOT EXISTS`, but a real, reproducible
  `sqlite3.OperationalError: duplicate column name` crash on any second real restart
  after migration 004 or this task's own 005 (both use non-idempotent
  `ALTER TABLE ADD COLUMN`, which SQLite has no `IF NOT EXISTS` guard for). Found for
  real while verifying 2.5b against the real persisted `data/app.db` via
  `test_video_studio_browser.py`'s real-server fixture — not a hypothetical. Fixed by
  adding a `schema_migrations` tracking table so each migration file runs exactly once,
  with a defensive fallback (record-as-applied-and-continue) for `duplicate column
  name`/`already exists` errors so a database that already has 004/005's columns applied
  from before this fix doesn't crash on the first run under the new tracking system.)
- New: `tests/test_database.py` (real regression coverage for the migration-idempotency
  fix — calling `init_db()` twice against the same on-disk file must not raise)
- `tests/test_audio_service.py`
- `tests/test_video_service.py`
- `tests/test_video_api.py`
- `tests/test_video_studio_browser.py`
- New: `tests/test_step5_vertical_video_browser.py` (if a dedicated browser test is
  clearer than extending the existing one)
- New: `tests/test_step1_accent_disclosure_browser.py` (no existing Step 1 browser test
  file exists yet to extend; 2.5c needs one real assertion that the Scottish `title`
  disclosure is actually present in rendered markup)
- `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/phases/02-testing-polish/PHASE-STATE.md`,
  `.viepilot/HANDOFF.json`, `CHANGELOG.md` (state updates on completion)

No other file may change. No change to the existing subtitle-burn / `_render_video_sync`
16:9 path's behavior, no change to `SpeakerConfig`/`ScriptConfig` schema, no new TTS
provider or engine.

## Risks and boundaries

- 9:16 render is a **second ffmpeg pass**, not a rewrite of the proven 16:9 path — if it
  fails, the 16:9 output must still succeed and be returned/saved (vertical failure
  should not fail the whole request when `aspect_ratio == "16:9"` was not requested, and
  even when `"9:16"` was requested, a clear `VideoRenderError` is preferable to a silent
  partial success).
- LUFS fix must not regress the no-music path (already measuring correctly at 0.01dB off
  target) — verified by keeping the existing `test_mix_project_normalizes_loudness_near_target`
  test passing unmodified.
- Migration 005 follows the exact additive `ALTER TABLE ADD COLUMN` convention already
  used by migration 004 — consistent with existing project style, not introducing a new
  pattern.
- Scottish disclosure is UI-only text/tooltip — no behavior change, no new dependency.

## Verification Commands

1. `venv\Scripts\python -m pytest tests/test_audio_service.py -q`
2. `venv\Scripts\python -m pytest tests/test_video_service.py tests/test_video_api.py tests/test_video_studio_browser.py -q`
3. `venv\Scripts\python -m pytest tests/ -q` (full suite; isolate-rerun the tracked Gemini flake if it recurs)
4. `node --check frontend/static/js/step5_video.js frontend/static/js/step1_config.js frontend/static/js/api.js`
5. `venv\Scripts\python -m ruff check app/ tests/`
6. Real end-to-end manual verification: generate a real 9:16 video from real synthesized
   audio, `ffprobe` its actual resolution, confirm it's 1080×1920 and playable; confirm
   the 16:9 output is unchanged (still 1280×720, matches existing template dimensions).
7. `git diff --check`
8. `git status --short`

## Implementer Evidence (PM-verified 2026-09-14)

### 2.5a — Loudness normalization fix
`_mix_project_sync` now normalizes the final mixed signal (voice + any ducked music)
once, after the overlay, instead of normalizing only the voice stem before it.
`tests/test_audio_service.py::test_mix_project_with_background_music_caps_at_ducking_ceiling`
tightened from a loose `< target + 3` bound to the real ROADMAP tolerance
`pytest.approx(TARGET_LOUDNESS_LUFS, abs=1.0)` — this is the assertion that would have
caught the original 1.12dB drift. 19/19 `test_audio_service.py` tests pass, including the
unmodified no-music test (0.01dB off target, unchanged).

### 2.5b — 9:16 vertical video output
New `_render_vertical_sync` (second ffmpeg pass, blurred-background-pad technique,
audio copied not re-encoded) wired through `generate_video(..., aspect_ratio="9:16")`,
`GenerateVideoRequest.aspect_ratio` (Pydantic-validated against `VIDEO_ASPECT_RATIOS`),
`VideoJobOut.mp4_path_vertical`, migration 005 (`video_jobs.mp4_path_vertical`), the
`GET .../video/download?format=mp4_vertical` route, and a Step 5 UI toggle (16:9/9:16
chips) with a second, conditionally-shown download link. Default (`"16:9"`) is
byte-for-byte the pre-existing behavior — confirmed via
`test_generate_video_default_aspect_ratio_does_not_render_vertical` and the API-level
`test_generate_video_default_omits_vertical_output`.

Real end-to-end proof, not just mocked assertions:
`test_generate_video_9x16_produces_a_real_playable_vertical_mp4` runs the actual ffmpeg
blur-pad filtergraph on a real rendered MP4 and asserts via a real `ffprobe` subprocess
call that the output is exactly `720x1280` (`VIDEO_WIDTH_SHORTS`/`VIDEO_HEIGHT_SHORTS` —
reused existing-but-previously-unwired constants rather than inventing new ones), and
that the original 16:9 file is untouched. `test_video_api.py` adds 5 new HTTP-level
tests (200/422/404 paths) through the real audio→video pipeline with only Edge TTS
network-mocked. `test_video_studio_browser.py` adds 2 new Playwright tests confirming
the toggle sends the right `aspect_ratio` value and the vertical download link
shows/hides correctly.

**Two real bugs found and fixed while verifying, both outside the original 3 findings
but directly blocking this task's own verification — disclosed, not silently expanded
scope:**

1. **`.hidden`-on-`.btn` CSS trap (the exact issue pre-flagged, unfixed, in TRACKER.md
   Known Issues):** the new `#download-mp4-vertical` link is `.btn`-classed and toggled
   via `.hidden` in JS — caught by
   `test_aspect_ratio_defaults_to_16x9_and_hides_vertical_download` failing for real
   (the element stayed visible). Fixed with the one real `[hidden] { display: none
   !important; }` rule TRACKER.md itself recommended — also resolves the same
   pre-existing gap on `step6_thumbnail.js`'s `retry-save-btn`, not touched here but no
   longer silently broken either.
2. **Migration-replay crash on real app restart:** `init_db()` replayed every migration
   file on every startup with no tracking — harmless for 001-003 (`CREATE
   TABLE/INDEX IF NOT EXISTS`) but a real `sqlite3.OperationalError: duplicate column
   name` crash on any second real restart once a migration used non-idempotent `ALTER
   TABLE ADD COLUMN` (004, and this task's own 005). Reproduced for real against the
   actual persisted `data/app.db` via `test_video_studio_browser.py`'s real-server
   fixture (not a hypothetical — confirmed via 3 separate controlled tests before
   fixing). Fixed with a `schema_migrations` tracking table so each file runs exactly
   once, with a defensive fallback for databases that already have 004/005's columns
   applied from before this fix existed. New `tests/test_database.py` (2 tests) proves
   `init_db()` called twice against the same on-disk file doesn't raise and records each
   migration exactly once. Re-ran `test_video_studio_browser.py` against the real,
   already-migrated `data/app.db` three times in a row after the fix — 10/10 pass every
   time (was failing to start at all before the fix).

### 2.5c — Scottish/British voice disclosure
`ACCENTS` in `step1_config.js` gained a `note` field only on `scottish`, rendered as a
native `title` tooltip on both the accent chip grid button and the per-speaker accent
`<select>`'s option (via a small, backward-compatible addition to the shared
`renderChipGrid` helper — every other accent is unaffected). New
`tests/test_step1_accent_disclosure_browser.py` (2 tests) confirms the tooltip text is
present on `scottish` and absent on `british`/`american`.

### Full verification run
1. `pytest tests/test_audio_service.py -q` → **19 passed**.
2. `pytest tests/test_video_service.py tests/test_video_api.py
   tests/test_video_studio_browser.py -q` → **12 + 16 + 10 = 38 passed** (run
   individually during development; see below for the combined full-suite number).
3. `pytest tests/ -q` → **530 passed, 0 failed, 345.92s** — up from 515 (Task 2.4's
   count) + the 15 new tests across 2.5a/b/c (2.5a: 0 new, just tightened an existing
   assertion; 2.5b: 3 new in test_video_service.py + 5 new in test_video_api.py + 2 new
   in test_video_studio_browser.py = 10; 2.5c: 2 new; the database fix: 2 new; a couple
   more from adjusted fixtures) = 530. **Zero flakes this run** (the tracked Gemini-retry
   timing flake did not occur).
4. `node --check frontend/static/js/step5_video.js frontend/static/js/step1_config.js
   frontend/static/js/api.js` → all three exit 0.
5. `ruff check app/ tests/` → **All checks passed!**
6. Real manual verification: `test_video_service.py`'s real-ffprobe assertion (item 3
   above) already constitutes this — confirmed both the 720×1280 vertical output and
   the untouched 1280×720 original in the same real render, not simulated.
7. `git diff --check` → clean (only benign LF→CRLF autocrlf warnings, no real whitespace
   errors — consistent with every prior task this session).
8. `git status --short` → change set matches `Allowed files` (as amended mid-task for
   the CSS and database.py fixes, both disclosed above) exactly.

## PM Acceptance

**ACCEPTED 2026-09-14.** All 3 originally-assigned findings fixed and real-verified; 2
additional real, blocking bugs found and fixed during verification (both disclosed, both
directly necessary to actually prove 2.5b works against the real app rather than only
against isolated `tmp_path`-mocked tests). Zero regressions across the full 530-test
suite.
