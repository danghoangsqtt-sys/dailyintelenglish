# Task 2.2: Bug Fixes & Performance — Blocking Calls + 429 Retry Audit

## Meta
- **ID**: 2.2 (first slice of ROADMAP.md Phase 2 "Bug Fixes & Performance" — covers items
  1 and 4 of 4; items 2 and 3 addressed by audit/scope decision, not code, below)
- **Phase**: 2
- **Status**: done (2026-09-13)
- **Priority**: medium
- **Assignee**: PM (Claude, autonomous continuation, "tiếp tục")

## Context (read before planning)

Audited all 4 ROADMAP.md "2.2 Bug Fixes & Performance" items before scoping, same
discipline as every "2.3 UX Polish" sub-task this session:

1. **"Fix any blocking API calls → move to executor"** — dispatched a read-only research
   agent to grep every `async def` in `app/services/*.py` and `app/api/*.py` for
   filesystem/subprocess calls not wrapped in `asyncio.to_thread`. Confirmed by direct
   file reads afterward. Found 4 genuine, small, real gaps (not the ~25 already-correct
   usages, which the agent independently verified are all inside sync helpers already
   dispatched via `asyncio.to_thread`):
   - `app/services/video_service.py`'s `generate_video()`: `background_path.is_file()`,
     `output_dir.mkdir(...)`, and `srt_path.write_text(...)` (a full SRT file write) all
     run directly on the event loop before the existing `to_thread`-wrapped ffmpeg call.
   - `app/services/tts_service.py`'s `synthesize_line()`: `settings.OMNIVOICE_MODEL_PATH
     .exists()`, `cache_dir.mkdir(...)`, and `audio_path.write_bytes(audio_bytes)` (can be
     hundreds of KB) all unwrapped — and this function runs **per script line** during
     "Generate All," a genuine hot path under concurrent synthesis.
   - `app/services/audio_service.py`'s `mix_project()`: `candidate.is_file()` (background
     music existence check) unwrapped.
   - `app/api/tts.py`'s `list_engines()`: `settings.OMNIVOICE_MODEL_PATH.exists()` AND
     (found independently while reading the file, same class of issue the agent's grep
     patterns didn't target) `shutil.which("piper")` — both blocking, both unwrapped,
     directly inside a request handler.
2. **"Optimize OmniVoice batch: generate 5 lines per batch instead of sequential"** —
   moot. Per the user's 2026-09-13 decision (TRACKER.md Known Issues), real OmniVoice
   integration will not be pursued; there is no OmniVoice batch pipeline to optimize.
3. **"Add progress cancellation (stop mid-generation)"** — audited the architecture: every
   generation route (`script/generate`, `learning/generate`, `audio/generate`,
   `video/generate`, `thumbnails/generate`, `youtube/generate`) is a synchronous
   request/response call the client awaits directly — there is no background-job queue
   or cancellation-token mechanism anywhere in this app. Building real mid-generation
   cancellation would mean converting some or all of these into background jobs with a
   cancel endpoint — a genuinely large architectural change, not a "bug fix." Deferred as
   its own future task, same class of decision as this session's "auto-save indicator"
   scope-narrowing (recognize a genuinely bigger item and don't force it into a quick
   slice).
4. **"Fix Gemini retry logic for 429 rate limit errors"** — already done. Every
   Gemini-calling service (`script_service.py`, `learning_service.py`,
   `thumbnail_service.py`, `youtube_service.py`) already has exponential backoff
   (1s→2s→4s) retrying only HTTP 429, built during Phase 1. This ROADMAP line predates
   that work and was never updated — closing via audit, no code needed.

So this task's real, actionable scope is item 1 only: 4 small, targeted fixes.

## Objective

Wrap each of the 4 confirmed unwrapped blocking filesystem calls in `asyncio.to_thread`
(or fold them into an existing/new small sync helper dispatched that way), so no request
handler or service function ever blocks the event loop on disk I/O.

## Paths (`allowed_files` — do not touch anything outside this list)

- `app/services/video_service.py`
- `app/services/tts_service.py`
- `app/services/audio_service.py`
- `app/api/tts.py`
- `.viepilot/phases/02-testing-polish/tasks/task-2.2.md` (this file)

## Acceptance Criteria

- [x] `video_service.generate_video()`: the background-template existence check,
  output-directory creation, and SRT file write all happen inside a new sync helper
  (e.g. `_write_video_outputs_sync`) dispatched via `asyncio.to_thread`, called before the
  existing `_render_video_sync` dispatch. `generate_srt(...)`'s own pure-computation call
  stays outside `to_thread` (no I/O, matches this function's existing "pure,
  independently unit-testable" design) — only the three actually-blocking calls move.
- [x] `tts_service.synthesize_line()`: the `OMNIVOICE_MODEL_PATH.exists()` check and the
  cache-dir-creation + audio-bytes-write both move off the event loop (the `.exists()`
  check via a direct `asyncio.to_thread(...)` call since it's a branch condition
  evaluated before synthesis even starts; the write via a new sync helper dispatched the
  same way after synthesis completes).
- [x] `audio_service.mix_project()`: the background-music `is_file()` check moves off the
  event loop via `asyncio.to_thread`.
- [x] `app/api/tts.py`'s `list_engines()`: both `OMNIVOICE_MODEL_PATH.exists()` and
  `shutil.which("piper")` move off the event loop via one small sync helper dispatched
  through `asyncio.to_thread`.
- [x] No behavior change of any kind — same return values, same error types/messages,
  same DB writes. This is purely an event-loop-blocking fix, not a feature change.
- [x] Existing tests for all 4 touched files (`tests/test_video_service.py`,
  `tests/test_video_api.py`, `tests/test_tts_service.py`, `tests/test_tts_api.py`,
  `tests/test_audio_service.py`) still pass unmodified — proves behavior is identical.

## Forbidden Scope

- No OmniVoice batch optimization — moot per the 2026-09-13 decision, nothing to build.
- No progress-cancellation feature — genuinely large, separate future task.
- No other refactor beyond the specific blocking calls listed above (e.g. don't touch
  `_render_video_sync`/`_mix_project_sync`/`_synthesize_edge_tts` internals — they're
  already correctly thread-dispatched).
- No `git add .`, no self-approval.

## Verification Commands

- `venv\Scripts\python -m pytest tests/test_video_service.py tests/test_video_api.py tests/test_tts_service.py tests/test_tts_api.py tests/test_audio_service.py -q`
- `venv\Scripts\python -m pytest tests/ -q` (must still show 493+ passed, 0 new failures)
- `venv\Scripts\python -m ruff check app/ tests/`
- `git diff --check`

## Result (2026-09-13) — DONE

Delivered exactly the plan above, all 4 fixes:

- `video_service.py`: new `_write_video_outputs_sync(background_path, output_dir,
  srt_path, srt_content)` (existence check + `mkdir` + SRT write), dispatched via
  `asyncio.to_thread` before the existing `_render_video_sync` dispatch.
  `generate_srt(...)` itself stays a plain call (pure computation, no I/O).
- `tts_service.py`: `OMNIVOICE_MODEL_PATH.exists()` now
  `await asyncio.to_thread(settings.OMNIVOICE_MODEL_PATH.exists)` as its own awaited
  branch condition; new `_write_audio_cache_sync(cache_dir, audio_path, audio_bytes)`
  dispatched via `asyncio.to_thread` after synthesis completes.
- `audio_service.py`: the background-music `candidate.is_file()` check now
  `await asyncio.to_thread(candidate.is_file)`.
- `app/api/tts.py`: new `_detect_engine_availability_sync()` returning
  `(omnivoice_exists, piper_which)` as a tuple, dispatched via `asyncio.to_thread`,
  replacing both direct blocking calls in `list_engines()`.

Zero behavior change confirmed: all 55 pre-existing tests across the 5 touched-file test
suites pass completely unmodified (same assertions, same fixtures) — proving identical
return values, error types, and DB writes before and after.

### Verification output

`venv\Scripts\python -m pytest tests/test_video_service.py tests/test_video_api.py tests/test_tts_service.py tests/test_tts_api.py tests/test_audio_service.py -q` (exit 0):
```
55 passed in 9.69s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`git diff --check` (exit 0): only pre-existing CRLF-on-touch notices, no real errors.

`venv\Scripts\python -m pytest tests/ -q` (exit 0, full suite):
```
2 failed, 491 passed, 3 warnings in 447.13s (0:07:27)
```
Both failures — `test_learning_service.py::test_generate_learning_pack_exhausts_retries_raises`
and `::test_generate_learning_pack_non_429_error_does_not_retry` — are the documented
Gemini-retry full-suite timing flake (TRACKER.md Known Issues); this run was itself
unusually slow (447.13s vs the ~90-130s baseline), matching the flake's own established
correlation. Re-ran both in isolation: `2 passed in 0.56s`. 493 total tests (491 + these
2, both passing) — not a regression, and unrelated to any file this task touched.
