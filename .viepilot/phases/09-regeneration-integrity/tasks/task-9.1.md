# Task 9.1: Preserve prior job data on regeneration failure; downgrade status on voice-settings change

## Meta
- **ID**: 9.1 (first task of Phase 9 — Regeneration Integrity)
- **Phase**: 9
- **Status**: planned
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

(Pending — Codex to present pre-code plan per AR-06 before any implementation.)
