# Task 9.1: Preserve prior job data on regeneration failure; downgrade status on voice-settings change

## Meta
- **ID**: 9.1 (first task of Phase 9 — Regeneration Integrity)
- **Phase**: 9
- **Status**: done (2026-09-18)
- **Priority**: high (2 real bugs, 1 involving actual data loss from the DB's
  perspective)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: the user had Codex run its own independent, parallel read-only `/vp-audit`
pass alongside PM's own audit (2026-09-18). Codex found 10 issues (0 critical, 1
high, 4 medium, 5 low); PM independently re-verified all 5 of the "important" ones
(1 high + 4 medium) by reading the actual source directly — **all 5 confirmed real**,
no false positives, an excellent scan. User chose to open this phase to fix the 2
most serious: `BUG-017` (real data loss on regeneration failure) and `BUG-016`
(voice-settings change doesn't invalidate downstream status — the same bug class as
`BUG-013`, already fixed for script edits under Task 7.1). The other 3
(`BUG-018`, `BUG-019`, `ENH-007`) are logged in `.viepilot/requests/` but explicitly
out of scope for this task per user decision.

## Current state (researched before writing this plan — do not re-derive from scratch)

### Item A — BUG-017: failed regeneration wipes a prior success's data (confirmed real, worse than "medium")

`app/services/audio_service.py::save_audio_job` and
`app/services/video_service.py::save_video_job` are full-column UPSERTs
(`INSERT ... ON CONFLICT(project_id) DO UPDATE SET col = excluded.col` for every
column). `app/api/audio.py`'s and `app/api/video.py`'s `except Exception:` handlers
call these same functions with only `status="error"` and `error_message=str(exc)` —
every other keyword defaults to `None`, and the UPSERT unconditionally overwrites
every column with these defaults. Confirmed via direct read: if a project already has
a successful job and a *subsequent* regeneration attempt fails, the previous job's
`mp3_path`/`wav_path`/`timestamps_json`/`duration_seconds`/`loudness_lufs` (audio) or
`mp4_path`/`mp4_path_vertical`/`srt_path` (video) are wiped to `NULL` in the DB —
**even though those files are still on disk, untouched.** The user's UI would show a
failed state with no download link, while a perfectly good previous output becomes
unreachable via the API (`download_audio`/`download_video` require
`job["status"] == "complete"` and a non-null path).

`audio_jobs` schema (`app/db/migrations/001_init.sql:67-81`): `id`, `project_id`
(UNIQUE), `status`, `mp3_path`, `wav_path`, `timestamps_json`, `background_music`,
`duration_seconds`, `loudness_lufs`, `error_message`, `started_at`, `completed_at`.

`video_jobs` schema (`001_init.sql:84-97` + `005_video_vertical_output.sql:9` adding
`mp4_path_vertical`): `id`, `project_id` (UNIQUE), `status`, `mode` (default
`'background'`), `mp4_path`, `mp4_path_vertical`, `srt_path`, `background_image`,
`subtitle_style_json`, `error_message`, `started_at`, `completed_at`.

### Item B — BUG-016: voice-settings change doesn't invalidate downstream status (same class as BUG-013)

`app/services/project_service.py::update_speaker` (via `PATCH
/api/projects/{id}/speakers/{speaker_id}`) updates
`tts_engine`/`voice_description`/`speed`/`pitch`/`volume` in place, never checks or
changes `project.status`. Confirmed via reading `SpeakerUpdate`
(`app/models/project.py:77-96`): every field on this model directly affects TTS
synthesis output — there is no cosmetic-only field (name/gender/accent are
deliberately excluded from it, per its own docstring, and live on a different update
path).

**Mitigating factor found during PM's re-verification** (real, but doesn't remove the
bug): the actual audible/downloadable output is never wrong, because both real
consumption paths — the per-line "Listen" button
(`frontend/static/js/step4_tts.js::previewLine`) and "Generate All"
(`generateAll`, lines 487-514) — always call `Api.previewTtsLine()` for every line
before playing or mixing, which always re-synthesizes fresh audio from *current*
speaker settings (`tts_service.py::synthesize_line`, no cache-skip anywhere). So the
real gap is purely the `status` field (and the stale on-disk MP3/MP4 file it still
points at) claiming "complete" when it no longer reflects current settings, until
Generate All is re-run — an honesty/signal gap, exactly like BUG-013.

`app/services/project_service.py::mark_script_changed` (added under Task 7.1) already
implements a downgrade-to-`script_generated` for exactly this situation — **but its
existing shape is not directly reusable as-is**: it has a `draft -> script_generated`
advance branch specific to the *script being generated for the first time*, which
would be actively wrong here — a speaker's voice settings can legitimately be edited
at Step 1 config time, before any script exists, and must **not** spuriously advance
the project to `script_generated` just because a voice was tweaked. Any fix must
reuse or share only the *downstream-downgrade* half of that logic (`audio_generated`/
`video_generated`/`complete` -> `script_generated`), while remaining a no-op for
`draft` and `script_generated`.

## Objective

Two independent backend-only fixes, no shared code path between them (only backend
Python files touched, matching Task 7.1's precedent — no frontend/JS changes
required for either).

### Required decisions (already settled by PM, do not re-litigate)

1. **BUG-017 fix must be non-destructive on failure**: a failed regeneration attempt
   must only change `status`/`error_message`/`completed_at` on the existing job row
   — every other column (file paths, duration, timestamps, etc.) must be preserved
   exactly as it was before the failed attempt. If no job row exists yet for this
   project (a genuine first-ever attempt), insert a fresh error-only row — this
   matches today's existing first-attempt behavior, so no regression there.
2. **BUG-017 fix must not touch the success path**: `save_audio_job`/`save_video_job`
   (called on a *successful* generation) continue to fully replace every column
   exactly as today — that is correct behavior for a genuine new success. Only the
   *failure* path changes.
3. **BUG-016 fix must not affect `draft` or `script_generated` projects at all** —
   editing a speaker's voice settings at either of those stages is a normal, expected
   part of the Step 1/early workflow and must not change `status`. Only
   `audio_generated`/`video_generated`/`complete` downgrade to `script_generated`,
   non-destructively (no files/records deleted — matches Task 7.1's decision #1
   exactly).
4. **BUG-016 fix should share logic with `mark_script_changed` where sensible**
   (both ultimately perform the identical downstream-downgrade), but Codex should
   propose the exact shape in its pre-code plan — e.g. extracting a shared private
   helper that both `mark_script_changed` and a new function call, vs. a fully
   separate function. Whichever shape is chosen must not change `mark_script_changed`'s
   existing external behavior (verified by Task 7.1's existing tests continuing to
   pass unmodified).
5. Do **not** invent a new UI staleness banner as part of this task — same reasoning
   as Task 7.1's decision #4: the existing Dashboard status badge and "Continue"
   routing already give an honest signal once status correctly reflects reality.

## Proposed File-Level Plan

- `app/services/audio_service.py`: add a narrow `mark_audio_job_failed`-style
  function (exact name/shape TBD by Codex) performing the non-destructive UPDATE
  described in decision #1, falling back to an INSERT only when no row exists.
- `app/services/video_service.py`: the equivalent for `video_jobs`.
- `app/api/audio.py`: route `generate_audio`'s `except` block to call the new audio
  function instead of `save_audio_job`.
- `app/api/video.py`: route `generate_video`'s `except` block to call the new video
  function instead of `save_video_job`.
- `app/services/project_service.py`: add the downstream-only downgrade capability
  described in decision #4 (new function and/or extracted shared helper).
- `app/api/projects.py`: call the new downgrade function from `update_speaker`'s
  route handler, inside its existing `_write_transaction` block.
- New or extended backend test coverage proving: (a) a failed regeneration after a
  prior success preserves every other column and the file remains downloadable, for
  both audio and video; (b) a failed *first-ever* attempt still records a sensible
  error-only row, unchanged from today; (c) editing speaker voice settings at
  `audio_generated`/`video_generated`/`complete` downgrades to `script_generated`;
  (d) editing speaker voice settings at `draft`/`script_generated` does **not**
  change status (a real regression test for the exact mistake a naive reuse of
  `mark_script_changed` would introduce); (e) `mark_script_changed`'s own existing
  behavior (Task 7.1's tests) is unaffected by any refactor.

## Allowed files
- `app/services/audio_service.py`
- `app/services/video_service.py`
- `app/services/project_service.py`
- `app/api/audio.py`
- `app/api/video.py`
- `app/api/projects.py`
- Existing or new backend test file(s) — Codex to confirm exact filename(s) in the
  pre-code plan.
- This task card, for plan/evidence updates.

## Verification checklist
- [ ] A failed audio regeneration after a prior success preserves `mp3_path`/
  `wav_path`/`timestamps_json`/`duration_seconds`/`loudness_lufs`/`background_music`;
  only `status`/`error_message`/`completed_at` change; the prior file remains
  downloadable via the API.
- [ ] Same for video: `mp4_path`/`mp4_path_vertical`/`srt_path`/`background_image`/
  `subtitle_style_json`/`mode` preserved.
- [ ] A genuinely first-ever failed attempt (no prior job row) still records a
  sensible error-only row — no regression.
- [ ] Editing a speaker's voice settings when status is `audio_generated`/
  `video_generated`/`complete` downgrades to `script_generated`.
- [ ] Editing a speaker's voice settings when status is `draft`/`script_generated`
  does not change status at all.
- [ ] Task 7.1's existing tests for `mark_script_changed` still pass unmodified.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces
  as a pass in isolation.
- [ ] `ruff check app/ tests/`, `git diff --check` — all clean, real output pasted.

## PM Plan Review

### Implementer Pre-Code Plan (Awaiting PM Confirmation)

Codex presented a plan covering both items with the following key design points:

**Item A (BUG-017)**: `mark_audio_job_failed`/`mark_video_job_failed` — narrow
`UPDATE ... SET status='error', error_message=?, completed_at=? WHERE project_id=?`,
touching nothing else; falls back to an error-only `INSERT` when `cursor.rowcount ==
0` (no prior row). Existing `save_audio_job`/`save_video_job` success paths left
fully untouched. The two API `except` blocks call the new functions with
`commit=False` inside the existing `_write_transaction`.

**Consequential change correctly identified and justified**: `download_audio`/
`download_video` currently gate on `job["status"] != "complete"`. Codex proposes
widening this to accept `status in ("complete", "error")` as long as the requested
format's path is non-null — otherwise a preserved-but-now-"error"-status job's still
valid old file would remain unreachable, defeating the whole point of the fix. This
is a correct, necessary consequence of Acceptance Criteria #3 ("the previously-
successful file remains downloadable"), not scope creep — both files are already in
the locked `allowed_files`.

**Item B (BUG-016)**: extracts a private helper
`_downgrade_downstream_to_script_generated(db, project_id, current_status)` in
`project_service.py`, handling only the 3 downstream statuses -> `script_generated`
downgrade (no commit, no draft handling). `mark_script_changed` calls it for its
existing 3-downstream-status branch, unchanged behavior otherwise (draft-advance and
script_generated no-op untouched). A new `mark_speaker_voice_changed()` is a no-op at
`draft`/`script_generated`, and calls the same shared helper otherwise — correctly
avoiding the naive-reuse trap flagged in this task card's "Required decisions" #4.
The `PATCH /speakers/{id}` route calls it only when the request body has at least one
field actually set (`exclude_unset` check), inside the same `_write_transaction` as
`update_speaker`, so both roll back together on any failure.

**Test plan**: reuses existing test files throughout
(`test_audio_service.py`/`test_video_service.py`/`test_audio_api.py`/
`test_video_api.py`/`test_projects_api.py`), covers all 5 required scenarios
including raw-row before/after diffing for the preservation checks, and — critically
— explicitly runs `tests/test_project_service.py` **unmodified** as a regression
guard proving Task 7.1's `mark_script_changed` behavior is untouched by the refactor.

### PM Review (2026-09-18) — APPROVED

Independently re-verified rather than approving on the plan's word alone.

**Confirmed the download-gate change is real and necessary**: read
`download_audio`/`download_video` directly — both currently gate on
`job["status"] != "complete"` with an identical `path is None` follow-up check.
Codex's proposed widening is exactly what Acceptance Criteria #3 requires and is
scoped to files already in `allowed_files`.

**Confirmed the shared-helper refactor is safe**: read `mark_script_changed`'s
current implementation directly (single `SELECT status`, branch on
`script_generated`/`draft`/downstream, final downstream branch does a plain `UPDATE`
+ optional commit). Extracting that final branch into a shared helper taking
`current_status` as an explicit parameter changes nothing about
`mark_script_changed`'s external behavior — its `draft` branch still goes through the
existing validated `update_project`/`_validate_status_transition` path unchanged.

**Confirmed the naive-reuse trap is correctly avoided**: `mark_speaker_voice_changed()`
is a genuinely separate function with its own no-op branches for `draft`/
`script_generated` — it does not call `mark_script_changed()` directly, so there is
no risk of the draft-advance branch firing from a Step 1 voice-settings edit.

**Plan approved as presented. No changes requested.** Codex may proceed to
implementation.

## Implementer Evidence (Awaiting PM Acceptance)

### Implementation summary

- Added `mark_audio_job_failed()` and `mark_video_job_failed()`. An existing job is
  updated through a deliberately narrow statement that changes only `status`,
  `error_message`, and `completed_at`; all prior artifact paths, metadata, job id, and
  `started_at` remain untouched. If no job exists, each helper inserts a minimal error
  row with fresh `id`/timestamps. Both helpers retain the established `commit` contract.
- Left the successful `save_audio_job()` and `save_video_job()` UPSERT paths unchanged.
  The audio/video generation exception handlers now call the narrow failure helpers
  with `commit=False` inside their existing write transactions.
- Widened audio/video download eligibility from `complete` to `complete` or `error`,
  while still requiring the requested format's path to be non-null. Consequently a
  preserved prior success remains downloadable after a failed regeneration, whereas a
  first-ever failed attempt still returns 404 from download routes.
- Extracted `_downgrade_downstream_to_script_generated()`, which handles only
  `audio_generated`/`video_generated`/`complete`. `mark_script_changed()` delegates only
  its existing downstream branch to this helper; its special `draft ->
  script_generated` advance and `script_generated` no-op remain unchanged.
- Added `mark_speaker_voice_changed()`, which validates the live status and uses the
  shared downstream-only helper. The speaker PATCH route calls it only for a non-empty
  patch, before `update_speaker()` and inside the same transaction, so failures roll
  both operations back and the returned project contains the final status. `draft`,
  `script_generated`, and empty speaker patches remain status no-ops.
- Added raw-row preservation tests, first-failure fallback tests, failed-regeneration
  HTTP/download tests, and all five speaker status cases. Task 7.1's existing
  `tests/test_project_service.py` was not modified and passes in the targeted suite.

### Files changed

- `app/services/audio_service.py`
- `app/services/video_service.py`
- `app/services/project_service.py`
- `app/api/audio.py`
- `app/api/video.py`
- `app/api/projects.py`
- `tests/test_audio_service.py`
- `tests/test_video_service.py`
- `tests/test_audio_api.py`
- `tests/test_video_api.py`
- `tests/test_projects_api.py`
- `.viepilot/phases/09-regeneration-integrity/tasks/task-9.1.md` (evidence only;
  `Status` unchanged)

### Verification evidence

Targeted final command, including the unmodified Task 7.1 service regressions:

```text
> venv\Scripts\python -m pytest tests/test_audio_service.py tests/test_video_service.py tests/test_audio_api.py tests/test_video_api.py tests/test_projects_api.py tests/test_project_service.py -q
........................................................................ [ 60%]
................
................................                         [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
120 passed, 2 warnings in 31.82s
```

Full suite, final run:

```text
> venv\Scripts\python -m pytest tests/ -q
........................................................................ [ 11%]
........................................................................ [ 23%]
........................................................................ [ 35%]
........................................................................ [ 46%]
........................................................................ [ 58%]
........................................................................ [ 70%]
........................................................................ [ 81%]
........................................................................ [ 93%]
.......................................                                  [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
615 passed, 2 warnings in 323.59s (0:05:23)
```

Lint:

```text
> venv\Scripts\python -m ruff check app/ tests/
All checks passed!
```

One intermediate API-test run had one test-design failure: the attempted use of an
invalid template never entered `generate_video` because request validation correctly
rejected it before the route. This was not a production failure. The test was corrected
to inject `VideoRenderError` inside the generation call, thereby exercising the intended
first-attempt fallback path, and the video API suite then passed 18/18 before the final
targeted/full runs above. Exact intermediate summaries:

```text
FAILED tests/test_video_api.py::test_generate_video_unknown_template_returns_422
1 failed, 29 passed, 2 warnings in 17.78s

> venv\Scripts\python -m pytest tests/test_video_api.py -q
..................                                                       [100%]
18 passed, 2 warnings in 11.60s
```

Final whitespace check (exit code 0; Git emitted only its Windows line-ending notices):

```text
> git diff --check
warning: in the working copy of '.viepilot/phases/09-regeneration-integrity/tasks/task-9.1.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/api/audio.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/api/projects.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/api/video.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/audio_service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/project_service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/video_service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_audio_api.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_audio_service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_projects_api.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_video_api.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_video_service.py', LF will be replaced by CRLF the next time Git touches it
```

Final worktree scope:

```text
> git status --short
 M .viepilot/phases/09-regeneration-integrity/tasks/task-9.1.md
 M app/api/audio.py
 M app/api/projects.py
 M app/api/video.py
 M app/services/audio_service.py
 M app/services/project_service.py
 M app/services/video_service.py
 M tests/test_audio_api.py
 M tests/test_audio_service.py
 M tests/test_projects_api.py
 M tests/test_video_api.py
 M tests/test_video_service.py
```

### Limits / residual risks

- A failed regeneration deliberately leaves the job status at `error` while exposing
  the preserved prior artifact through the download API. This is the approved behavior;
  no separate UI stale-artifact banner was added.
- A non-empty speaker patch conservatively invalidates downstream status even when the
  submitted value equals the stored value. An empty patch is explicitly a no-op.
- The two test warnings are pre-existing FastAPI/Starlette dependency deprecations,
  unrelated to Task 9.1. There were zero test failures and zero Gemini retry flakes in
  the final full-suite run.

## PM Re-review (2026-09-18) — ACCEPTED

Independently re-verified rather than accepting the report on its word.

**Diff review** — read the full `git diff` for all 6 production files:
- `audio_service.py`/`video_service.py`: `mark_audio_job_failed`/`mark_video_job_failed`
  confirmed to touch only `status`/`error_message`/`completed_at` via a plain `UPDATE
  ... WHERE project_id = ?`, falling back to a minimal error-only `INSERT` only when
  `cursor.rowcount == 0` — exactly as planned, no other column referenced.
- `audio.py`/`video.py`: both `except` blocks now call the new narrow functions
  instead of the old full-replace `save_audio_job`/`save_video_job`. Both download
  routes' gate widened from `status != "complete"` to `status not in ("complete",
  "error")`, with `audio.py` gaining a new explicit `path is None` check (video.py
  already had an equivalent check for the vertical/SRT case, correctly reused as-is
  rather than duplicated).
- `project_service.py`: `_downgrade_downstream_to_script_generated` correctly
  no-ops (returns `False`) for anything outside the 3 real downstream statuses.
  `mark_script_changed`'s `draft`/`script_generated` branches are byte-for-byte
  unchanged; only its final branch now delegates to the shared helper — confirmed
  identical resulting SQL and commit behavior. `mark_speaker_voice_changed` does its
  own independent status fetch (not reusing `get_project`, avoiding an unnecessary
  speakers-table join) and is a genuine no-op for `draft`/`script_generated` — it
  never calls `mark_script_changed` or shares its draft-advance branch, correctly
  avoiding the exact trap this task card flagged.
- `projects.py`: the `PATCH /speakers/{id}` route change is a minimal 2-line
  addition — `mark_speaker_voice_changed` called only when
  `patch.model_dump(exclude_unset=True)` is truthy, before `update_speaker`, both
  inside the same `_write_transaction`.

**Test review**: `test_mark_audio_job_failed_preserves_every_existing_non_failure_column`
does a genuine raw-row set-diff (every column except the 3 allowed to change must be
byte-identical before/after) and monkeypatches `_now()` to return distinguishable
"successful-at"/"failed-at" values, proving `started_at` truly survives from the
original success while only `completed_at` reflects the failed attempt — not just
asserting the same value twice. `test_failed_audio_regeneration_keeps_prior_mix_downloadable`
and its video equivalent are full end-to-end HTTP tests that generate a *real* audio/
video mix, download and save the actual response *bytes*, force a second attempt to
fail, then assert the download endpoint returns those exact same bytes afterward —
proving the fix at the actual byte level a user would experience, not just at the DB
row level. `test_update_speaker_downgrades_only_downstream_statuses` is fully
parametrized across all 5 real statuses, driving each project through genuine forward
`PUT` transitions before checking the `PATCH speaker` outcome — exactly the
regression-guard shape required by this task card's decision #3. Confirmed via `git
diff` that `tests/test_project_service.py` (Task 7.1's existing suite) has zero
changes.

**PM independently re-ran every verification command**: 120/120 targeted (including
Task 7.1's unmodified `test_project_service.py`), `ruff check` clean, `git diff
--check` exit 0, `git status --short` confirmed exactly the 12 reported files touched.

**Full suite, run independently — 2 failures found, both confirmed non-regressive,
one of them a newly-observed flake class**: 613 passed, 2 failed in 309.39s.
`test_generate_script_backoff_sequence_is_1s_2s_4s` is the project's long-documented
Gemini-retry/backoff timing flake class, unrelated to any of this task's files.
`test_music_library_waveform_browser.py::test_waveform_renders_real_pixels_for_a_real_audio_file`
is **not** part of that documented class and has never failed in any full-suite run
this session — it decodes real audio via the Web Audio API and reads real canvas
pixels in a headless browser, a timing/resource-sensitive shape similar in kind to
the Gemini-retry class but distinct in cause. It touches code (`waveform.js`,
`music_library.html/js`) that Task 9.1 never modifies. Both tests re-run individually
and passed instantly (4.87s combined) — confirmed non-regressive. Noted here
explicitly rather than silently folded into "the known flake" so it's tracked
honestly; not blocking acceptance given the isolation-pass result and zero code
overlap with this task.

**Zero real defects found on PM review.** Accepted as delivered — no changes
requested.

**This closes Task 9.1 — and Phase 9 (Regeneration Integrity) in full**, since it was
the phase's only task. BUG-016 and BUG-017 are now resolved.
