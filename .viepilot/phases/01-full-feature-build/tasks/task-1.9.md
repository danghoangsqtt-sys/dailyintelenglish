# Task 1.9: Step 7 — YouTube Package

## Meta
- **ID**: 1.9
- **Phase**: 1
- **Status**: planned
- **Priority**: medium
- **Assignee**: AI

## Paths
- `app/services/youtube_service.py`
- `app/api/youtube.py`
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step7_youtube.js`

## Acceptance Criteria
- [ ] Title options (3 variants: click-worthy, educational, SEO)
- [ ] Description with auto-generated timestamps/chapters
- [ ] Tag generator (comma-separated, max 500 chars)
- [ ] Full package download (.zip containing video, thumbnail, SRT, metadata.txt)

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
