# Task 5.2: Timeline polish — proportional clip width + keyboard resizer

## Meta
- **ID**: 5.2 (second task of Phase 5 — UI Polish Backlog)
- **Phase**: 5
- **Status**: done (2026-09-17)
- **Priority**: medium
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: the 2026-09-16 Codex UI audit's P1 finding — "timeline clip width isn't
proportional to real duration... a 3s and a 7s line render at nearly the same width" —
plus its accessibility note that the horizontal timeline resizer has `tabindex="0"` but
no keydown handler. Both re-verified as still real by PM before opening this task (see
Current state below — the audit's blanket "Script/TTS/Video all affected" claim needed
correcting, not just confirming).

## Current state (researched before writing this plan — do not re-derive from scratch)

**Shared CSS**: `frontend/static/css/style.css:197`,
`.timeline-clip { flex: 0 0 auto; min-width: 72px; ... }` — every clip on every
timeline page auto-sizes to its text content (`"{speaker} #{n}"` etc.), clamped to a
72px minimum. No page sets an explicit width today; this is why width currently tracks
label length, not duration.

**Per-page data availability is not uniform — the audit's claim needs correcting**:
- `step2_script.js`'s `renderTimeline()` (line ~149): Script's clips have **no timing
  concept at all**, ever — this page runs before audio exists, and nothing on it
  fetches or computes per-line duration. There is no real data to make width
  proportional to. **Script is out of scope for the width change** — forcing a fake
  or estimated duration here would violate this project's "no fake features"
  precedent (established at Task 1.7c and reinforced throughout Task 4.2).
- `step5_video.js`: already computes real per-line timing —
  `timingForLine(line)` (line ~58) reads `state.audioJob.timestamps[index]`
  (`{start_sec, end_sec}`, real measured values from `Api.getAudioStatus()`, already
  fetched in `init()`) and returns `null` if unavailable. `renderTimeline()` (line
  ~78) already uses this for the Voice clip's tooltip (`formatTiming(timing)`) but
  never for its width. **This page needs zero new API calls** — the data already
  exists, just isn't applied to width.
- `step4_tts.js`: **also already calls** `Api.getAudioStatus(state.projectId)` in
  `init()` (line ~537, to detect a previously-completed job and render the download
  section) — but the fetched `job` is a local variable, never stored to `state`, so
  its `timestamps` aren't available to `renderTimeline()` today. Making TTS's Voice
  clips proportional requires storing `state.audioJob = job` when the fetch succeeds
  (a small state addition, not a new API call) and computing timing the same way
  Video does. Before audio is generated (`state.audioJob` absent), TTS's clips must
  keep their current text-driven auto-width — never guess a duration that doesn't
  exist yet.

**Keyboard resizer**: `frontend/static/js/shell.js`'s `makeVerticalResizer()` (line
41-51) has a full `keydown` handler (`ArrowLeft`/`ArrowRight`, `Shift` for a bigger
step, clamped to `{min, max}`). `makeHorizontalResizer()` (line 54-82) has **no**
keydown handler at all — confirmed via direct read, matching the audit finding
exactly. This function is shared by all 3 timeline pages (Script/TTS/Video all pass
`timeline`+`resizerTop` to `WorkspaceShell.init()`), so fixing it once in `shell.js`
fixes keyboard access to the timeline resizer everywhere it exists.

## Objective

1. Make timeline clip width proportional to real duration **on Video, and on TTS once
   audio exists** — never on Script, and never using a fake/estimated duration.
2. Add keyboard support (`ArrowUp`/`ArrowDown`, `Shift` for a bigger step) to
   `shell.js`'s horizontal resizer, mirroring the existing vertical-resizer pattern
   exactly.

### Required decisions (already settled by PM, do not re-litigate)

1. **Width-only, not a full time-axis timeline.** The audit's complaint was
   specifically about clip *width* not reflecting duration — this task does not build
   absolute time-based positioning/alignment across lanes (Script/Voice/Music clips
   lining up at shared horizontal time offsets), a ruler, or zoom/scroll controls.
   That would be a materially bigger feature than what was asked for or measured as a
   problem. Disclose this scope boundary in the plan explicitly, the same way Task
   4.2c disclosed skipping timeline playback.
2. **Formula and constants are Codex's implementation call, within this reasoning**:
   a linear px-per-second scale, clamped to a minimum width matching the existing 72px
   (so very short lines stay legible/clickable) — pick and justify the exact
   px/second multiplier and whether a maximum cap is needed, based on what actually
   looks right against real script durations (typically a few seconds to ~15s per
   line). State the chosen numbers and reasoning in the plan.
3. **Never fabricate a duration.** If `timingForLine()` (Video) or the equivalent
   TTS lookup returns `null`/unavailable, that clip keeps today's auto-width behavior
   — do not substitute an estimate, average, or placeholder duration.
4. **TTS requires a small state addition, no new API call.** Store the already-fetched
   `job` from `Api.getAudioStatus()` into `state.audioJob` in `init()`; reuse it in
   `renderTimeline()` the same way Video's `timingForLine()` does. If TTS's `job` came
   back 404 (no audio yet, the existing `catch` branch), `state.audioJob` stays unset
   and clips render exactly as they do today.
5. **Keyboard resizer**: `ArrowUp` grows the timeline pane, `ArrowDown` shrinks it
   (matching the existing drag behavior's direction: dragging the handle down shrinks
   the pane below it), `Shift` gives a bigger step, exactly mirroring
   `makeVerticalResizer()`'s keydown handler shape. `makeHorizontalResizer()`'s `max`
   parameter is a **function** (`() => window.innerHeight * 0.7`), not a plain number
   like the vertical resizers' `max` — call it fresh on every keypress, the same way
   the existing `pointermove` handler already does, don't cache a stale value.

## Proposed File-Level Plan

- `frontend/static/js/shell.js`: add a `keydown` listener to `makeHorizontalResizer()`
  mirroring `makeVerticalResizer()`'s handler shape (`ArrowUp`/`ArrowDown` instead of
  `ArrowLeft`/`ArrowRight`, remembering `max` is a function here).
- `frontend/static/js/step5_video.js`: in `renderTimeline()`, compute an inline width
  (e.g. `scriptClip.style.width` / `voiceClip.style.width`) from `timingForLine(line)`
  when available, for both the Script and Voice clips (both represent the same line at
  the same point in time, so both should size together) — falling back to no inline
  style (today's auto-width) when timing is unavailable.
- `frontend/static/js/step4_tts.js`: store `state.audioJob = job` in `init()` after a
  successful `Api.getAudioStatus()` call; add an equivalent `timingForLine()`-style
  helper (or reuse the same shape as Video's); apply proportional width to the Voice
  clip (and Script clip, for the same reason as above) when timing is available.
- `frontend/static/css/style.css`: only if a shared class/rule is genuinely needed
  beyond inline widths (e.g., a `min-width` override) — state whether this was needed.
- New or extended browser test coverage — Codex to confirm exact file(s) in the
  pre-code plan. Must include: a real width-comparison assertion (e.g., a clip with a
  longer measured duration has a measurably larger bounding-box width than a shorter
  one — not just "a style attribute exists"), a case confirming a line with no
  timing data keeps the unstyled/auto-width behavior, and a keyboard-driven resize
  test for the horizontal resizer on at least one timeline page (mirroring the
  existing vertical-resizer keyboard tests, if any exist — check first).

## Allowed files
- `frontend/static/js/shell.js`
- `frontend/static/js/step4_tts.js`
- `frontend/static/js/step5_video.js`
- `frontend/static/css/style.css` (only if needed per above — state whether it was
  needed in the evidence)
- Existing or new browser test file(s) — Codex to confirm exact filename(s) in the
  pre-code plan (e.g. extending `tests/test_tts_shell_browser.py` /
  `tests/test_video_shell_browser.py`, and/or a new shell-level resizer test file).
- This task card, for plan/evidence updates.

## PM Plan Review (2026-09-17) — APPROVED (plus one endorsed addition)

Codex presented its pre-code plan per AR-06's 3-step process. Plan matches every
required decision in this task card.

**Width formula confirmed well-reasoned**: 16px/second, 72px minimum (matches the
existing CSS floor exactly), 240px maximum (= 15s). Derived from real read-only data
(78 real timing samples, p90 5.97s, max 7.66s observed) — not guessed. A 3s clip stays
at the 72px floor, a 7s clip reaches 112px, giving a real, visible difference for the
audit's exact complaint case. Invalid/zero/negative/missing durations correctly get no
inline width at all (auto-width preserved) rather than a guessed value.

**Endorsed addition beyond the original task card**: storing the job returned by
`Api.generateAudio()` into `state.audioJob` too (not just the one from `init()`'s
`Api.getAudioStatus()` call). PM independently verified this is sound before approving
— `app/api/audio.py:30-71` (`POST .../audio/generate`) and `:74-83`
(`GET .../audio/status`) both return the identical `job` shape via `ok(job, ...)`,
including real `timestamps` (confirmed: `save_audio_job(..., timestamps=result
["timestamps"], ...)` at generate-time is the same field `get_audio_job()` returns).
This is genuinely the same already-fetched data, not a new call, and closes a real gap
the task card's original plan would have left: without it, a user generating audio for
the first time wouldn't see proportional widths until reloading the page. Good catch —
approved.

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `frontend/static/js/shell.js`
- `frontend/static/js/step4_tts.js`
- `frontend/static/js/step5_video.js`
- `tests/test_tts_shell_browser.py` (extended)
- `tests/test_video_shell_browser.py` (extended)
- `frontend/static/css/style.css` — confirmed **not** needed, existing rules suffice
- `step2_script.js` — confirmed **not** touched; Codex's own verification plan
  (`git diff --exit-code` + Script regression run) is a good extra safety check PM
  will also independently confirm on review
- This task card, for evidence only (Status field remains PM-only)

**Plan approved as presented, including the endorsed addition. No changes
requested.** Codex may proceed to implementation.

## Verification checklist
- [ ] A real measured-width comparison: a longer-duration clip is visibly/measurably
  wider than a shorter one on Video (and on TTS once audio exists) — bounding-box
  width assertion, not just a style-attribute presence check.
- [ ] A line with no timing data (before TTS audio exists, or a `null` return from
  `timingForLine`) renders with today's unchanged auto-width behavior — no fake
  duration substituted.
- [ ] Script's timeline is confirmed **unchanged** — no width logic added there.
- [ ] Keyboard `ArrowUp`/`ArrowDown` (and `Shift`-modified) on the horizontal timeline
  resizer actually resizes the timeline pane, on at least one page that has one.
- [ ] Existing timeline-related tests (Script/TTS/Video shell tests, `test_step_nav_
  browser.py`, resizer-related tests) still pass unmodified or with justified updates.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `node --check` on touched JS, `git diff --check` — all
  clean, real output pasted.

## Implementer Evidence (Awaiting PM Review — 2026-09-17)

### Scope delivered

- `frontend/static/js/step4_tts.js`: uses real audio-job timestamps for matching
  Script/Voice clip widths. The already-fetched job is retained from both
  `Api.getAudioStatus()` and `Api.generateAudio()`, so existing jobs and a first
  Generate All both update widths without an extra API request or reload.
- `frontend/static/js/step5_video.js`: uses the existing real `timingForLine()` data
  for matching Script/Voice clip widths.
- Both pages use the approved formula: `16px/s`, clamped to `72px..240px`. Missing,
  invalid, zero, or negative timing leaves the clip without an inline width, preserving
  the existing auto-width behavior instead of estimating data.
- `frontend/static/js/shell.js`: the horizontal resizer now supports ArrowUp/ArrowDown
  (12px) and Shift+ArrowUp/Shift+ArrowDown (40px), with a fresh dynamic maximum on
  every keypress.
- `frontend/static/css/style.css` was not needed and was not changed.
- `frontend/static/js/step2_script.js` was not changed; Script keeps its existing
  non-timed clip sizing.

### Browser coverage and manual visual check

`venv\Scripts\python.exe -m pytest tests/test_tts_shell_browser.py tests/test_video_shell_browser.py -q`
(exit code 0):

```text
............                                                             [100%]
12 passed in 26.16s
```

`venv\Scripts\python.exe -m pytest tests/test_tts_shell_browser.py tests/test_video_shell_browser.py tests/test_new_shell_resize_browser.py tests/test_tts_audio_browser.py tests/test_video_studio_browser.py tests/test_step_nav_browser.py -q`
(exit code 0):

```text
................................................                         [100%]
48 passed in 80.47s (0:01:20)
```

A disposable real-Chromium check at 1440×900 measured the approved 3-second and
7-second clips, exercised the keyboard resizer, checked the untouched Script page,
and checked document overflow. Raw measurement output:

```json
{"screenshot":"C:\\Users\\Admin\\AppData\\Local\\Temp\\task-5.2-tts-timeline.png","tts_script_widths":[72,112],"tts_voice_widths":[72,112],"timeline_height_before":210,"timeline_height_after_up":222,"timeline_height_after_shift_up":262,"script_page_inline_widths":["",""],"horizontal_overflow":false}
```

The screenshot was kept outside the repository at
`C:\Users\Admin\AppData\Local\Temp\task-5.2-tts-timeline.png`. Visual inspection
confirmed a clean timeline with the 7-second clip visibly wider than the 3-second
clip.

### Required verification output

`venv\Scripts\python.exe -m pytest tests/ -q` (exit code 1 — two instances of the
task card's accepted pre-existing Gemini-retry/shared-sleep timing flake class; both
pass together in isolation immediately below):

```text
........................................................................ [ 12%]
..........................................F............................. [ 25%]
........................................................................ [ 37%]
........................................................................ [ 50%]
........................................................................ [ 63%]
........................................................................ [ 75%]
........................................................................ [ 88%]
..........................................F......................        [100%]
================================== FAILURES ===================================
__________ test_generate_learning_pack_non_429_error_does_not_retry ___________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001E5E47F3E00>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_learning_pack_non_429_error_does_not_retry(monkeypatch, no_real_sleep):
        calls = queue_responses(monkeypatch, [FakeResponse(500, text="internal error")])

        with pytest.raises(LearningGenerationError, match="HTTP 500"):
            await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)

        assert calls["n"] == 1
>       assert no_real_sleep == []
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == []
E
E         Left contains 283926 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_learning_service.py:296: AssertionError
_____________ test_generate_package_retries_on_429_then_succeeds ______________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x000001E5E55E4980>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_package_retries_on_429_then_succeeds(monkeypatch, no_real_sleep):
        calls = queue_responses(
            monkeypatch, [FakeResponse(429, text="rate limited"), gemini_ok_response(VALID_PACKAGE)]
        )

        await youtube_service.generate_package(SAMPLE_PROJECT, SAMPLE_SCRIPT_LINES)

        assert calls["n"] == 2
>       assert no_real_sleep == [1.0]
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 789128 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_youtube_service.py:217: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.youtube_service:youtube_service.py:107 gemini_youtube_retryable_error model=gemini-3.8-flash prompt_hash=7130789c18899117 status=429 attempt=1 retry_in_s=1.0
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_learning_service.py::test_generate_learning_pack_non_429_error_does_not_retry
FAILED tests/test_youtube_service.py::test_generate_package_retries_on_429_then_succeeds
2 failed, 567 passed, 2 warnings in 659.35s (0:10:59)
```

Task 5.2 changes no Python/backend/Gemini code. Both failures received unrelated
0.1-second background sleeps in the shared `no_real_sleep` fixture (283,926 and
789,128 extra entries respectively), which is the already documented flake class.
Immediate isolated rerun together:

`venv\Scripts\python.exe -m pytest tests/test_learning_service.py::test_generate_learning_pack_non_429_error_does_not_retry tests/test_youtube_service.py::test_generate_package_retries_on_429_then_succeeds -q`
(exit code 0):

```text
..                                                                       [100%]
2 passed in 0.56s
```

`venv\Scripts\ruff.exe check app/ tests/` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/shell.js` (exit code 0):

```text
(no stdout or stderr)
```

`node --check frontend/static/js/step4_tts.js` (exit code 0):

```text
(no stdout or stderr)
```

`node --check frontend/static/js/step5_video.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --exit-code -- frontend/static/js/step2_script.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/05-ui-polish-backlog/tasks/task-5.2.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/shell.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step4_tts.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step5_video.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_tts_shell_browser.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_video_shell_browser.py', LF will be replaced by CRLF the next time Git touches it
```

These are Windows line-ending conversion notices, not whitespace errors.

## PM Re-review (2026-09-17) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word.

**Diff review** — read the full `git diff` for all 5 touched files:
- `shell.js`: exactly the one keydown listener added to `makeHorizontalResizer()`,
  mirroring `makeVerticalResizer()`'s shape precisely (`ArrowUp`/`ArrowDown`, 12/40px
  step, `max()` called fresh on every keypress rather than cached).
- `step5_video.js` / `step4_tts.js`: identical `measuredClipWidth()`/
  `applyMeasuredClipWidth()` helpers (72/16/240 constants), correctly returning `null`
  for missing/non-finite/zero/negative durations (no inline `style.width` set in that
  case, preserving auto-width) and applied consistently to both the Script and Voice
  clip for a given line. TTS additionally gained `state.audioJob` set from **both**
  `Api.getAudioStatus()` (with an explicit `state.audioJob = null` reset in the catch
  branch) and `Api.generateAudio()` — confirmed both call sites updated, delivering
  the endorsed addition from plan review exactly as agreed.
- Confirmed via `git diff --exit-code -- frontend/static/js/step2_script.js` (exit 0)
  and `frontend/static/css/style.css` unlisted in `git status` that neither was
  touched, matching the plan exactly.

**New/extended test review**: `test_video_shell_browser.py`'s new test cleverly
reuses the existing `line-3` script fixture with a *truncated* 2-entry `timestamps`
override to exercise the "missing timing mid-list" case realistically, and asserts
real bounding-box widths (not style-attribute presence) for the 3s/7s comparison, the
missing-timing fallback, and Script/Voice width parity. `test_tts_shell_browser.py`
adds an equivalent measured-vs-auto-width test plus a full 4-step keyboard round-trip
test for the horizontal resizer (`ArrowUp`/`ArrowDown`/`Shift+ArrowUp`/
`Shift+ArrowDown`, checking real height changes each step), and extends the
pre-existing `test_generate_all_keeps_preview_then_mix_order` test with width
assertions — directly proving the "no reload needed after Generate All" addition
works, not just asserting it in prose.

**PM independently re-ran every verification command**: 48/48 targeted+regression
pass, `ruff check` clean, all 3 `node --check` clean, `step2_script.js` confirmed
unchanged, `git diff --check` exit 0 — all matched the Implementer's report exactly.

**Screenshot review**: confirms the "Alex #1" (short) clip visibly narrower than
"Sam #2" (long) clip in both the Script and Voice lanes, matching the measured
72px/112px values in the raw JSON output.

**Full suite, run independently**: 568 passed, 1 failed
(`test_generate_learning_pack_exhausts_all_fallback_models_raises`) in 655.73s — the
known Gemini-retry timing flake class, confirmed passing in isolation at 0.54s. Task
5.2 touched zero backend/Gemini code, so non-regressive by construction.

**Zero real defects found on PM review.** Accepted as delivered — no changes
requested.

**This closes Task 5.2.** Phase 5 continues with Task 5.3 (small polish batch) next.
