# Task 1.9: Step 7 — YouTube Package

## Meta
- **ID**: 1.9
- **Phase**: 1
- **Status**: in_progress (Sub-task 1.9a done)
- **Priority**: medium
- **Assignee**: AI (Claude Code, acting as PM + Implementer)

## Paths
- `app/services/youtube_service.py`
- `app/api/youtube.py`
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step7_youtube.js`

## Acceptance Criteria
- [x] Title options (3 variants: click-worthy, educational, SEO) — Gemini-generated, `responseJsonSchema` validated
- [x] Description with auto-generated timestamps/chapters — description done; chapters are honestly ESTIMATED (no real audio exists yet), clearly labelled as such in API + UI
- [x] Tag generator (comma-separated, max 500 chars) — `YOUTUBE_TAGS_MAX_CHARS` enforced on the joined string
- [ ] Full package download (.zip containing video, thumbnail, SRT, metadata.txt) — deferred to Sub-task 1.9b, blocked on Task 1.7 (ffmpeg)

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
