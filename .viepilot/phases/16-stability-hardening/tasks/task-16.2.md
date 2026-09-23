# Task 16.2 — ffmpeg Timeouts (ENH-008)

- **Status:** not started
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** 16.1 accepted
- **Controlling detail:** plan §4 "16.2"; `.viepilot/requests/ENH-008.md`

## Measured problem (do not re-derive)

`app/services/video_service.py:120` (`_render_video_sync`) and `:154`
(`_render_vertical_sync`) call `subprocess.run(command, capture_output=True, text=True)`
with no `timeout`. Both already run in `asyncio.to_thread`, so the event loop is safe, but a
hung ffmpeg keeps the job `rendering` forever.

## Allowed files

`app/services/video_service.py`, `app/core/constants.py`, `tests/test_video_service.py`,
`CHANGELOG.md`.

## Required behaviour

1. Both calls pass `timeout = max(VIDEO_RENDER_TIMEOUT_MIN_SECONDS,
   VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND × audio_duration_seconds)` (new constants,
   suggested 300 and 4.0). The vertical pass needs the duration passed in.
2. `subprocess.TimeoutExpired` → `VideoRenderError("ffmpeg … timed out after N s")`,
   so the existing error path marks the job `error` and the user can retry.
3. Partial output files are removed on timeout.

## Explicitly forbidden

Changing the ffmpeg command arguments (the `-t` pacing from Task 14.10 stays), and moving
the calls onto the event loop.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending_

## Verification (required)

A fake command that sleeps past a tiny patched timeout → `VideoRenderError`, job `error`,
partial file removed. Existing render tests unchanged. Revert-and-confirm-failure.
Full suite. `ruff`.

## Evidence

_pending_
