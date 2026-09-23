# Task 16.2 — ffmpeg Timeouts (ENH-008)

- **Status:** in_progress
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
`CHANGELOG.md`. Plan Amendment A (PM, folded in post-16.1-acceptance, nit N3):
`tests/test_ai_health_api.py`, for the one fix described under "N3" below only
— no other change to that file.

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

**1. Timeout constants (constants.py)**
Add `VIDEO_RENDER_TIMEOUT_MIN_SECONDS = 300` and
`VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND = 4.0` next to the existing `VIDEO_*`
block. A helper in `video_service.py`,
`_render_timeout_seconds(audio_duration_seconds: float) -> float`, returns
`max(VIDEO_RENDER_TIMEOUT_MIN_SECONDS, VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND *
audio_duration_seconds)`. Both `_render_video_sync` and
`_render_vertical_sync` call it with the same `audio_duration_seconds` — one
render's timeout budget, not two independent ones — since they're two passes
over the same underlying audio length, and the card explicitly says the
vertical pass "needs the duration passed in," not its own formula.

**2. `_render_vertical_sync` gains a duration parameter**
Its signature becomes `_render_vertical_sync(source_mp4_path: Path,
output_path: Path, audio_duration_seconds: float) -> None`. `generate_video`
already has `audio_job["duration_seconds"]` in scope at its one call site
(the `"9:16"` branch) — passed straight through, no new plumbing needed
upstream of that.

**3. Both `subprocess.run` calls (video_service.py:120, :154)**
Add `timeout=_render_timeout_seconds(audio_duration_seconds)` to the existing
`subprocess.run(command, capture_output=True, text=True)` call in each
function (command arguments themselves are unchanged — Explicitly Forbidden).
Wrap each in `try/except subprocess.TimeoutExpired`. On catch:
`output_path.unlink(missing_ok=True)` (removes whatever partial file ffmpeg
had started writing via `-y`; `subprocess.run` itself already kills the child
process on timeout, per the stdlib's own implementation — that part needs no
new code), then `raise VideoRenderError(f"ffmpeg video render timed out
after {timeout:g} s")` (`"ffmpeg vertical (9:16) render timed out after
{timeout:g} s"` for the second function) — `from None`, since the original
`TimeoutExpired` traceback (all of `stdout`/`stderr` captured so far) adds
nothing actionable beyond what the message already says, and swallowing it
avoids ever surfacing a raw stdlib exception up through `generate_video`'s
own `except Exception as exc:` blocks (which would otherwise re-wrap it a
second time with a redundant "Video rendering failed: ..." prefix).

**4. Test plan (`tests/test_video_service.py`)**
No fixture ffmpeg binary is stubbed anywhere in this file today — the
existing tests run the real `ffmpeg`/`ffprobe` against tiny real media, per
this file's own header comment. Reproducing an actual multi-hundred-second
hang isn't practical in a unit test, so the new tests monkeypatch
`video_service.subprocess.run` itself with a wrapper that *ignores the
built ffmpeg command* and instead really execs a short-lived Python
subprocess (`[sys.executable, "-c", "import time; time.sleep(5)"]`) via the
**real** `subprocess.run`, forwarding only the `timeout=` kwarg the caller
passed. This exercises the real stdlib `TimeoutExpired` path — not a
hand-rolled fake exception — while staying fast and platform-independent
(mirrors this file's stated preference for exercising real behavior over
mocks, applied to the one piece, `ffmpeg`, that a unit test can't actually
wait 300s+ for).
- `test_render_video_sync_raises_video_render_error_on_timeout`: patches
  `VIDEO_RENDER_TIMEOUT_MIN_SECONDS` down to ~0.05s via
  `monkeypatch.setattr(video_service, "VIDEO_RENDER_TIMEOUT_MIN_SECONDS", 0.05)`
  (module-level, read at call time, same pattern as 16.1's
  `AI_WORKER_LOOP_ERROR_BACKOFF_SECONDS`), installs the sleepy `subprocess.run`
  wrapper, pre-creates a dummy `output_path` file to stand in for ffmpeg's
  partial output, calls `_render_video_sync` directly, and asserts:
  `VideoRenderError` is raised with "timed out" in the message, and
  `output_path` no longer exists.
- `test_render_vertical_sync_raises_video_render_error_on_timeout`: same
  shape for `_render_vertical_sync`, confirming the new duration parameter
  actually drives the timeout too (patches the constant the same way).
- `test_generate_video_timeout_surfaces_as_video_render_error_not_double_wrapped`:
  through the public `generate_video()` entry point, confirms the message
  is exactly the one `_render_video_sync` raises (no
  "Video rendering failed: ffmpeg video render timed out..." double-wrap),
  proving the `from None` / direct-raise choice in (3) actually works through
  the existing `except VideoRenderError: raise` passthrough in
  `generate_video`.
- Revert-and-confirm-failure target:
  `test_render_video_sync_raises_video_render_error_on_timeout` — temporarily
  drop the `timeout=` kwarg from the `subprocess.run` call, confirm the test
  now hangs/fails (times out against pytest's own run, or never raises
  `VideoRenderError` within a bounded `pytest.raises` — whichever the
  implementation shows once written), then restore.
- All 12 existing tests in this file are unaffected: none of them patch
  `subprocess.run`, so they still exercise the real ffmpeg command, now with
  a (generous, real-duration-derived) `timeout=` added that a sub-second
  fixture render never approaches.

**N3 (PM nit, folded in via Amendment A, `tests/test_ai_health_api.py`)**
`test_health_reports_worker_alive_false_when_the_worker_task_is_dead`
currently does `monkeypatch.setattr(ai_worker, "_task", None)` and leaves the
revert to monkeypatch's own fixture-teardown undo, which can run *after* the
`client` fixture's own teardown (`with TestClient(app)` exiting → lifespan
shutdown → `await ai_worker.stop()`). If `_task` is still `None` at that
point, `stop()`'s own `if self._task is None: return` guard fires
immediately, and the real loop task is never awaited/cancelled — orphaned
until the TestClient's portal event loop itself closes. Fix: stop relying on
monkeypatch's teardown timing for this one attribute — save the real task,
set `ai_worker._task = None` directly, and restore it in a `try/finally`
inside the test body itself, so it's back in place before *any* fixture
teardown (including `client`'s) begins, deterministically, regardless of
fixture teardown order.

**Test plan (N3)** — no new test; existing test's body changes as described.
Confirmed manually reasoning through it; will also be visible in the targeted
run since a genuinely orphaned task would otherwise (eventually, non-
deterministically) surface as an "Exception ignored" / "Task was destroyed
but it is pending" warning on a later test in the same session — the targeted
`tests/test_ai_health_api.py` run in Evidence will note this stayed clean.

## Verification (required)

A fake command that sleeps past a tiny patched timeout → `VideoRenderError`, job `error`,
partial file removed. Existing render tests unchanged. Revert-and-confirm-failure.
Full suite. `ruff`.

## Evidence

_pending_
