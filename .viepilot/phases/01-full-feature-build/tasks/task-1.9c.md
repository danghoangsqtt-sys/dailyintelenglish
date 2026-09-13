# Task 1.9c: Full Transcript + Learning Content in YouTube Export

## Meta
- **ID**: 1.9c
- **Phase**: 1 (close-out gap, not Phase 2 — see context)
- **Status**: done (2026-09-13) — implemented by Codex, PM-accepted
- **Priority**: high (closes a Phase 1 completion gap)
- **Assignee**: AI (Codex)

## Context (read before planning)

Phase 1's 10 major tasks are all done per their own individual task cards. During
close-out review, PM (Claude Code) re-checked `.viepilot/ROADMAP.md`'s separate,
stricter, phase-level **"Acceptance Criteria (Phase 1 Complete)"** checklist (near the
bottom of that file) and found one real gap that no individual task card's own Acceptance
Criteria had captured:

> YouTube package includes complete description + chapters + transcript + vocabulary

Task 1.9 (`task-1.9.md`) delivered title options, description, chapters, and tags — and
Sub-task 1.9b's `.zip` export (`GET /api/projects/{id}/youtube/export`) bundles
`video.mp4` + `subtitles.srt` + `thumbnail.png` + `metadata.txt` — but `metadata.txt`
never included the full script transcript or Learning Content (vocabulary/idioms/
grammar/quiz, Task 1.5). That was never part of 1.9a/1.9b's own (narrower) specs, which
is why it slipped through two rounds of otherwise-thorough review. This task closes it.

Read before planning, in this order:
- `.viepilot/ROADMAP.md` → the "Acceptance Criteria (Phase 1 Complete)" section (bottom
  of the file) — the actual requirement wording
- `.viepilot/phases/01-full-feature-build/tasks/task-1.9.md` — everything already built,
  including its own Implementation Notes for `build_export_zip()`
- `app/services/youtube_service.py` — `build_export_zip()`, `_build_metadata_text()`,
  the existing export route in `app/api/youtube.py`
- `app/services/learning_service.py` → `get_learning_content(db, project_id) -> dict | None`
  and `app/models/learning.py` for the exact field names on each item
  (`VocabularyItem`, `IdiomItem`, `GrammarItem`, `QuestionItem`)
- `app/services/script_service.py` → `get_script(db, project_id) -> list[dict]` (fields:
  `id`, `line_index`, `speaker_id`, `text`, ...) — this is the transcript source; join with
  `project["speakers"]` (already available wherever `project_service.get_project` is
  called) to label each line with the speaker's name, same pattern
  `audio_service._mix_project_sync` already uses for its timestamp labels

## Objective

Extend the existing `.zip` export so it also includes the full script transcript and (if
generated) the Learning Content pack, closing the ROADMAP.md Phase 1 completion gap.

## Paths (`allowed_files`)

- `app/services/youtube_service.py`
- `app/api/youtube.py`
- `tests/test_youtube_service.py`
- `tests/test_youtube_export_api.py`
- `.viepilot/phases/01-full-feature-build/tasks/task-1.9c.md` (this file — plan + evidence
  only; do not touch `PHASE-STATE.md`/`TRACKER.md`/`ROADMAP.md`/`CHANGELOG.md` or this
  file's own `## Meta` status/checkboxes — PM updates those on acceptance)

## Acceptance Criteria

- [x] `build_export_zip()` gains the project's script lines (with speaker names resolved)
      and, if one exists, the Learning Content pack, and writes a new file into the zip —
      e.g. `transcript_and_vocabulary.txt` — containing:
      - `=== FULL TRANSCRIPT ===` — every line as `SpeakerName: line text`, in order
      - `=== VOCABULARY ===` — each item: word (part of speech) — IPA — EN definition —
        VI definition — example sentence
      - `=== IDIOMS & COLLOCATIONS ===` — phrase — EN meaning — VI meaning — example
      - `=== GRAMMAR POINTS ===` — point — structure — EN explanation — VI explanation —
        examples
      - `=== COMPREHENSION QUESTIONS ===` — question, options (if any), correct answer,
        explanation
- [x] The transcript section is always present (a completed video/audio mix already
      implies a non-empty script — export already requires a completed video)
- [x] The vocabulary/idioms/grammar/questions sections are present **only if** Learning
      Content has been generated for the project; if not, the file says so plainly (e.g.
      `"Learning Content was not generated for this project."`) rather than omitting the
      file entirely or crashing — **exporting must not newly require Learning Content as
      a hard prerequisite** (it never was one anywhere else in the pipeline, and requiring
      it now would silently break any already-exported project's expectations)
- [x] `metadata.txt` (titles/description/tags/chapters) is unchanged in content — this is
      a new, additional file in the zip, not a merge into the existing one (keeps the
      existing `test_build_export_zip_contains_all_four_files`-style assertions valid
      after you extend them to 5 files)
- [x] Verify: unit tests for the new text-formatting function in isolation (empty pack,
      full pack, special characters/long text don't break formatting), and an updated
      real end-to-end export API test (extend `tests/test_youtube_export_api.py`'s
      existing full-pipeline test, which already generates a real project/script/audio/
      video/thumbnail — add a real Learning Content generation step, mocking only its
      Gemini call like the test already does for youtube/thumbnail) asserting the 5th
      file exists in the downloaded zip and contains the right sections

## Forbidden Scope

- No change to `metadata.txt`'s existing content/format
- No new hard prerequisite blocking export (Learning Content must stay optional)
- No changes to Learning Content generation itself (`app/services/learning_service.py`
  business logic) — read-only consumer here
- No UI changes (`/step7` already just has one export button; it doesn't need to know
  what's inside the zip)
- No `git add .`, no self-approval, no status/checkbox edits beyond this file's plan section

## Verification Commands

- `venv\Scripts\python -m pytest tests/test_youtube_service.py tests/test_youtube_export_api.py -q`
- `venv\Scripts\python -m pytest tests/ -q` (must show 432+ passed, 0 new failures)
- `venv\Scripts\python -m ruff check app/ tests/`
- `git diff --check`

## Environment preflight required before planning

Backend-only, no ffmpeg/GPU dependency beyond what Task 1.6/1.7's existing tests already
require (the full-pipeline export test mocks Edge TTS and Gemini but exercises real
AudioService/VideoService/ThumbnailService code, so it does need a working `ffmpeg` in
your sandbox exactly like `tests/test_youtube_export_api.py` already requires today — if
`ffmpeg` isn't available, report that explicitly rather than skipping/faking the test).

## Implementer Evidence (Awaiting PM Acceptance)

### Delivered

- `app/services/youtube_service.py`
  - Added `_build_transcript_and_learning_text()` with speaker-name resolution matching
    AudioService's `speaker_names_by_id.get(speaker_id, speaker_id)` fallback.
  - The transcript is always written in script order as `SpeakerName: line text`.
  - A generated Learning Content pack is rendered into vocabulary, idioms/collocations,
    grammar, and comprehension-question sections. A missing pack produces the explicit
    notice `Learning Content was not generated for this project.` instead.
  - `build_export_zip()` now adds UTF-8 encoded `transcript_and_vocabulary.txt` as the
    fifth file. `_build_metadata_text()` and `metadata.txt` content were not changed.
- `app/api/youtube.py`
  - The existing export read transaction now fetches the project script and optional
    Learning Content pack, then passes both to `build_export_zip()`.
  - Learning Content was not added to the export prerequisite list.
- `tests/test_youtube_service.py`
  - Added isolated formatting coverage for missing Learning Content, a full pack, an
    existing pack with four empty lists, speaker fallback/order, and long real Unicode
    text (Vietnamese diacritics, emoji, typographic punctuation, and special characters).
  - Renamed the ZIP test from `all_four_files` to `all_five_files` and verified UTF-8
    round-trip by decoding the actual ZIP member.
- `tests/test_youtube_export_api.py`
  - The real media pipeline now generates and persists Learning Content while mocking
    only that service's Gemini response, like the existing YouTube/thumbnail mocks.
  - The downloaded ZIP is verified to contain all five files and all required sections.
  - A separate end-to-end case proves export still succeeds without Learning Content.

The generated-empty-pack test is not an impossible fabricated state: the current
`LearningPackOut` model permits empty lists (`default_factory=list`, no list-level
`min_length`) and persistence also accepts them. The test is still defensive because a
useful Gemini result would normally contain items.

### Files changed

- `app/services/youtube_service.py`
- `app/api/youtube.py`
- `tests/test_youtube_service.py`
- `tests/test_youtube_export_api.py`
- `.viepilot/phases/01-full-feature-build/tasks/task-1.9c.md` (evidence only)

### Verification output

`venv\Scripts\python -m pytest tests/test_youtube_service.py tests/test_youtube_export_api.py -q` (exit 0):

```text
..................................                                       [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

venv\Lib\site-packages\pydub\utils.py:170
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\pydub\utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
    warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
34 passed, 3 warnings in 4.36s
```

`venv\Scripts\python -m pytest tests/ -q` (exit 0; final completion output):

```text
.............................. [ 98%]
.....                                                                    [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

venv\Lib\site-packages\pydub\utils.py:170
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\pydub\utils.py:170: RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
    warn("Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work", RuntimeWarning)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
437 passed, 3 warnings in 164.23s (0:02:44)
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0):

```text
All checks passed!
```

`git diff --check` (exit 0):

```text
warning: in the working copy of '.viepilot/phases/01-full-feature-build/tasks/task-1.9c.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/api/youtube.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/youtube_service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_youtube_export_api.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_youtube_service.py', LF will be replaced by CRLF the next time Git touches it
```

There are no whitespace/EOF errors. These are Git's Windows line-ending conversion
notices; the command exits 0.

### Remaining limits / risks

- Bare `ffmpeg` is not resolvable in the current shell, but the configured
  `DIE_FFMPEG_PATH` points to a working ffmpeg 9.0.1 binary. Both the targeted real
  export pipeline and the full suite passed through the project's existing PATH shim.
- The three warnings above are pre-existing dependency/runtime warnings; none is a test
  failure or a newly suppressed condition.
- No UI, schema, Learning Content generation logic, export prerequisite, or existing
  `metadata.txt` format was changed.

## PM Acceptance (2026-09-13)

Independently re-verified, not just trusted — re-ran every claimed command myself:
- `pytest tests/test_youtube_service.py tests/test_youtube_export_api.py -q`: 34 passed (matches).
- `pytest tests/ -q`: 436 passed + 1 failure
  (`test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s`), confirmed
  passing in isolation immediately after (0.55s) — this is the same known, accepted
  Gemini-retry-pattern flake tracked in
  `.viepilot/debug/session-debug-20260912T000000Z.json` (now its 6th occurrence, 3rd time
  hitting this exact test, always on an unrelated change set during a slow full-suite
  run) — not caused by this change, logged and moved on rather than re-investigated.
- `ruff check app/ tests/`: clean (matches).
- `git diff --check`: exit 0, only the pre-existing CRLF-on-touch notices (matches).

Read the actual diff, not just the report:
- `_build_transcript_and_learning_text()`: speaker-name fallback
  (`speaker_names_by_id.get(speaker_id, speaker_id)`) is exactly `audio_service`'s
  pattern, as required. Direct bracket access on required Pydantic-model fields
  (`item['word']`, `item['phrase']`, etc.) is safe, not reckless: I traced
  `learning_service.update_learning_content()`'s write path back to
  `app/api/learning.py`'s `payload: LearningPackUpdate` route parameter — every write to
  `learning_contents` (both initial Gemini generation and any later user edit) is
  Pydantic-validated before persistence, so a stored item is guaranteed to carry every
  required field. `.get()` is used only for the genuinely optional `examples`/`options`/
  `correct_answer`/`explanation` fields, which correctly have `default_factory=list`/`""`
  in their models — the defensive-vs-direct-access split in the diff is deliberate and
  correct, not inconsistent.
- `build_export_zip()`: `metadata.txt` write path is byte-for-byte unchanged;
  `transcript_and_vocabulary.txt` is a genuinely new, separate archive member — confirmed
  via the new API test's explicit negative assertions (`"FULL TRANSCRIPT" not in
  metadata`, `"VOCABULARY" not in metadata`).
- `app/api/youtube.py`: Learning Content fetch was correctly added as a plain optional
  read (`get_learning_content` returning `None` is not added to the `missing` list) —
  confirmed by the new `test_export_without_learning_content_still_succeeds` test, which
  never generates Learning Content and still gets a 200 with a real zip.
- Test quality: real Vietnamese diacritics, emoji, `<>&`, and 200x-repeated long text are
  used (not placeholder ASCII), and the zip member is round-tripped through actual
  `zipfile`/UTF-8 decode, not just checked as a Python string in memory — this is a
  genuine encoding proof, not a superficial one. The "empty-but-generated pack" test
  claim (four empty lists is a real, reachable state per `LearningPackOut`'s schema, not
  a fabricated scenario) checks out: I confirmed none of `VocabularyItem`/`IdiomItem`/
  `GrammarItem`/`QuestionItem` are used with a list-level `min_length` on the pack itself.

**Accepted.** This closes Sub-task 1.9c — Task 1.9 now has no open gaps against either its
own Acceptance Criteria or ROADMAP.md's phase-level "Acceptance Criteria (Phase 1
Complete)" checklist.
