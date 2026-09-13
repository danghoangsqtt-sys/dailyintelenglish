# Task 1.9c: Full Transcript + Learning Content in YouTube Export

## Meta
- **ID**: 1.9c
- **Phase**: 1 (close-out gap, not Phase 2 — see context)
- **Status**: planned
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

- [ ] `build_export_zip()` gains the project's script lines (with speaker names resolved)
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
- [ ] The transcript section is always present (a completed video/audio mix already
      implies a non-empty script — export already requires a completed video)
- [ ] The vocabulary/idioms/grammar/questions sections are present **only if** Learning
      Content has been generated for the project; if not, the file says so plainly (e.g.
      `"Learning Content was not generated for this project."`) rather than omitting the
      file entirely or crashing — **exporting must not newly require Learning Content as
      a hard prerequisite** (it never was one anywhere else in the pipeline, and requiring
      it now would silently break any already-exported project's expectations)
- [ ] `metadata.txt` (titles/description/tags/chapters) is unchanged in content — this is
      a new, additional file in the zip, not a merge into the existing one (keeps the
      existing `test_build_export_zip_contains_all_four_files`-style assertions valid
      after you extend them to 5 files)
- [ ] Verify: unit tests for the new text-formatting function in isolation (empty pack,
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
