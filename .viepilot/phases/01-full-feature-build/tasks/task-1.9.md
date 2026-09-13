# Task 1.9: Step 7 — YouTube Package

## Meta
- **ID**: 1.9
- **Phase**: 1
- **Status**: done (2026-09-13) — both sub-tasks (1.9a, 1.9b) complete
- **Priority**: medium
- **Assignee**: AI (Claude Code, acting as PM + Implementer)

## Paths
- `app/services/youtube_service.py`
- `app/api/youtube.py`
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step7_youtube.js`

## Acceptance Criteria
- [x] Title options (3 variants: click-worthy, educational, SEO) — Gemini-generated, `responseJsonSchema` validated
- [x] Description with auto-generated timestamps/chapters — chapters are MEASURED from real audio when one exists (Sub-task 1.9b), or honestly ESTIMATED when it doesn't; the API response and UI both label which one applies
- [x] Tag generator (comma-separated, max 500 chars) — `YOUTUBE_TAGS_MAX_CHARS` enforced on the joined string
- [x] Full package download (.zip containing video, thumbnail, SRT, metadata.txt) — Sub-task 1.9b, 2026-09-13

## Forbidden Scope
- No auto-publishing to YouTube without explicit user export/consent

## Verification Commands
- `venv\Scripts\python -m pytest tests/`

## Implementation Notes (2026-09-12, Sub-task 1.9a: text-generation vertical slice)

Codex is out of quota; PM (Claude Code) is acting as both PM and Implementer for this task,
same rigor as reviewing an external implementer — self-plan, self-implement, self-verify with
real command output before accepting.

### Why split

Acceptance criterion 4 ("Full package download .zip containing video, thumbnail, SRT,
metadata.txt") needs a real video + SRT file, which do not exist yet (Task 1.7 Video Studio is
blocked on `ffmpeg`, same as Sub-tasks 1.6b/1.10b — see TRACKER.md Known Issues). Splitting
mirrors the pattern already used for Tasks 1.6/1.8/1.10.

- **Sub-task 1.9a (this one):** title options, description, auto-estimated chapters, and tags
  — all pure Gemini text generation + persistence + a display/regenerate UI. No zip, no
  video/ffmpeg dependency.
- **Sub-task 1.9b (deferred):** full `.zip` export bundling video + thumbnail + SRT +
  `metadata.txt`, once Task 1.7 exists.

### Schema change

`youtube_packages` (from `001_init.sql`) has never been read or written by any code — same
situation `002_learning_content.sql` documented for the old `learning_content` table (PM
decision 2026-09-10: drop and recreate rather than leave a confusingly similar unused table).
Following that precedent exactly: `003_youtube_package.sql` drops and recreates
`youtube_packages` with `title_options_json` (new — no column existed for title variants, even
though the task card has always required them) instead of the never-populated
`full_transcript`/`vocabulary_formatted`/`grammar_formatted`/`comprehension_formatted` columns,
which belong to the deferred zip/metadata.txt work (1.9b) and would be speculative now.

### Chapters/timestamps are honestly estimated, not measured

No real audio exists yet for this project (Task 1.6 Sub-task 1.6b/AudioService is also
blocked on `ffmpeg`). Chapter timestamps are therefore estimated from cumulative word count at
a fixed reading-speed constant (`YOUTUBE_CHAPTER_WORDS_PER_MINUTE`, documented as an estimate,
not a measurement), grouped at genre-appropriate topic-shift boundaries. The API response and
UI both label these as "Estimated" — never presented as exact. Once real audio duration exists
(1.6b/1.9b), a follow-up task can replace the estimate with the measured value without changing
the response shape (same `chapters_text` field).

### Behavior and approach

1. `app/models/youtube.py`: `TitleOption` (variant: Literal["click_worthy","educational","seo"],
   text: str, 1-100 chars), `YouTubePackageOut` (Gemini output: exactly 3 `TitleOption`s with
   distinct variants, `description` 1-5000 chars, `tags: list[str]` each non-blank, joined
   tag string must not exceed `YOUTUBE_TAGS_MAX_CHARS`). Semantic validation rejects duplicate
   variants or an over-length tag string — same strict-validation discipline as
   `ThumbnailSuggestionPack`.
2. `prompts/youtube/youtube_package.txt` (new Jinja2 template) + `render_youtube_prompt` in
   `app/core/prompt_loader.py`, following the exact `_render_thumbnail_prompt_sync` pattern
   (own `Environment`, own prompts dir, validates genre/CEFR before touching the filesystem).
3. `app/services/youtube_service.py`: `generate_package(project, script_lines)` — requires a
   non-empty script (`ValidationError` otherwise, mirroring `learning_service`'s check),
   `_call_gemini`/`_generate_with_retry` reusing the identical `responseJsonSchema` +
   429-only-backoff + prompt-hash-logging pattern as script/learning/thumbnail services (no
   new pattern invented). `estimate_chapters(script_lines)` is a pure, independently unit-tested
   function: cumulative word count / `YOUTUBE_CHAPTER_WORDS_PER_MINUTE` → seconds → `MM:SS`,
   one chapter per topic-shift heuristic (a new speaker turn after N lines, N configurable via
   constant) formatted as YouTube's plain-text chapter list (`00:00 Introduction`, ...).
   `save_package`/`get_package` UPSERT into `youtube_packages` (matches the `learning_service`
   UPSERT pattern, one row per project).
4. `app/api/youtube.py`: `POST /api/projects/{id}/youtube/generate` (reads script via
   `_read_transaction`, calls Gemini with no lock held, writes via `_write_transaction`,
   mirrors `learning.py`'s route shape exactly), `GET /api/projects/{id}/youtube` (null if not
   yet generated).
5. `app/main.py`: register the youtube router; add `GET /step7` serving
   `frontend/pages/step7_youtube.html`.
6. `frontend/pages/step7_youtube.html` + `step7_youtube.js`: 3 title-option cards (labelled by
   variant) with copy-to-clipboard, description + estimated-chapters display, tag list display,
   "Generate"/"Regenerate" (confirm-gated like Learning Content's Regenerate Pack), loading
   state, friendly-only errors (CR-05, via `api.js`). No zip/download control in this slice —
   an explicit "Full package export (video+thumbnail+SRT) — coming after Task 1.7" note instead
   of a dead/fake button.
7. `.viepilot/ARCHITECTURE.md`: update the YouTube Package section to mention
   `title_options_json` and that chapters are estimated pending Task 1.7 real audio duration.

### File-level plan / `allowed_files`

- `.viepilot/phases/01-full-feature-build/tasks/task-1.9.md` (this plan + evidence)
- `.viepilot/phases/01-full-feature-build/PHASE-STATE.md`, `.viepilot/TRACKER.md`,
  `.viepilot/HANDOFF.json`, `.viepilot/ROADMAP.md`, `CHANGELOG.md` (state updates, PM step)
- `.viepilot/ARCHITECTURE.md` (YouTube Package section + data model only)
- `app/db/migrations/003_youtube_package.sql` (new)
- `app/core/constants.py` (title variants, chapter word-rate constant, topic-shift line count)
- `app/core/exceptions.py` (`YouTubePackageGenerationError`)
- `app/core/prompt_loader.py` (add `render_youtube_prompt`, its own Jinja env)
- `app/models/youtube.py` (new)
- `app/services/youtube_service.py` (new)
- `app/api/youtube.py` (new)
- `app/main.py` (register router + `/step7` route only)
- `prompts/youtube/youtube_package.txt` (new)
- `frontend/pages/step7_youtube.html`, `frontend/static/js/step7_youtube.js` (new)
- `frontend/static/js/api.js` (centralize the 2 new calls, CR-05)
- `tests/test_youtube_prompt.py`, `tests/test_youtube_service.py`, `tests/test_youtube_api.py` (new)

No AudioService/ffmpeg/video work, no zip export, no real (non-estimated) timestamps, no
status/checkbox edits beyond this task's own, no unrelated refactor.

### Risks and limits

- Chapter timestamps are estimates (documented above), not measured — must never be presented
  as exact in the UI copy.
- `youtube_packages` schema change follows the exact precedent already PM-approved for the same
  situation (unused table, `002_learning_content.sql`) — no new pattern, no migration-tracking
  mechanism needed since none existed before either.
- Topic-shift chapter heuristic (new chapter every N lines) is a simple, honest approximation,
  not real topic-segmentation NLP — acceptable for a draft aid, not claimed as more.

### Verification commands

- `venv\Scripts\python -m pytest tests/test_youtube_prompt.py -q`
- `venv\Scripts\python -m pytest tests/test_youtube_service.py -q`
- `venv\Scripts\python -m pytest tests/test_youtube_api.py -q`
- `venv\Scripts\python -m pytest tests/ -q`
- `venv\Scripts\python -m ruff check app/ tests/`
- `node --check frontend/static/js/api.js`
- `node --check frontend/static/js/step7_youtube.js`
- `git diff --check`

## Implementer Evidence (2026-09-12) — Claude Code acting as both PM and Implementer

### Delivered

- `app/db/migrations/003_youtube_package.sql` (+ synced `.viepilot/schemas/database-schema.sql`):
  drops and recreates `youtube_packages` with `title_options_json`, dropping the
  never-populated transcript/vocabulary/grammar/comprehension columns (moved to 1.9b).
- `app/models/youtube.py`: `TitleOption`, `YouTubePackageOut` — exactly 3 titles (one per
  variant, enforced via `model_validator`), description 1-5000 chars, tags list validated
  nonblank with a joined-length check against `YOUTUBE_TAGS_MAX_CHARS`.
- `prompts/youtube/youtube_package.txt` + `render_youtube_prompt` in `app/core/prompt_loader.py`
  (own Jinja env, validates genre/CEFR before touching the filesystem — same pattern as
  `_render_thumbnail_prompt_sync`).
- `app/services/youtube_service.py`: `generate_package()` follows the exact
  `responseJsonSchema` + 429-only-backoff + prompt-hash-logging pattern as script/learning/
  thumbnail services (verified via `test_call_gemini_includes_response_json_schema`).
  `estimate_chapters()` is a pure function (word-count-based estimate, first chapter always
  "00:00 Introduction", new chapter every `YOUTUBE_CHAPTER_MIN_LINES` lines) — unit-tested
  in isolation, no Gemini call involved. `save_package`/`get_package` UPSERT into
  `youtube_packages`, mirroring `learning_service`'s pattern exactly.
- `app/api/youtube.py`: `POST .../youtube/generate`, `GET .../youtube` — thin routes using
  `_read_transaction`/`_write_transaction`, no lock held across the Gemini call.
- `app/main.py`: router registered, `GET /step7` added.
- `frontend/pages/step7_youtube.html` + `step7_youtube.js`: read-only display (3 title
  cards, description, tags, estimated-chapters block explicitly labelled "Estimated"),
  copy-to-clipboard per section, confirm-gated Regenerate, friendly-only errors (raw Gemini
  error text never reaches the DOM), an explicit note that full zip export awaits Task 1.7
  rather than a dead/fake download button.
- `frontend/static/js/api.js`: 2 new centralized calls (CR-05).
- Tests: `tests/test_youtube_prompt.py`, `tests/test_youtube_service.py`,
  `tests/test_youtube_api.py`, `tests/test_youtube_browser.py` (6 real-Chromium scenarios).

### Two real bugs found and fixed before landing (self-caught, not shipped broken)

1. **Tag round-trip whitespace bug**: `_row_to_package` split the stored comma-joined tag
   string on `,` without stripping, so every tag after the first came back with a leading
   space (`" english learning"` instead of `"english learning"`). Caught by
   `test_save_and_get_package_roundtrip` and `test_generate_returns_200_and_persists` both
   failing on first run. Fixed by stripping each tag after split.
2. **`[hidden]` attribute silently ignored on `#generate-panel`**: the panel's own
   `#generate-panel { display: grid; ... }` rule (ID selector) has higher CSS specificity
   than the browser's default `[hidden] { display: none }` rule, so setting
   `generatePanel.hidden = true` in JS had no visual effect — the panel stayed visible
   underneath the content. Caught by
   `test_existing_package_loads_directly_without_generate_click` (a real Playwright browser
   test, not a unit test) asserting `#generate-panel` was actually hidden. Fixed by adding
   an explicit `#generate-panel[hidden] { display: none; }` rule.

### Verification output (all re-run fresh just before this entry, not reused from earlier)

`venv\Scripts\python -m pytest tests/test_youtube_prompt.py tests/test_youtube_service.py tests/test_youtube_api.py tests/test_youtube_browser.py -q`

```text
36 passed
```

`venv\Scripts\python -m pytest tests/ -q`

```text
350 passed, 2 warnings in 86.46s
```

`venv\Scripts\python -m ruff check app/ tests/`

```text
All checks passed!
```

`node --check frontend/static/js/api.js` and `node --check frontend/static/js/step7_youtube.js`: both exit 0.

## PM Acceptance (2026-09-12)

**Accepted.** Both bugs above were caught by the test suite itself (not discovered later by
a reviewer) — the tag-stripping bug by a unit-level roundtrip test, the CSS-specificity bug
only by an actual browser test, which is exactly why Sub-task 1.8b/1.10a's real-Chromium
coverage requirement exists. Chapters are honestly labelled as estimates in both the API
shape and the UI copy. This closes Sub-task 1.9a. Sub-task 1.9b (full `.zip` export) remains
blocked on Task 1.7 (`ffmpeg`).

## Implementation Notes (2026-09-13, Sub-task 1.9b: full .zip export + measured chapters)

User unreachable this session (traveling), autonomous PM+Implementer authorization
standing. Task 1.7 Sub-task 1.7a (real video+SRT) and Task 1.6 Sub-task 1.6b (real
per-line timestamps) now both exist, unblocking this sub-task exactly as planned.

### Measured chapters (was: word-count estimate only)

`youtube_service.generate_package()` now accepts an optional `timestamps` argument (the
completed `audio_jobs.timestamps` list, when one exists). When present, chapters are built
from AudioService's real measured `start_sec` values via a new `real_chapters_from_timestamps()`
(same topic-shift heuristic as `estimate_chapters` — new chapter every
`YOUTUBE_CHAPTER_MIN_LINES` lines, first chapter always "00:00 Introduction" — just fed
real seconds and the real line text AudioService's timestamps now carry, instead of a
word-count projection). When no audio exists yet, falls back to the existing
`estimate_chapters()` unchanged — 1.9a's behavior is preserved for a project with no audio.

A new `chapters_estimated: bool` flag is persisted alongside `chapters_text` so the UI can
say the true thing instead of always claiming "Estimated" (which became false the moment
real timestamps exist). Schema change: **additive** `ALTER TABLE ADD COLUMN` this time
(`004_youtube_chapters_measured.sql`), not a drop-and-recreate like `002`/`003` — those were
justified specifically because `youtube_packages` was dead/unused at the time; it is now a
live, working table (1.9a shipped and works), so the correct move is additive.

### Full `.zip` export

New `GET /api/projects/{id}/youtube/export` streams an in-memory zip (no temp file to
clean up) containing:
- `video.mp4` (from the completed `video_jobs` row, Task 1.7)
- `thumbnail.png` (the current favorite `is_selected=1` thumbnail's 16:9 PNG, Task 1.8 —
  YouTube's upload requirement is a single 16:9 image, so 9:16 isn't included)
- `subtitles.srt` (from the same `video_jobs` row)
- `metadata.txt` (plain text: all 3 title variants, description, tags, chapters)

Requires all three (YouTube package, completed video job, a selected thumbnail favorite)
to exist — a clear `ValidationError` names exactly which piece is missing rather than a
generic failure, so the user knows which earlier step to go back and finish.

Files:
- `app/db/migrations/004_youtube_chapters_measured.sql` (new, additive).
- `.viepilot/schemas/database-schema.sql` (synced, same precedent as 1.9a).
- `app/services/youtube_service.py`: `real_chapters_from_timestamps(timestamps) -> str`,
  `generate_package(project, script_lines, timestamps=None)`, `_row_to_package` reads
  `chapters_estimated`, `save_package` persists it, `build_export_zip(package, video_job,
  thumbnail_row) -> bytes` (pure — takes already-fetched rows, doesn't touch the DB itself).
- `app/api/youtube.py`: `generate_youtube_package` now also reads the audio job (if any)
  and passes its timestamps through; new `GET .../youtube/export` route reads the package,
  video job, and thumbnail rows via their existing service `get_*` functions and calls
  `build_export_zip`.
- `frontend/pages/step7_youtube.html` + `step7_youtube.js`: the "Estimated..." note now
  reads correctly based on `chapters_estimated` (a real "✅ Measured from the final audio"
  message once true), plus a "Download full package (.zip)" button — disabled with a
  tooltip-style hint when video/thumbnail aren't ready yet rather than a dead link.
- `tests/test_youtube_service.py`: `real_chapters_from_timestamps` unit tests, and
  `generate_package` with/without `timestamps` producing the right `chapters_estimated`.
- `tests/test_youtube_api.py`: export route tests (success with a real in-memory zip whose
  contents are verified, and each missing-piece 422 case).

Forbidden Scope: no change to the existing estimate-chapters behavior for projects with no
audio yet, no change to `youtube_packages` beyond the additive column, no Shorts (9:16)
thumbnail in the zip, no auto-upload to YouTube (Task 1.9's own Forbidden Scope already
rules this out).

## Sub-task 1.9b Result (2026-09-13) — DONE, closes Task 1.9

Delivered exactly the plan above. New: `app/db/migrations/004_youtube_chapters_measured.sql`
(additive), `.viepilot/schemas/database-schema.sql` synced, `real_chapters_from_timestamps()`
+ `build_export_zip()` in `app/services/youtube_service.py`, `GET .../youtube/export` in
`app/api/youtube.py`. Frontend: `step7_youtube.html`/`.js` now show the correct
estimated-vs-measured label and a real "Download full package (.zip)" link, disabled with
an explanatory status line until both a completed video and a selected favorite thumbnail
exist. 13 new tests (7 `tests/test_youtube_service.py`, 4 new
`tests/test_youtube_export_api.py`, 2 new `tests/test_youtube_browser.py`), plus 4 existing
`tests/test_youtube_api.py` fixtures updated for `generate_package`'s new optional
`timestamps` parameter. 421/421 total tests pass, ruff clean, both JS files `node --check`
clean.

**Real bug caught by a browser test, not by inline review** (same pattern as the
`#generate-panel` bug from 1.9a): the first version of the frontend logic used
`state.package.chapters_estimated ? "Estimated…" : "Measured…"` — since the *existing*
`tests/test_youtube_browser.py` mock fixture never set `chapters_estimated` at all,
`undefined` is falsy in JavaScript, so the ternary took the "Measured" branch by default
even though nothing was actually measured. A live Playwright assertion on the rendered
text caught this immediately. Fixed by flipping the check to require an explicit
`=== false` for the "Measured" branch — the safe default (missing/falsy/`true`) is always
"Estimated," never a false claim of precision.

`tests/test_youtube_export_api.py` exercises the real end-to-end chain (real script → real
Edge TTS, network mocked → real AudioService mix → real VideoService render → real Pillow
thumbnail render, only its Gemini text call mocked → real zip assembly) rather than mocking
away the very features Sub-task 1.9b's export depends on — the same "exercise the real
local pipeline" philosophy as `tests/test_audio_service.py`/`tests/test_video_service.py`.

### Verification output

`venv\Scripts\python -m pytest tests/test_youtube_service.py tests/test_youtube_api.py tests/test_youtube_export_api.py tests/test_youtube_browser.py -q` (exit 0):
```
25 passed  (test_youtube_service.py)
26 passed  (test_youtube_api.py)
4 passed   (test_youtube_export_api.py)
8 passed   (test_youtube_browser.py)
```

`venv\Scripts\python -m pytest tests/ -q` (exit 0):
```
421 passed, 3 warnings in 157.32s (0:02:37)
```

`venv\Scripts\python -m ruff check app/ tests/ scripts/` (exit 0): `All checks passed!`

`node --check frontend/static/js/api.js` and `node --check frontend/static/js/step7_youtube.js`: both exit 0.

**This closes Task 1.9 entirely** (all acceptance criteria done: titles, description,
tags, chapters — measured when available — and the full `.zip` export).
