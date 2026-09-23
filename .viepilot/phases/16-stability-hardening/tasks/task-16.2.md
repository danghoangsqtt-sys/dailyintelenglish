# Task 16.2 — ffmpeg Timeouts (ENH-008)

- **Status:** done
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

**Amendment B (PM CHANGES on 17cb199, plan Amendment B 4f6ba97) — atomic output write**
The original design's timeout branch did `output_path.unlink(missing_ok=True)`
where `output_path` is the *final* `video.mp4` / `video_vertical.mp4` — wrong,
because ffmpeg's `-y` truncates that file the instant a re-render starts, and
`mark_video_job_failed` (BUG-017) deliberately leaves the DB row pointing at
the prior successful video on any failure. A timed-out (or otherwise failed)
re-render would therefore delete the file the DB row still points at, or at
best leave it truncated — the exact class of bug BUG-017 was written to
prevent, just reached from a different direction. The pre-existing
(non-timeout) failure path had this same latent issue; this amendment fixes
both at once.

Both `_render_video_sync` and `_render_vertical_sync` now render into a temp
sibling path — `output_path.parent / f"{output_path.stem}.rendering
{output_path.suffix}"` (e.g. `video.rendering.mp4`, `.mp4` kept so ffmpeg
still infers the right container from the extension) — never the final path
directly:
- The ffmpeg command's output-path argument becomes the temp path; every
  other argument (including `-t`) stays byte-identical to today. This is the
  one narrow amendment to the task's "don't change ffmpeg arguments"
  prohibition — the prohibition's intent (don't touch encoding behavior) is
  preserved; only *where the bytes land* changes.
- `returncode == 0` → `os.replace(temp_path, output_path)` (atomic on both
  POSIX and Windows for same-volume paths, which this always is — both under
  `settings.DATA_DIR`). The final file only ever changes via this one
  successful, atomic swap.
- `TimeoutExpired` **or** `returncode != 0` → `temp_path.unlink(missing_ok=True)`,
  then raise `VideoRenderError` (timeout message as before for the timeout
  branch; the existing `f"ffmpeg ... failed: {result.stderr[-500:]}"` message,
  unchanged, for the non-zero-returncode branch). The final path is never
  touched on any failure path, for either function.
- `_render_vertical_sync`'s `source_mp4_path` argument is unaffected by this —
  it's already required to be the *final*, previously-replaced `video.mp4`
  from the first pass (its caller, `generate_video`, only calls it after the
  first `await asyncio.to_thread(_render_video_sync, ...)` has returned
  successfully), so it necessarily reads a complete file either way.

**Test plan (Amendment B)**
- `test_render_video_sync_leaves_the_prior_video_untouched_on_timeout`:
  pre-create `output_path` (`video.mp4`) with known marker bytes, run the
  same timeout scenario as the original design's timeout test, then assert
  `output_path.read_bytes()` is still exactly those marker bytes (not
  truncated, not deleted) and that no `video.rendering.mp4` sibling is left
  behind.
- The success-path assertion (no leftover temp file after a real render)
  rides on the existing real-ffmpeg tests in this file
  (`test_generate_video_produces_a_real_playable_mp4` etc.) — add one
  explicit assertion there that `output_path.with_name("video.rendering.mp4")`
  does not exist after a successful `generate_video()` call, so the
  temp-then-replace path is verified on the real success path too, not only
  synthetically.
- The original two timeout tests
  (`test_render_video_sync_raises_video_render_error_on_timeout`,
  `test_render_vertical_sync_raises_video_render_error_on_timeout`) are kept
  as designed, updated only to assert against the temp path instead of the
  final path where they check for leftover files.

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

**N4 (PM nit on 95d8b29, folded in pre-acceptance) — `os.replace` itself can fail**
`os.replace(temp_path, output_path)` can raise `OSError` on its own — most
realistically a Windows `PermissionError` ([WinError 5]) if `output_path` is
open elsewhere (e.g. the Video Studio preview streaming it through
`FileResponse`, which opens the file without `FILE_SHARE_DELETE`). Before
this fix that left `video.rendering.mp4` behind and surfaced as a generic
`"Video rendering failed: [WinError 5] ..."` via `generate_video`'s catch-all
`except Exception`. Both `os.replace` call sites (identical logic, so
factored into one new helper, `_publish_rendered_output(temp_path,
output_path, context)`) now wrap the replace in `try/except OSError`: on
failure, `temp_path.unlink(missing_ok=True)`, then raise a
`VideoRenderError` with a user-actionable message (names the exception type,
asks the user to close whatever has the file open and retry) — `from None`,
same rationale as the timeout branch. `output_path` itself is never at risk
either way: `os.replace` never partially applies, so a failed replace leaves
the prior video exactly as it was.

**Test plan (N4)**
`test_render_video_sync_raises_actionable_error_when_replace_fails`:
monkeypatches `video_service.subprocess.run` to a fake that reports success
(`returncode = 0`) and actually writes the temp file (so the real code path
reaches the replace step), then monkeypatches `video_service.os.replace` to
raise `PermissionError`. Pre-creates `output_path` with marker bytes.
Asserts: `VideoRenderError` is raised with "could not replace" in the
message, `output_path.read_bytes()` is still exactly the marker bytes, and
the temp file no longer exists. Covers `_render_video_sync`'s call site;
`_render_vertical_sync` shares the same `_publish_rendered_output` helper, so
one test covers both call sites' actual replace-failure logic.

## Verification (required)

A fake command that sleeps past a tiny patched timeout → `VideoRenderError`, job `error`,
partial file removed. Existing render tests unchanged. Revert-and-confirm-failure.
Full suite. `ruff`.

## Evidence

- Design commit `17cb199` (CHANGES on 17cb199 → Amendment B required, everything
  else approved as drafted). Implementation commit `95d8b29` (Amendment B).
  PM's own diff review + revert check confirmed on `95d8b29` (TRACKER
  `7991541`): diff matches Amendment B, targeted 20/20, own revert check
  (drop `timeout=` → 4 tests fail; restored → 20/20), tree clean — with one
  follow-up, N4 (below), folded in before final acceptance.
- Files touched, all within the allowed list (plus the pre-approved Amendment
  A allowance for `tests/test_ai_health_api.py`, already committed in
  `17cb199`): `app/services/video_service.py` (`_render_timeout_seconds`,
  `_rendering_temp_path`, `_publish_rendered_output` (N4), timeout +
  temp-then-atomic-replace write in both `_render_video_sync` and
  `_render_vertical_sync`, duration threaded into `_render_vertical_sync` and
  its one call site), `app/core/constants.py`
  (`VIDEO_RENDER_TIMEOUT_MIN_SECONDS = 300`,
  `VIDEO_RENDER_TIMEOUT_PER_AUDIO_SECOND = 4.0`), `tests/test_video_service.py`
  (+5 new tests, +1 assertion on an existing success-path test), `CHANGELOG.md`.
- Targeted run: `tests/test_video_service.py` → 21 passed (20 + N4's new test).
- Full suite: `./venv/Scripts/python.exe -m pytest -q` → **945 passed** (944
  after Amendment B + N4's 1 new test). No baseline test broke.
- `ruff check app scripts tests` → all checks passed.
- Revert-and-confirm-failure: temporarily dropped the `timeout=`/`except
  TimeoutExpired` handling from `_render_video_sync` (calling
  `subprocess.run` with no timeout) and re-ran
  `test_render_video_sync_raises_video_render_error_on_timeout` alone → it
  failed (the sleepy fake command completed normally with no timeout
  enforced, so the code fell through to `_publish_rendered_output` on a temp
  file that was never created, raising `FileNotFoundError` instead of the
  expected `VideoRenderError` — a different failure mode than anticipated,
  but confirms the timeout guard is what makes the test pass at all).
  Restored the guard → the same test and the full `test_video_service.py`
  file (21 tests) passed again.
- Verification bullets from the card, confirmed by test:
  - Fake command sleeps past a tiny patched timeout →
    `VideoRenderError`, partial (temp) file removed:
    `test_render_video_sync_raises_video_render_error_on_timeout`,
    `test_render_vertical_sync_raises_video_render_error_on_timeout`.
  - Existing render tests unchanged: all pre-existing tests in this file
    still pass, real ffmpeg still exercised, only with a `timeout=` now
    present that a sub-second fixture render never approaches.
  - Amendment B (BUG-017 interaction): the prior final video is never
    truncated or deleted on a timed-out re-render:
    `test_render_video_sync_leaves_the_prior_video_untouched_on_timeout`.
  - No double-wrapped error message through the public entry point:
    `test_generate_video_timeout_surfaces_as_video_render_error_not_double_wrapped`.
  - N4 (`os.replace` itself fails) → actionable `VideoRenderError`, temp file
    cleaned up, prior video untouched:
    `test_render_video_sync_raises_actionable_error_when_replace_fails`.
