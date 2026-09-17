# Changelog — Daily Intel English Studio

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [SemVer](https://semver.org/)

---

## [Unreleased]

### Changed
- Phase 4 Task 4.1, CEFR `news`-genre prompt tuning (2026-09-15, by Claude Code as PM +
  Implementer): added register-vs-complexity guidance to `prompts/script/news.txt`,
  targeting the exact 3 patterns Task 2.1b's real 18-sample review flagged as BORDERLINE
  (Future Simple drift at A2, B2-leaning idioms at B1, C1-bordering vocabulary at B2).
  Re-tested A2/B1/B2 × `news` with 3 real Gemini calls, re-reviewed against Task 2.1b's
  exact rubric. Honest result: **partial, mixed improvement, not a full fix** — one
  specific pattern (A2's indefinite-pronoun+modal) didn't recur but Future Simple usage
  persists; B1's exact flagged idiom ("a breath of fresh air") recurred verbatim; B2's
  idiom choice became more solidly B2-appropriate but grammar (Past Perfect Continuous)
  still borders C1. Not overclaimed as solved — consistent with tuning a probabilistic
  model. Single genre-scoped prompt file, no `app/`/`tests/` code touched. See
  `.viepilot/phases/04-post-beta-polish/tasks/task-4.1.md` for the full before/after
  evidence.
- Phase 4 Task 4.2a, UI Redesign Slice 2 — Learning page (2026-09-15, by Claude Code as
  PM + Implementer): `/step3` wrapped in the same 3-panel shell Task 2.4 built for
  Script (`frontend/pages/step3_learning.html`, `frontend/static/js/step3_learning.js`)
  — no timeline (Learning has no sequential-items concept). New read-only item inspector:
  click any vocabulary/idiom/grammar/quiz card to see its full detail; the quiz
  inspector always shows the correct answer, independent of the main list's show/hide
  toggle. Deliberately no per-item action buttons — no backend endpoint exists to
  regenerate a single item, only the whole pack. Existing inline-`contenteditable`-edit
  and coalesced-trailing-autosave behavior unchanged. New
  `tests/test_learning_shell_browser.py` (3 tests) — first browser coverage this page
  has ever had.
- Phase 4 Task 4.2b, UI Redesign Slice 2 — TTS Audio Studio page (2026-09-16,
  implemented by Codex, accepted by Claude Code as PM per the AR-06 contract — the
  first task fully delegated to Codex since Phase 4 opened): `/step4` wrapped in the
  same 3-panel shell, this time **with** a real 3-track timeline (Script — read-only
  reference; Voice — per-line synthesis state; Music — the selected background track).
  New read-only inspector shows the selected line with an honest session-only
  preview-state badge (Not previewed/Synthesizing/Preview ready — verified by an actual
  page-reload test that this never guesses persisted cache state), a real Listen action
  reusing the existing preview endpoint, and a real scroll-to-speaker-card "Voice
  settings" affordance — no new write path. Existing per-speaker autosave debounce and
  the sequential Generate-All request order verified unchanged. New
  `tests/test_tts_shell_browser.py` (5 tests). Went through 2 real PM review rounds
  before acceptance (see Fixed, below).
- Phase 4 Task 4.2c, UI Redesign Slice 2 — Video Studio page (2026-09-16, implemented
  by Codex, accepted by Claude Code as PM — the second task delegated end-to-end to
  Codex): `/step5` wrapped in the same 3-panel shell with a real 3-track timeline. This
  page never fetched the script's lines before, so a new `Api.getScript()` call site
  was added (an existing endpoint, not a new route), correlated by array index to the
  audio job's real per-line `timestamps`. Script track is a read-only reference; Voice
  track is honestly labeled "Synced" (every line's audio already exists by this stage,
  unlike TTS's in-progress states); Music track shows the real `background_music`
  filename or "No music selected". Read-only inspector shows real `M:SS – M:SS`
  measured timing — no playback button, a considered and disclosed scope cut (the
  seek/race complexity wasn't worth it for an optional feature). A `/script`-fetch
  failure degrades gracefully (logs, shows a timeline-only message) rather than
  blocking the core avatar/template/generate workflow. New
  `tests/test_video_shell_browser.py` (4 tests). Zero real defects found on PM review
  this round — `renderTimeline()` proactively cleared all 3 timeline lanes from the
  start, directly informed by Task 4.2b's Music-lane bug.
- Phase 4 Task 4.4, P0 navigation bug fixes (2026-09-16, implemented by Codex, accepted
  by Claude Code as PM per AR-06): the Config page (`/step1`) now fetches and prefills
  from an existing `project_id` in the URL and, for a `draft` project, saves via a new
  `Api.updateProject()` (`PUT /api/projects/{id}` — an endpoint that already existed
  but had no frontend caller until now) instead of always creating a new project; for
  any later status, every form control renders disabled with a clear
  configuration-is-locked banner rather than exposing a write path that would
  desynchronize already-generated content. No cascade/regenerate logic was invented.
  New `tests/test_step1_config_edit_browser.py` (5 tests), including a double-submit
  stress test and a status-parametrized read-only-lock check.
- Phase 4 Task 4.2d, UI Redesign Slice 2 — Thumbnail Generator page (2026-09-16,
  implemented by Codex, accepted by Claude Code as PM per AR-06 — the third task
  delegated end-to-end to Codex): `/step6` wrapped in the same 3-panel shell, no
  timeline (no sequential-items concept, same as Learning). Unlike every prior
  sub-task, this page already had a real, pre-existing write-path editor for the
  selected variant (headline + color palette, 400ms debounced autosave, trailing-save
  coalescing, 409 stale-revision conflict handling, `SaveIndicator`, `beforeunload`
  guard) — the inspector pane now hosts this real editor as-is rather than a new
  read-only view, since the write path already existed and wasn't invented. Stage
  hosts template selection and the variant grid; every existing element id was
  preserved unrenamed. New `tests/test_thumbnail_shell_browser.py` (2 tests). Zero
  real defects found on PM review — PM had flagged the relocated live preview's
  reduced width as an open risk during plan review and confirmed via its own
  screenshots (both themes) that it stays legible.
- Phase 4 Task 4.2e, UI Redesign Slice 2 — YouTube Package page (2026-09-16,
  implemented by Codex, accepted by Claude Code as PM per AR-06 — the fourth task
  delegated end-to-end to Codex): `/step7` wrapped in the same 3-panel shell, no
  timeline. This page has no per-item selection concept at all (titles, description,
  chapters, tags are all fully shown at once), so unlike every prior sub-task there is
  no natural "selected item" for the inspector — the inspector instead hosts the "Full
  Package Export" section, a real dynamic readiness panel (video + thumbnail present
  or not), while the generated content stays in the stage. Deliberately did not invent
  a click-to-inspect interaction for the 3 title-variant cards. New
  `tests/test_youtube_shell_browser.py` (2 tests). Zero real defects found on PM
  review.
- Phase 5 Task 5.1, Dashboard scale — client-side pagination (2026-09-17, implemented
  by Codex, accepted by Claude Code as PM per AR-06): the Dashboard's project grid now
  paginates at 24 cards per page instead of rendering every matching project at once
  (previously observed rendering 176 real project cards / 358 buttons in a single
  pass, producing a ~17,000px page). Client-side only — the data fetch already returns
  every project in one small payload and is unchanged; only DOM rendering is capped.
  Prev/Next controls with a "Page X of Y" indicator, hidden entirely when everything
  fits on one page. Filter and search changes reset to page 1. The page-clamp logic
  that prevents an emptied last page from staying visible lives centrally inside the
  render function itself, so deleting the last card on the last page correctly falls
  back a page with no special-case code needed. New
  `tests/test_dashboard_pagination_*` coverage (4 tests) using an isolated large
  fixture — the pre-existing shared project-list fixture and its 6 existing consuming
  tests were left untouched.
- Phase 5 Task 5.2, Timeline polish — proportional clip width + keyboard resizer
  (2026-09-17, implemented by Codex, accepted by Claude Code as PM per AR-06): timeline
  clip width on the Video and TTS pages now reflects real measured duration (16px per
  second, clamped 72-240px) instead of only auto-sizing to label text — a 3-second line
  stays at the 72px floor, a 7-second line reaches 112px. Script's timeline is
  unaffected on purpose: it has no timing data at any point in the pipeline, and this
  task does not fabricate one. Missing, invalid, zero, or negative durations keep the
  existing auto-width behavior rather than guessing. TTS also captures the audio job
  from a first "Generate All" call (not just from revisiting an already-completed
  project), so widths update immediately without a reload. The shared workspace
  shell's horizontal timeline resizer now supports keyboard resizing
  (`ArrowUp`/`ArrowDown`, `Shift` for a bigger step), matching the sidebar/inspector
  resizers' existing keyboard support — fixed once, applies to every page with a
  timeline. New/extended browser tests use real measured bounding-box widths rather
  than checking for a style attribute's presence.
- Phase 5 Task 5.3, Small polish batch (2026-09-17, implemented by Codex, accepted by
  Claude Code as PM per AR-06 — the final Phase 5 task): Learning's vocabulary/idiom/
  grammar/quiz cards are now keyboard-accessible (`role="button"`, `tabindex="0"`,
  `Enter`/`Space` activation isolated from nested inline-edit controls) instead of
  click-only. Learning's inspector now defaults to the active tab's first item
  whenever nothing is selected — on first load, first generate, and after switching
  tabs — rather than starting empty, while never overriding a real existing
  selection. Video's "Speaker avatars (optional)" section (a disclosed, not-yet-
  functional preview of a future feature) now collapses by default using a native
  `<details>`/`<summary>` element, reusing the same pattern already used for Script's
  language notes — no custom JS toggle needed. New/extended browser tests include a
  real keyboard walkthrough and a direct assertion that `Space`'s page-scroll default
  is actually prevented.

### Fixed
- Found via a Codex read-only UI audit (2026-09-16), independently confirmed by PM:
  Dashboard's "Continue" button silently did nothing for `audio_generated`/
  `video_generated`/`complete` project statuses — only `draft`/`script_generated` had
  ever been wired up (`frontend/static/js/dashboard.js`). Fixed with a single
  `STATUS_TO_STEP` map covering all 5 statuses, resuming each to the step that produced
  it (`audio_generated`→`/step4`, `video_generated`→`/step5`, `complete`→`/step7`). See
  Task 4.4, above.
- Same audit: the Config page (`/step1`) ignored an existing `project_id` in the URL
  and always created a brand-new project on submit — since Config is a real, reachable
  StepNav link from every other step, a user revisiting it mid-workflow could silently
  spawn a duplicate project. See Task 4.4, above, for the fix.
- `tests/test_step_nav_browser.py` assumed only the Script page (`/step2`) used the new
  3-panel shell layout; fixed its branching to also cover Learning (`/step3`), and fixed
  the real root cause on the implementation side — `step3_learning.js`'s
  `StepNav.render()` call was missing `variant: "workflow"`.
- `/vp-audit` pass after Task 4.2a (2026-09-15): `README.md` had no mention of Phase 4
  despite Tasks 4.1/4.2a already shipping — added a summary section matching the
  existing Phase 2/3 format. `step3_learning.js`'s `commitField()` never called
  `renderInspector()`, so editing the currently-selected item's field left the inspector
  showing stale text until re-selected — fixed, and verified as a real bug via
  revert-and-confirm-failure (Script's equivalent `commit()` already handles this
  correctly, confirming it was a Learning-specific oversight, not a systemic pattern).
- Task 4.2b PM review round 1: Codex correctly flagged, before writing any other code,
  that `tests/test_step_nav_browser.py`'s shell-layout branch would also break for
  `/step4` (`current_step == 4`) — same class of issue Task 4.2a hit — and reported it
  rather than touching a file outside its assigned scope; PM pre-authorized the exact
  one-line fix (`(2, 3)` → `(2, 3, 4)`).
- Task 4.2b PM review round 2: PM's own independent screenshot (not the test suite, not
  the Implementer's described screenshots) caught a real bug —
  `step4_tts.js`'s `renderTimeline()` cleared the Script and Voice timeline lanes on
  every re-render but never the Music lane, so it accumulated a duplicate stale clip on
  every selection/preview/music-change event. Reproduced live (2 duplicate "No music
  selected" badges after a single click). Sent back to Codex with the exact fix
  (`musicLane.replaceChildren()`, matching the pattern already used for the other two
  lanes) and a regression-test assertion; re-verified independently, including a
  disposable 5-interaction stress test confirming exactly 1 clip survives repeated
  re-renders.
- Task 4.2e plan review: relocating YouTube Package's "Full Package Export" section
  into the always-visible inspector would have surfaced a previously-invisible,
  misleading static placeholder ("Checking export readiness…" — inert HTML text that
  `render()` never updates before a package exists, harmlessly hidden today because
  the whole section was nested inside `#content-wrap`). Fixed with an honest static
  default ("Generate the YouTube package to check export readiness."); the existing
  `renderExportStatus()` still overwrites it correctly once a package loads or is
  generated — no new JS logic.

## [1.0.0-beta] - 2026-09-15

All 3 planned phases (Full Feature Build, Testing & Polish, Review & Documentation)
complete — see `.viepilot/TRACKER.md` for the full evidence trail. 533/533 tests pass.

### Added
- Initial project crystallization from brainstorm session 2026-09-10
- Architecture design: FastAPI + OmniVoice + Gemini + ffmpeg stack
- 7-step production pipeline design
- SQLite database schema
- FastAPI skeleton (CORS, lifespan, routers), SQLite init via aiosqlite, dark-mode dashboard UI
- `ProjectService` full CRUD (create/get/list/update/delete) with validated Pydantic models (`ScriptConfig`, `SpeakerConfig`, `ProjectUpdate`) and `POST/GET/PUT/DELETE /api/projects[/{id}]`
- Forward-only project state machine: `draft → script_generated → audio_generated → video_generated → complete` — no skipping or reverting
- Atomic `num_speakers`/`speakers` updates — the two can only change together, keeping the `speakers` table and the `num_speakers` column consistent
- `config_json` is recomputed from the merged project state on every update, not only at creation
- Global `RequestValidationError` handler so Pydantic 422s use the same `{success, data, error, meta}` envelope as every other response
- All settings namespaced under a `DIE_` env-var prefix, so generic system env vars (e.g. bare `DEBUG`) can no longer crash startup or leak into config
- `scripts/check_dependencies.py` now checks the configured ffmpeg path and Gemini API key the same way the app itself resolves them (`settings.FFMPEG_PATH`, `settings.GEMINI_API_KEY`), plus a new OmniVoice model directory check
- `ruff` added as the lint gate; 30 automated tests (`pytest`) covering project CRUD, validation, and dependency-check logic
- Step 1 — Script Config wizard (`/step1`): full form (name, topic, CEFR, duration presets/custom, num_speakers, 10 genres, 10 accents, 6 language-feature toggles, dynamic speaker cards), submitting via `Api.createProject()` with a loading state, double-submit lock, and a friendly-only error banner (raw API errors are logged to console, never shown to the user)
- Dashboard's "New Project" button now opens `/step1` instead of a placeholder alert
- A minimal Step 2 entry-point placeholder (`/step2`) that carries the created `project_id`/name — the real Step 2 UI ships in Task 1.4
- Script prompt templates (`prompts/script/`): 1 Jinja2 base + 10 genre blocks + 6 CEFR blocks, loaded async via `app/core/prompt_loader.py`
- `ScriptService` (`app/services/script_service.py`): `generate_script()`/`regenerate_line()` via the Gemini REST API (`httpx.AsyncClient`, `responseMimeType=application/json`, exponential backoff 1s→2s→4s on HTTP 429 only), plus persistence (`save_script`/`get_script`/`get_script_line`/`update_script_line`)
- Step 2 — Script Generation UI (`/step2`, `step2_script.html`/`.js`) replacing the Task 1.3 placeholder: generate, per-line regenerate, click-to-edit with autosave, "Regenerate All", and `GET /api/projects/{id}/script` so a reload/revisit never loses the script
- `POST .../script/generate` and `PUT .../script` auto-advance a project from `draft` to `script_generated`
- Step 3 — Learning Content Wizard & Service (Task 1.5):
  - `LearningContentService` (`app/services/learning_service.py`): generates structured vocabulary (with IPA, part of speech, bilingual definitions, examples), idioms, grammar points, and comprehension quiz via Gemini REST API (`gemini-3.8-flash`) with strict JSON schema enforcement (`responseJsonSchema`) and retry/backoff on 429
  - Dedicated SQLite table `learning_contents` (`app/db/migrations/002_learning_content.sql`) with UPSERT and foreign key cascade to `projects(id)`
  - REST endpoints: `POST /api/projects/{id}/learning/generate`, `GET /api/projects/{id}/learning`, and `PUT /api/projects/{id}/learning`
  - Step 3 UI (`frontend/pages/step3_learning.html`, `step3_learning.js`): 4-tab interface (Vocabulary, Idioms, Grammar, Quiz with answer reveal), inline editing, coalesced trailing autosave, and "Regenerate Pack" confirmation modal
  - Step 4 placeholder entry point (`frontend/pages/step4_tts_placeholder.html`, `GET /step4`)
- `ENH-002`: Architecture diagram sidecars (`.viepilot/architecture/data-flow.mermaid`, `module-dependencies.mermaid`) and Diagram source references in `ARCHITECTURE.md`
- `ENH-003`: Gemini Implementer Delivery Protocol and contract (`docs/GEMINI_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`, updated `CLAUDE_CODE_PROMPT.md`)
- Task 2.4 — UI Redesign Slice 1 (Dashboard + Script workspace): Dashboard rebuilt as a light, high-contrast project launcher (hero, filter/search toolbar, light project cards) with all existing list/filter/search/delete/new-project behavior unchanged; Step 2 rebuilt as a CapCut-style Script workspace via new `frontend/static/js/shell.js` (`WorkspaceShell`) — resizable/collapsible sidebar, central script stage (original inline editor untouched), a selected-line inspector (speaker/text/language notes, Listen via the existing TTS preview endpoint, Regenerate), and a three-track Script/Voice/Music timeline; shared CSS tokens flipped to light-by-default with dark values moved under `[data-theme="dark"]`

### Changed
- `theme.js`'s stored-preference fallback changed from `"dark"` to `"light"` (Task 2.4) — first-visit default is now light; explicit user choice via `#theme-toggle` still persists and overrides

### Fixed
- Step 2 autosave now resyncs script-line ids from the `PUT .../script` response (the save always reissues fresh ids) and serializes overlapping autosaves into one coalesced trailing save instead of firing them concurrently; Regenerate is disabled for the full duration of an in-flight save
- Step 2 no longer shows the "Generate Script" panel when loading an existing script fails — previously this could invite overwriting a script that actually exists but just failed to load
- `GEMINI_MODEL` moved off the shut-down `gemini-2.0-flash` to `gemini-3.8-flash` (Google's current default Flash model)
- Every write to the shared `aiosqlite` connection (create/update/delete project, script generate/regenerate/save) and every read from it (list/get project, `GET .../script`, and the pre-read steps of generate/regenerate/save) now serializes on one connection-wide lock (`app/api/projects.py::_write_transaction` / `_read_transaction`) — closes a HIGH-severity bug where an unrelated concurrent request could interleave into another request's uncommitted transaction and be wiped out by its rollback (dirty/phantom reads and writes). The lock is never held across a Gemini call. `db.commit()` now runs inside the `try` so a commit failure also triggers a rollback
- `BUG-001`: Fixed JSON syntax error (trailing comma) in `.viepilot/HANDOFF.json`, restored phase structure (`.viepilot/phases/01-full-feature-build/`)
- `BUG-002`: Reconciled counters across `TRACKER.md` (14/29 tasks, Day 2/21), `ROADMAP.md` (checked Task 1.5 with commit hashes), and `HANDOFF.json`
- `BUG-003`: Re-established 10 phase task cards (`tasks/task-1.1.md` through `task-1.10.md`), verified with `vp-tools phase-info 1` and `vp-tools progress`
- `BUG-004`: Fixed double-encoded UTF-8 in `README.md`, updated documentation to use `DIE_GEMINI_API_KEY`, synchronized `database-schema.sql` with migration 002, removed stale Gemini 2.0 and JSON-sidecar references
- `BUG-005`: Resolved HTTP 500 on explicit null fields in `PUT /api/projects/{id}/learning` by adding `@model_validator(mode="before")` on `LearningPackUpdate` to reject nulls with HTTP 422, reinforced with service-level validation
- `BUG-006`: Resolved empty/whitespace-only project and speaker names by adding string validators (`min_length=1`, whitespace stripping) to Pydantic models and service layer
- `BUG-007`: Enforced strict Gemini structured-output schema on all AI generation calls (`ScriptService`, `LearningContentService`), added dedicated `regenerate_line.txt` template and `render_regenerate_line_prompt`; confirmed structural determinism is achieved via schema (see `BUG-011`), sampling `temperature` intentionally left unset so "Regenerate" keeps returning varied content
- `BUG-008`: Fixed race conditions and data loss on rapid Step navigation by adding dirty state checks, save awaiting in `handleNextStep`, UI action locking, and `beforeunload` warning in Step 2 and Step 3
- `BUG-009`: Restored PM-only acceptance authority — all Sprint 1.5R requests reverted to `ready_for_review` pending explicit PM sign-off (`AR-06`); reconciled test counts (223) and `_write_lock` terminology across `TRACKER.md`/`PHASE-STATE.md`/`HANDOFF.json`/`ROADMAP.md`/`task-1.5.md`
- `BUG-010`: Fixed `README.md` Task 1.7–1.10 numbering to match `ROADMAP.md`/`SPEC.md` (1.7 Video Studio, 1.8 Thumbnail Generator, 1.9 YouTube Package, 1.10 Music Library), confirmed `.viepilot/ARCHITECTURE.md` and `docs/walkthrough-sprint-1.5r.md` are committed and `git diff --check` is clean
- `BUG-011`: Switched `ScriptService`/`LearningContentService` from the unsupported `responseSchema` field to Gemini's `responseJsonSchema` field (the correct carrier for Pydantic's `$defs`/`$ref` output), removed the silent schema-less fallback on `TypeError`, added wire-payload regression tests
- `BUG-012`: Added explicit `saveStatus` state machine (`saved`/`dirty`/`saving`/`failed`) to Step 2/Step 3 so navigation only proceeds after a confirmed save, with a real `/step4` placeholder route and a Playwright regression suite (`tests/test_ui_async_browser.py`) for save/failure/retry/rapid-edit races
- Task 1.2 closed: Dashboard automated browser tests (`tests/test_dashboard_browser.py`, 7 Playwright tests) covering listing/status badges, filter, search, empty state, "New Project" → `/step1` navigation, "Continue" → `/step2?project_id=...` navigation, and delete-after-confirm
- Task 1.6 Sub-task 1.6a (Edge-TTS-first): `TTSService` (`app/services/tts_service.py`) synthesizes script lines via Edge TTS (`EDGE_TTS_VOICE_MAP` covering all 10 accents x 3 genders, voice ids verified live), with an OmniVoice path guarded by `asyncio.Semaphore(MAX_CONCURRENT_TTS)` that honestly falls back to Edge TTS since no local model weights exist yet; `POST /api/projects/{id}/tts/preview` and `GET /api/projects/{id}/tts/cache/{line_id}.mp3` routes; retry-once-on-empty-audio guard added after live testing surfaced a real transient Edge TTS failure. AudioService and the TTS Studio UI are deferred to 1.6b/1.6c pending `ffmpeg`
- Task 1.10 Sub-task 1.10a (ffmpeg-independent Music Library, by Codex — second AI Implementer): `/music` page for uploading, listing, previewing, and deleting background tracks. `app/api/music.py` adds `POST /api/music` (multipart upload, 50MB limit, WAV/MP3 magic-byte validation, atomic no-clobber duplicate naming via `os.link`) and `GET /api/music/{filename}` (safe streaming preview) alongside the existing list/delete routes; all four routes share one path-traversal-safe filename validator. Waveform visualization, volume leveling, and Step 4/5 background-track selection are deferred to Sub-task 1.10b pending `ffmpeg` and the `audioop-lts` backport (`pydub` doesn't import on Python 3.14 without it)
- Task 1.8 Sub-task 1.8a (Thumbnail Generator backend, by Codex): `ThumbnailService` (`app/services/thumbnail_service.py`) generates 3-5 distinct headline/color-palette suggestions via Gemini (`responseJsonSchema`, exact-count + duplicate-rejection Pydantic validation, no vision call needed), renders them onto one of 5 deterministic Pillow templates (`minimal_clean`, `gradient_bold`, `modern_split`, `dynamic_wave`, `podcast_classic`) using Pillow's embedded scalable default font (`ImageFont.load_default(size=...)`, no system/hardcoded font path), and exports PNG+JPEG at both 1280x720 and 720x1280. `POST /api/projects/{id}/thumbnails/generate`, `GET .../thumbnails`, `GET /api/thumbnails/templates`, and a safe `GET .../thumbnails/{id}/{aspect}.{format}` content route (never exposes local paths). Regeneration stages the full new render set before the DB swap and only removes superseded files after a successful commit. The interactive manual editor UI is deferred to Sub-task 1.8b
- Task 1.8 Sub-task 1.8b (Thumbnail Generator interactive UI, by Codex — **closes Task 1.8**): `/step6` page with a template gallery, generate/regenerate workflow (confirm-gated when replacing an existing batch), exclusive favorite selection (`PUT .../thumbnails/{id}/favorite`, one atomic SQL `UPDATE ... CASE WHEN`), and a manual headline/color editor (`PATCH .../thumbnails/{id}`) with true optimistic concurrency — a SQL-level compare-and-swap keyed on the row's current render revision, rejecting stale edits with a new `ConflictError` (409) instead of silently clobbering a newer change. Asset URLs now carry a `?revision=` cache-busting token so a stable content URL never serves a stale cached image after an edit. The editor's `saved`/`dirty`/`saving`/`failed` state machine (debounced auto-save, single in-flight + trailing-save coalescing, `beforeunload` guard, friendly 409 recovery) matches the established Step 2/3 pattern
- Task 1.9 Sub-task 1.9a (YouTube Package text generation, by Claude Code acting as PM + Implementer): `YouTubeService.generate_package()` produces 3 Gemini-generated title options (`click_worthy`/`educational`/`seo`), a description, 5-15 tags (joined length capped at `YOUTUBE_TAGS_MAX_CHARS`), and chapter markers — honestly **estimated** from cumulative script word count at a fixed reading speed rather than measured, since no real audio exists yet (Task 1.7/AudioService are blocked on `ffmpeg`); both the API response and the `/step7` UI label these as estimates. New migration `003_youtube_package.sql` drops and recreates the never-used `youtube_packages` table (same precedent as `002_learning_content.sql`) to add `title_options_json`. `/step7` is a read-only display page (copy-to-clipboard per section, confirm-gated Regenerate) with an explicit note that the full `.zip` export (video+thumbnail+SRT+metadata.txt) awaits Task 1.7, rather than a dead download button. Two real bugs were caught and fixed by the test suite before landing: tags lost their spacing on a DB round-trip, and `#generate-panel`'s own `display: grid` rule was silently overriding the `hidden` attribute (only caught by a genuine Playwright visibility assertion, not a unit test)
- Task 1.6 Sub-task 1.6b (AudioService, by Claude Code as PM + Implementer, ffmpeg/OmniVoice now installed): `AudioService.mix_project()` (`app/services/audio_service.py`) concatenates a project's synthesized lines with speaker-aware silence gaps (300ms same-speaker / 500ms different), normalizes integrated loudness to -16 LUFS via real ITU-R BS.1770 measurement (`pyloudnorm`, not a dBFS approximation), overlays optional background music at a flat ducking ceiling, and exports MP3(192k)+WAV(44100Hz/16-bit) plus real measured per-line timestamps to `data/audio/{project_id}/`. New `POST/GET /api/projects/{id}/audio/{generate,status,download}` routes (`/status` is a plain polling GET, not SSE — documented deviation, matches every other `*/generate` route in this codebase). Also closes Task 1.10's background-music/loudness-leveling item, deferred there "alongside AudioService"
- Task 1.6 Sub-task 1.6c (TTS Audio Studio UI — **closes Task 1.6**'s sub-task split): `/step4` (`frontend/pages/step4_tts.html`/`.js`, replacing the Task 1.5 placeholder) with a per-speaker voice-assignment panel (engine + speed/pitch/volume, autosaved), per-line preview playback, a background-music selector, sequential "Generate All" (synthesizes every line, then mixes), and MP3/WAV download. Added a new narrow `PATCH /api/projects/{id}/speakers/{speaker_id}` route specifically because the existing full-replace `PUT /{id}` (`speakers`) path deletes and reinserts every speaker row with new ids — harmless before a script exists, but would silently cascade-delete every `script_lines` row once one does, since `script_lines.speaker_id` has `ON DELETE CASCADE`
- Task 1.1 closed: `scripts/check_dependencies.py` now reports all-GREEN (Python, ffmpeg, GPU, Gemini key, OmniVoice model, data dirs)
- Task 1.7 Sub-task 1.7a (VideoService background+subtitle backend, by Claude Code as PM + Implementer): `VideoService.generate_video()` renders a project's completed audio mix (Task 1.6) into an MP4 with burned-in subtitles (ffmpeg `subtitles`/libass filter) over one of 3 fixed pre-rendered background templates (`scripts/generate_video_background_assets.py` → `frontend/static/video_backgrounds/`, same deterministic-asset precedent as thumbnail templates). SRT cues use AudioService's real *measured* per-line timestamps (start/end seconds + actual dialogue text + speaker label), extended with a small backward-compatible `text` field. `GET /api/video/templates`, `POST/GET /api/projects/{id}/video/{generate,status,download}`. Level 3 (LivePortrait avatar lip-sync) is deliberately deferred: no speaker has an avatar image and no upload/generation feature exists yet — the same class of blocker as OmniVoice's `ref_audio` requirement, a real user decision rather than something to fabricate
- Task 1.9 Sub-task 1.9b (full `.zip` export + measured chapters — **closes Task 1.9**): `real_chapters_from_timestamps()` replaces the word-count estimate with AudioService's real measured timestamps whenever a project's audio exists (additive migration `004_youtube_chapters_measured.sql`, `chapters_estimated` flag says which); new `GET /api/projects/{id}/youtube/export` streams an in-memory `.zip` (video.mp4 + subtitles.srt + the favorite thumbnail.png + metadata.txt) once video and a selected thumbnail both exist, naming exactly which prerequisite is missing otherwise. `/step7` UI shows the correct estimated-vs-measured label and a real download link. Caught a real bug via a live browser test: the frontend defaulted to claiming "Measured" whenever `chapters_estimated` was simply `undefined` — fixed to require an explicit `=== false`
- Task 1.7 Sub-task 1.7b (Video Studio UI — **closes Task 1.7**'s sub-task split): `/step5` (`frontend/pages/step5_video.html`/`step5_video.js`) with a background-template selector (3 fixed templates only), synchronous Generate, `<video>` preview, and MP4/SRT downloads. No avatar/lips-sync controls — that backend path (Level 3 LivePortrait) doesn't exist and is blocked on a real user decision about avatar image sourcing. `/step4` gained its first pipeline-navigation button ("Next: Video Studio →")
- Task 1.10 Sub-task 1.10c (waveform visualization — **closes Task 1.10, completing all 10 Phase 1 major tasks**): new `frontend/static/js/waveform.js` decodes each Music Library track via the Web Audio API and renders a real canvas waveform with played/unplayed tinting and click-to-seek, wired into `/music`'s track cards
- Task 1.9 Sub-task 1.9c (full transcript + Learning Content in the YouTube export, by Codex — **closes Task 1.9 and the one gap found in Phase 1's close-out review**): the `.zip` export gains a 5th file, `transcript_and_vocabulary.txt`, with the full script transcript (speaker names resolved) plus vocabulary/idioms/grammar/comprehension questions when Learning Content has been generated for the project; a project with none still exports successfully with a plain notice — Learning Content was deliberately never made a hard export prerequisite. `metadata.txt` unchanged
- Task 2.3 (Phase 2, "UX Polish" — step progress indicator + breadcrumb navigation, by Codex): new `frontend/static/js/step_nav.js` (`StepNav.render()`, a pure synchronous DOM component) mounted identically on all 7 step pages (`/step1`-`/step7`), showing "Step X of 7" plus 7 clickable pills that jump directly to any step while preserving `project_id`; a missing `project_id` degrades to clean bare URLs rather than a broken link
- Decision, 2026-09-13 (user, via analysis presented by Claude Code as PM): Edge TTS becomes the sole official TTS engine — real OmniVoice integration will not be pursued. The actual k2-fsa/OmniVoice API turned out to be zero-shot voice cloning requiring a reference audio sample, not the natural-language "voice design" the original ROADMAP envisioned, and raises consent/rights questions the project has no way to resolve on its own. `SpeakerConfig.tts_engine` now defaults to `"edge_tts"`; Step 4's per-speaker engine picker (a dead choice between one working and one always-falls-back engine) was removed
- Task 1.7c (Phase 1, Video Studio groundwork — speaker avatar upload, by Claude Code as PM + Implementer): per the same 2026-09-13 decision round, the user chose to build only avatar image upload now (LivePortrait lip-sync integration itself stays deferred). New `app/services/avatar_service.py` validates (magic-byte-checked PNG/JPEG, 8MB cap) and stores one mutable avatar file per speaker at `data/avatars/{project_id}/{speaker_id}.{ext}`, served through a safe path-contained route (never a raw filesystem path in any API response — `project_service.get_project` now maps a stored path to a served URL). New `POST`/`GET`/`DELETE /api/projects/{id}/speakers/{id}/avatar` routes; `/step5` gained a small per-speaker avatar upload/preview/remove section, not wired into video generation. Caught and fixed a real rendering bug via a live screenshot: this app's stylesheet has no `[hidden]` rule, so setting `.hidden` on a `.btn`-classed Remove button left it visibly showing regardless — fixed by only appending the button to the DOM when an avatar exists
- Task 2.3b (Phase 2, "UX Polish" — keyboard shortcuts, by Claude Code as PM + Implementer via `/vp-auto`): audited the remaining 5 ROADMAP "UX Polish" items first and found most already substantially satisfied by existing patterns (friendly-only error banners, contextual empty states, native `confirm()` dialogs and existing inline-edit revert handlers already covering "Esc to cancel") — the one real gap was `Ctrl+Enter` to generate. New `frontend/static/js/keyboard_shortcuts.js` (`KeyboardShortcuts.init({ primaryButtonId })`, same shared-component pattern as `StepNav`) mounted on all 7 step pages, one line + one init call per page; triggers each page's real primary button only when it's genuinely visible and not disabled, so it can never fire "Generate" behind a hidden panel or a disabled button. Caught and fixed a real bug in the new module before shipping (a top-level `const` doesn't attach to `window` in a classic script — fixed to match `StepNav`'s explicit `window.X = ...` assignment) plus two test-fixture mistakes while writing the Playwright suite (a wrong 404-vs-`data:null` assumption about the YouTube package "not generated yet" contract, and a missing `/tts/preview` mock that let a test silently hit the real backend)
- Task 2.3c (Phase 2, "UX Polish" — error toasts, by Claude Code as PM + Implementer via `/vp-auto`): re-audited the two "substantially satisfied" items from Task 2.3b with a real page-by-page check. `music_library.js` genuinely already covers friendly errors (different element ids than the step-page convention, which a naive grep had missed). The Dashboard (`/`) had two real gaps: a failed project load silently rendered "No projects yet." — indistinguishable from a genuinely empty account — and a failed delete used a raw `alert(err.message)`, the last remaining spot in the app showing raw backend text to a user. Both fixed with the same `#error-banner` pattern already used everywhere else, plus a new `loadFailed` flag so a failed load can never look like an empty account. "Empty states" needed no code once checked — every page that can be meaningfully empty already handles it. Caught a real test-authoring bug while writing the new tests: a Playwright dialog handler returning a tuple hid its `dialog.accept()` coroutine from the fire-and-forget scheduling Playwright applies when a handler returns a coroutine directly, deadlocking a `confirm()` dialog
- Task 2.3d (Phase 2, "UX Polish" — responsive layout, by Claude Code as PM + Implementer via `/vp-auto`): ran a real Playwright audit before writing any plan — all 9 pages already have zero horizontal overflow at a 1024px viewport, thanks to this app's consistent `repeat(auto-fit, minmax(...))` grid pattern (self-reflowing by construction) plus `/step6`'s existing `@media (max-width: 1180px)` rule, which already covers 1024px. No production code change needed. New permanent `tests/test_responsive_layout_browser.py` (9 tests, one per page, realistic mocked data reused from each page's own existing test fixtures) pins the finding as a durable regression check. This closes 6 of ROADMAP.md's 7 "UX Polish" items — only "auto-save indicator" remains unassigned
- Task 2.3e (Phase 2, "UX Polish" — auto-save indicator, by Claude Code as PM + Implementer via `/vp-auto`) — **closes Task 2.3 entirely, all 7 ROADMAP "UX Polish" items now resolved**: new shared `frontend/static/js/save_indicator.js` (`SaveIndicator.mount()`, same pattern as `StepNav`/`KeyboardShortcuts`) mounted in the header of `/step2`, `/step3`, `/step6` — the 3 pages with an existing page-level `saved`/`dirty`/`saving`/`failed` state machine — as a purely additive change alongside each page's existing inline `#save-status` element, wired via one new line inside each page's existing central setter function. `/step4` (per-speaker-field autosave, no single "document" concept) and `/step1`/`/step5`/`/step7`/Dashboard/Music Library (no page-level autosave concept) intentionally excluded, with documented reasoning per page. 2 new Playwright tests; the existing autosave-race suite (`tests/test_ui_async_browser.py`) re-run unmodified and still passes, proving the existing inline indicator behavior is untouched
- Task 2.2 (Phase 2, "Bug Fixes & Performance" — blocking-calls fix, by Claude Code as PM + Implementer via `/vp-auto`): audited all 4 ROADMAP items before scoping. A research-agent grep + direct file review found 4 real event-loop-blocking gaps (not the ~25 already-correct `asyncio.to_thread` usages elsewhere): `video_service.generate_video()`'s background-check/mkdir/SRT-write, `tts_service.synthesize_line()`'s model-exists-check/mkdir/audio-write (a per-line hot path during "Generate All"), `audio_service.mix_project()`'s background-music existence check, and `app/api/tts.py`'s `list_engines()` (model-exists check + `shutil.which("piper")`, the latter found independently while reading the file). All 4 wrapped in `asyncio.to_thread`; 55 pre-existing tests across the touched files pass completely unmodified, proving zero behavior change. "Fix Gemini retry logic for 429" turned out to already be done during Phase 1 — closed via audit, no code needed. "Optimize OmniVoice batch" is moot post-decision. "Add progress cancellation (stop mid-generation)" was explicitly left open, not closed: audited the architecture and found every generation route is a synchronous request/response call with no background-job or cancellation mechanism anywhere — building real cancellation needs an architectural change, not a quick fix, so it stays a separate future task
- Deep security/correctness audit (Phase 2, by Claude Code as PM, 2026-09-14, dispatched a
  research agent then independently re-verified every finding against the real code before
  fixing anything): 4 real bugs fixed, 1 deliberately deferred as a documented known issue.
  **Path traversal / arbitrary file read (HIGH)**: `POST /api/projects/{id}/audio/generate`'s
  `background_music` field flowed straight into `settings.DATA_DIR / "music_library" /
  background_music_filename` with zero validation — confirmed live with pathlib that an
  absolute path (e.g. `C:/Windows/win.ini`) silently discards the base directory entirely
  (documented pathlib join semantics), and `../`-style relative paths escape it just as
  easily; the file, if it decoded as audio, would get mixed into the downloadable output.
  Fixed with the same character-level filename guard already used by `app/api/music.py`
  (new `audio_service._validate_music_filename`), 6 new parametrized regression tests.
  **Blocking event-loop call (MEDIUM)**: `GET .../youtube/export` called the synchronous
  `youtube_service.build_export_zip()` (real multi-MB file reads + zipfile DEFLATE
  compression) directly on the event loop — same bug class as Task 2.2's 4 fixes, missed
  because this route was added separately; wrapped in `asyncio.to_thread`.
  **Orphaned files on project deletion (MEDIUM)**: `delete_project` only ever removed DB
  rows (FK cascade) — the 5 per-project data directories (avatars/audio/video/thumbnails/
  tts_cache) were never cleaned up, an unbounded storage leak with no reaper anywhere. New
  `project_service.cleanup_project_artifacts()`, called from the DELETE route only after
  the DB transaction durably commits (best-effort, never inside the same transaction).
  **Inconsistent file-serving safety (LOW)**: `tts_service.get_cached_audio_path` was the
  only cached-file resolver in the app that skipped the containment/existence check its
  siblings (`avatar_service`, `thumbnail_service`) already use — a moved/deleted cache file
  surfaced as an unhandled 500 instead of a clean 404; brought in line.
  **Deliberately NOT fixed, documented instead**: a narrow race where a project deleted
  while its own audio/video/YouTube-package generation is mid-flight can hit a raw
  `IntegrityError` (500) instead of a clean 404 when the job-save write lands after the
  delete — real but requires the single local user to run two conflicting actions on the
  same project simultaneously from separate sessions; fixing it cleanly touches 3 files ×
  2 write blocks each, deferred rather than rushed (see TRACKER.md Known Issues).
  16 new tests across the touched files, full suite green.
- Gemini reliability (Phase 2, by Claude Code as PM + Implementer, 2026-09-14): all four Gemini-calling services (`script_service`, `learning_service`, `thumbnail_service`, `youtube_service`) now retry on HTTP 503 ("model temporarily overloaded") in addition to 429, and fall back through a new `GEMINI_MODEL_FALLBACKS` chain (`gemini-3.8-flash` → `gemini-3.7-flash` → `gemini-3.6-flash` → `gemini-3.5-flash` → `gemini-3.5-flash-lite` → `gemini-3.1-flash-lite`) once a model's own retries are exhausted, instead of failing outright. `gemini-3.1-flash-lite` was added last at the user's explicit request; PM disclosed beforehand that it already has an announced 2027-05-07 shutdown date and that Google's own recommended replacement for it is `gemini-3.5-flash-lite` (already earlier in the chain) — user chose to keep it anyway as one more quota bucket. Real Google AI Studio usage data showed each Flash model version tracks its own separate RPM/RPD quota bucket on this account (3.8 Flash was at 26/20 RPD and 8/5 RPM while 3.7/3.6 sat completely unused at 0/20 and 0/5) — confirmed live via `models.list` that every model ID in the chain is real, GA (no `-preview` suffix), and callable before wiring it in; deliberately excluded the only available Pro-tier model (`gemini-3.1-pro-preview`) since it carries the same preview-instability risk that forced the earlier `gemini-2.0-flash` migration, and the user confirmed the goal here is spreading quota load, not a per-difficulty quality tier. Also corrected `GEMINI_RATE_LIMIT_RPM` from an unverified `15` to the account's real measured `5`, fixing `scripts/generate_cefr_review_samples.py`'s inter-request throttle (4.1s → 12.1s). Live-verified end-to-end against the real API while 3.8 Flash was still quota-exhausted: 3.8 failed 429 three times, fell back to 3.7, which failed 503 twice then succeeded on its third attempt — a real generation that would have failed outright before this fix. 12 new/updated tests across the four services' test files (503-retry, model-fallback-after-exhaustion, full-chain-exhaustion) plus the CEFR sample CLI's throttle test, 92/92 passing on the affected files
- Task 2.5 (2026-09-14, by Claude Code as PM + Implementer): fixed all 3 real findings from Task 2.1c's audio/video QA pass. `audio_service._mix_project_sync` now normalizes the final mixed signal (voice + any ducked background music) once, after the overlay, instead of only the pre-music voice stem — background-music mixes previously drifted to -17.12 LUFS (1.12dB outside the declared ±1dB tolerance), now land within it (per EBU R128 guidance that loudness normalization must target the complete final mix). New 9:16 (vertical) video output: `_render_vertical_sync` runs a second ffmpeg pass (the real blurred-background-pad convention used by YouTube Shorts/TikTok/Reels tooling) over the existing 16:9 render, exposed via a new `aspect_ratio` request field (default `"16:9"`, byte-for-byte unchanged), a new `video_jobs.mp4_path_vertical` column, a new download format, and a Step 5 UI toggle — real `ffprobe` confirms the output is genuinely 720×1280. Step 1's Scottish accent option now discloses via a tooltip that it shares British's Edge TTS voice (confirmed live against the real `edge-tts` package that no distinct Scottish voice exists upstream — not fixable in code without a different TTS provider). Also fixed 2 more real bugs found while verifying: the `.hidden`-on-`.btn` CSS trap already flagged in TRACKER.md Known Issues (a missing `[hidden] { display: none !important; }` rule let an unconditional `.btn { display: inline-flex }` always win), and a real `init_db()` crash on any second real app restart once a non-idempotent `ALTER TABLE ADD COLUMN` migration exists (fixed with a `schema_migrations` tracking table). 530/530 full suite passes (up from 515), zero flakes.
- Task 2.6 (2026-09-14, by Claude Code as PM + Implementer): fixed 3 of 6 findings from a
  post-Task-2.5 `/vp-audit` self-review pass. `ARCHITECTURE.md`'s `### Video` API docs now
  mention `aspect_ratio` and the `mp4_vertical` download format (stale since Task 2.5b).
  `video_service.generate_video()` now deletes a stale `video_vertical.mp4` left on disk
  when a later regenerate call doesn't request `"9:16"` again, instead of silently
  orphaning it while the DB column quietly returns to `NULL`. `step1_config.js`'s
  `escapeHtml()` now also escapes `"`/`'`, not just `&`/`<`/`>` -- verified as a real,
  reachable bug (not just theoretical) by reverting the fix and watching a quote-breakout
  payload actually corrupt a rendered `value="..."` attribute before restoring it. The
  other 3 findings (a missing `die-vp-p1-complete` git tag, `save_video_job`'s pre-existing
  error-path field-wiping, a design note on `init_db()`'s migration-fallback assumption)
  were left noted-only in TRACKER.md Known Issues per the user's explicit choice. 532/533
  full suite passes (1 pre-existing tracked flake).
- Phase 3 documentation (2026-09-15, by Claude Code as PM + Implementer): `README.md`
  updated to reflect Phase 2's completion; new `docs/prompt-guide.md` (how to customize
  the Gemini script/learning/thumbnail/YouTube prompt templates, including the
  CEFR-ceiling-vs-language-toggle precedence rule and solo-speaker override); new
  `docs/tts-setup.md` (Edge TTS voice map, the Scottish/British voice-id limitation, and
  why real OmniVoice integration was investigated but not pursued); new `docs/api.md`
  auto-generated from the app's real FastAPI OpenAPI schema via new
  `scripts/generate_api_docs.py` (49 routes documented) instead of hand-written prose that
  could drift. 533/533 full suite passes (the previously-tracked Gemini-retry timing flake
  did not recur this run).
- Phase 3 Task 3.2, Demo & Review (2026-09-15, by Claude Code as PM + Implementer): new
  `scripts/generate_sample_episodes.py` produces 3 real sample episodes (A1/B1/C1) under
  `docs/samples/` — real Gemini script generation, real Edge TTS synthesis, real ffmpeg
  mix, same topic/genre/speakers held constant so CEFR level is the only variable; new
  `scripts/record_demo_video.py` drives a real in-process `uvicorn` server + Playwright
  through the entire pipeline (project creation → script → learning content → TTS/audio
  → video → thumbnail → YouTube package) with video recording enabled, producing a real
  `ffprobe`-verified 223.9-second `docs/demo/demo-video.webm`; new
  `docs/product-review.md` (feature checklist/known issues/future improvements,
  cross-checked against `ROADMAP.md`/`TRACKER.md`). Two real bugs found and fixed while
  building the recording script: Step 1's speaker-name fields are empty by default and
  block form submission, and Step 4's original 120s wait timeout was too tight for ~29
  sequential real Edge TTS calls (raised to 300s with diagnostics added).
- Phase 3 Task 3.3, Final Cleanup (2026-09-15, by Claude Code as PM + Implementer),
  closing Phase 3 in full: audited all 4 ROADMAP items first — "remove `print()` debug
  statements" and "verify `requirements.txt` is complete and pinned" were both already
  satisfied (zero `print()` calls anywhere in `app/`; every dependency already pinned
  with `==`); `.env.example` was genuinely stale, advertising 5 dead `Settings` fields
  with zero real usages anywhere (`GOOGLE_TTS_API_KEY`/`AZURE_TTS_API_KEY`/
  `AZURE_TTS_REGION` — vestiges of the pre-decision multi-engine TTS design superseded by
  the 2026-09-13 Edge-TTS-only decision; `OMNIVOICE_DEVICE`/`OMNIVOICE_MAX_CONCURRENT` —
  the real concurrency limit is the unrelated hardcoded `MAX_CONCURRENT_TTS` constant) —
  removed from both `app/core/config.py` and `.env.example`. Verification hit 2
  abnormally slow full-suite runs (real system load — a Chrome Remote Desktop session
  active on this machine) each triggering the project's pre-existing, tracked
  Gemini-retry timing flake once; confirmed non-regressive via isolated re-run.

---

## [0.1.0] — 2026-09-10

### Added
- Project initialized
- `.viepilot/` architecture artifacts created
- Brainstorm session completed

[Unreleased]: https://github.com/danghoangsqtt-sys/dailyintelenglish/compare/v1.0.0-beta...HEAD
[1.0.0-beta]: https://github.com/danghoangsqtt-sys/dailyintelenglish/compare/3fc1cb8...v1.0.0-beta
[0.1.0]: https://github.com/danghoangsqtt-sys/dailyintelenglish/commit/3fc1cb8
