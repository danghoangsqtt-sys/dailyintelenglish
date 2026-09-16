# Task 4.2c: UI Redesign Slice 2 — Video Studio page (`/step5`)

## Meta
- **ID**: 4.2c (third sub-task of Task 4.2 — UI Redesign Slice 2, split per-page per
  the 2026-09-15 brainstorm session's explicit pacing decision)
- **Phase**: 4
- **Status**: done (2026-09-16)
- **Priority**: medium
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Precedent: `tasks/task-4.2b.md` (TTS Audio Studio, done 2026-09-16 by Codex — read this
first, it is the closest real reference: same shell+timeline+inspector shape, and shows
2 real review rounds worth learning from before starting). This task wraps
`frontend/pages/step5_video.html` in the same 3-panel shell **with a timeline**
(Script/Voice/Music tracks) — the 2026-09-14 UI-redesign session decided Video is one
of the 3 pages (with Script and TTS) that has a real "sequential items" concept.

## Current state (researched before writing this plan — do not re-derive from scratch)

`frontend/pages/step5_video.html` + `frontend/static/js/step5_video.js` today: a
single-column page with 3 sections — (1) an `avatar-grid` of per-speaker portrait
upload/replace/remove cards (`Api.uploadSpeakerAvatar()`/`Api.deleteSpeakerAvatar()` —
**not consumed by video generation**, LivePortrait lip-sync is a separate,
not-yet-started effort, see Task 1.7/1.7c), (2) a `template-grid` (pick 1 of N
background templates) + an aspect-ratio toggle (`16:9`/`9:16`, real, both wired to
`Api.generateVideo(projectId, templateId, aspectRatio)`) + "Generate video" button, (3)
a `result-card` (MP4/9:16-MP4/SRT downloads + `<video>` preview). Full function map:
`renderHeader`, `renderAvatars`, `uploadAvatar`, `removeAvatar`, `renderTemplates`,
`applyLocks`, `setupAspectRatioToggle`, `setGenerateLoading`, `renderResult`,
`generateVideo`, `init`.

**Important, different from TTS**: this page does **not** currently fetch the script's
lines at all — it only needs `Api.getAudioStatus()` (gates the whole workspace on
`status === "complete"`) and `Api.listVideoTemplates()`. There is no existing per-line
concept or per-line action on this page today (unlike TTS's `previewLine`).

## Objective

Wrap in the shell: `pane-sidebar` (StepNav, `variant: "workflow"` — **the exact
regression both 4.2a and 4.2b hit when this was missing, do not repeat it a third
time**) + `pane-main` (`pane-stage` + `#resizer-top` + `pane-timeline`) +
`pane-inspector`. Reuse `frontend/static/js/shell.js`'s `WorkspaceShell.init()` exactly
as the other 2 pages do — do not modify `shell.js` itself.

### Required decisions (already settled, do not re-litigate)
1. **Timeline has 3 tracks, built from real data this page doesn't currently fetch —
   add `Api.getScript(projectId)`** (same endpoint Script/TTS already use) to `init()`,
   called alongside the existing `Api.getAudioStatus()` call. Correlate script lines to
   the audio job's real `timestamps` array (`{start_sec, end_sec, label, speaker_id}` —
   see `app/models/audio.py::TimestampOut`) **by array index**, matching how
   `AudioService`/`script_service` both order by `line_index` — this is the same
   ordering assumption Script's own timeline already relies on implicitly, not a new
   risk.
   - **Script track**: one clip per line (line text on hover/title), read-only
     reference — editing happens on Step 2, not here.
   - **Voice track**: one clip per line. By the time this page's workspace is even
     reachable, `state.audioReady` is already `true` (the whole page is gated on the
     mix being complete) — so every line's audio already exists. Label clips something
     honest like "Synced" rather than reusing TTS's "Not previewed" language, which
     wouldn't be true here.
   - **Music track**: a single clip showing the audio job's real `background_music`
     field (already available from the existing `Api.getAudioStatus()` response) or
     "No music selected" if null — same honest-absence pattern as TTS's Music track.
2. **No fake actions**: every timeline click / inspector action must map to real data
   or a real, already-existing endpoint. Do not invent a per-line video-regenerate
   action (video generation is whole-episode, not per-line — same class of restriction
   as TTS's "no fake per-item regenerate").
3. **Avatar upload/remove behavior is untouched** — keep exactly as-is; this section
   still isn't consumed by generation (LivePortrait remains deferred).
4. **Aspect-ratio toggle and "Generate video" flow are untouched** — same
   `Api.generateVideo(projectId, templateId, aspectRatio)` call, same locking behavior.

### Proposed inspector design (Codex: confirm or refine before implementing, per AR-06's
"present plan, wait for PM" step — this is a starting point grounded in real data, not
a mandate)
Selecting a line in the Script or Voice track shows in the inspector: the line's text +
speaker name (from the newly-fetched script) and its **real** measured timing window
formatted as `M:SS – M:SS` (from `timestamps[index].start_sec`/`end_sec` — genuinely
useful for spot-checking subtitle sync before rendering, not decorative). **Optional
stretch, not required**: a "▶ Play this segment" button that seeks a real
`<audio>` element (sourced from the existing `Api.audioDownloadUrl(projectId, "mp3")` —
already a real, working download endpoint, not a new one) to `start_sec` and plays
until roughly `end_sec`. If this adds meaningful complexity or risk, a plain read-only
text+timing inspector (no playback) is a perfectly acceptable, honest alternative —
present both options in your plan and PM will confirm which to build.

## File-Level Plan

- **`frontend/pages/step5_video.html`** — rewrite to the shell structure (see
  `step2_script.html`/`step4_tts.html` as precedents — step5 is closer to those two
  since it now also has a real timeline). Move the existing 3 sections into
  `pane-stage`. Trim the local `<style>` block to only what isn't already shared in
  `style.css` — **verify with `grep` first**, don't assume (Task 4.2b confirmed
  `.generate-progress`/`.result-card`/`.download-links`/`.spinner`/`#error-banner`/
  `.empty-state`/`.stage-header` etc. are shared; this page's own
  `.avatar-grid`/`.avatar-card`/`.template-grid`/`.chip`/`.template-option` classes are
  likely still page-local — confirm each one, don't guess from memory of the other
  pages' audits).
- **`frontend/static/js/step5_video.js`** — additive changes: fetch `Api.getScript()`
  in `init()` (only after `audioReady` is confirmed, since lines are meaningless
  without a completed mix), `data-line-id` on timeline clips, a `state.selectedLineId`,
  a `renderInspector()`/`selectLine()`/`renderTimeline()` set (mirror TTS's naming —
  see `step4_tts.js` for the exact reference pattern, including how it re-renders the
  timeline/inspector at every relevant state transition to avoid the staleness class of
  bug Task 4.2a hit). `WorkspaceShell.init({...})` call **with `timeline`/`resizerTop`**
  (Video has a timeline, unlike Learning). `StepNav.render(..., variant: "workflow")` —
  verify this explicitly, it is the single most repeated regression across 4.2a and
  4.2b.
- **New `tests/test_video_shell_browser.py`** (mirror `tests/test_tts_shell_browser.py`
  and `tests/test_learning_shell_browser.py`'s patterns exactly — same live-server
  fixture, same route-mocking approach, including mocking `GET .../script` alongside
  the existing `GET .../audio/status`/`GET .../video/templates`/`GET .../video/status`
  mocks this page will need):
  1. Shell resizes/collapses correctly (sidebar + inspector + timeline height drag).
  2. **Explicitly verify `StepNav.render()` includes `variant: "workflow"`** (assert
     `#pane-sidebar #step-nav .step-nav-workflow` exists) — do not skip this, it has
     been the exact regression twice already.
  3. Selecting a line shows its real text/speaker/timing in the inspector; if playback
     is implemented, verify it seeks the real audio element correctly.
  4. Regression: avatar upload/remove still calls the real endpoints unchanged;
     template selection + aspect-ratio toggle + Generate video still call
     `Api.generateVideo` with the correct arguments; empty-state (no audio yet) still
     shows correctly and does **not** attempt to fetch the script (real gate: script
     lines are irrelevant before `audioReady`).
  5. **Explicitly verify the Music timeline lane never accumulates duplicate clips
     across multiple re-renders** — Task 4.2b's exact regression. Trigger at least 2
     re-renders (e.g. select 2 different lines) in this test and assert the Music lane
     still has exactly 1 clip.

## Allowed files
- `frontend/pages/step5_video.html`
- `frontend/static/js/step5_video.js`
- `tests/test_video_shell_browser.py` (new)
- Do **not** touch `app/` (zero API/schema change — `Api.getScript()` already exists
  and is already used elsewhere; this task only adds a new *call site*, not a new
  route), `shell.js`, or any other page's files.
- If `test_step_nav_browser.py` needs `current_step == 5` added to its shell-layout
  branch (the same regression class as 4.2a and 4.2b), **this is pre-authorized in
  advance** — the pattern is now established and mechanically identical 3 times in a
  row: extend `if current_step in (2, 3, 4):` to `if current_step in (2, 3, 4, 5):`.
  Scope is that one branch condition only, same as the prior 2 rounds — no other change
  to that file.
- If a real bug is found in any *other* shared file (`style.css`, `shell.js`, or any
  test file not listed above) while implementing, **report it to PM, do not fix it
  silently**.
- State-tracking files (`.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`,
  `.viepilot/HANDOFF.json`, `.viepilot/phases/04-post-beta-polish/PHASE-STATE.md`,
  `CHANGELOG.md`) are updated by **PM only**, after acceptance — Codex does not touch
  these per AR-06.

## Verification (paste real command output in the handoff, not a description)
- `venv\Scripts\python -m pytest tests/ -q` — 100% pass, full suite (not just the new
  file) — paste real output.
- `venv\Scripts\python -m ruff check app/ tests/` — clean, paste real output.
- `node --check frontend/static/js/step5_video.js` — clean, paste real output.
- `git diff --check` — clean, paste real output.
- Real Playwright screenshot at 1440×900 (both empty state — no audio yet — and
  populated state) — describe exactly what's shown, matching the prior 2 pages' bar.
- **Specifically stress the Music-lane fix pre-emptively**: before calling this done,
  manually trigger at least 3 re-renders in your own manual verification (not just the
  1 test assertion) and confirm no duplicate clips accumulate — Task 4.2b's bug was
  found by PM's own repeated-interaction screenshot, not by a single-assertion test;
  save PM the need to repeat that this time.

## PM Acceptance
_Pending — filled in by PM (Claude Code) after independently re-running every
verification command above and reading the full diff, per AR-06. Do not mark this task
`done` — that is PM's decision alone._

## Implementer Evidence (Awaiting PM Review — 2026-09-16)

- Migrated Video Studio to the shared 3-pane shell with workflow StepNav, resizable
  sidebar/inspector/timeline, and Script/Voice/Music tracks.
- Added the approved read-only inspector using real script speaker/text and audio-job
  timestamps by array index. A timestamp mismatch displays "timing unavailable" rather
  than inferring data.
- Kept script loading non-fatal: its timeline reports a friendly scoped error while
  avatar/template/aspect-ratio/generate controls remain available.
- Preserved the existing avatar upload/remove and whole-episode video generation paths.
- New browser coverage includes shell resizing/collapse, workflow StepNav, real timing,
  empty-state script gating, non-fatal script failure, avatar/generate regressions, and
  Music-lane clip count after repeated selections.

### Manual browser verification

Used a real local server and Chrome at an explicit 1440×900 viewport.

- Populated project `b330d37f-a212-4cf7-a779-7a109098bd6c` rendered the workflow
  sidebar, Video stage, all 30 Script clips, all 30 Voice clips, exactly one Music
  placeholder, and the selected-line inspector with measured timing.
- Selected line 2, then line 5, then line 10 (the third interaction was through the
  Voice track). Inspector content changed respectively to Maya `0:04 – 0:09`, Alex
  `0:20 – 0:26`, and Maya `0:50 – 0:55`. After every selection the live DOM result was
  `musicCount: 1`, text `No music selected`; the final screenshot also showed exactly
  one Music badge.
- Empty project `897863a5-03f1-4eb2-9c83-7d75f25802a9` showed the finished-audio
  guidance in the stage, no script data clips, one Script placeholder, one Voice
  placeholder, and exactly one Music placeholder. No Video controls were falsely
  presented as ready.

### Verification output

Targeted regression run before the full suite:

`venv\Scripts\python -m pytest tests/test_video_shell_browser.py tests/test_video_studio_browser.py tests/test_step_nav_browser.py::test_each_page_renders_and_navigates_shared_step_nav tests/test_responsive_layout_browser.py::test_step5_no_overflow_at_1024 -q` (exit code 0):

```text
......................                                                   [100%]
22 passed in 35.80s
```

`venv\Scripts\python -m pytest tests/ -q` (exit code 1):

```text
........................................................................ [ 13%]
................................F....................................... [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 66%]
........................................................................ [ 79%]
........................................................................ [ 92%]
.........................................                                [100%]

================================== FAILURES ===================================
_______ test_generate_learning_pack_exhausts_all_fallback_models_raises _______

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x00000268DEA996A0>
no_real_sleep = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, ...]

    async def test_generate_learning_pack_exhausts_all_fallback_models_raises(monkeypatch, no_real_sleep):
        """Only once every model in GEMINI_MODEL_FALLBACKS is exhausted does generation fail."""
        fallbacks = learning_service.GEMINI_MODEL_FALLBACKS
        calls = queue_responses(monkeypatch, [FakeResponse(429, text="rate limited")] * (4 * len(fallbacks)))

        with pytest.raises(LearningGenerationError, match="exhausting all fallback models") as exc_info:
            await learning_service.generate_learning_pack("proj-1", SAMPLE_CONFIG, SAMPLE_SCRIPT_LINES)

        assert calls["n"] == 4 * len(fallbacks)
        assert calls["models"] == [model for model in fallbacks for _ in range(4)]
>       assert no_real_sleep == [1.0, 2.0, 4.0] * len(fallbacks)
E       assert [0.1, 0.1, 0....0.1, 0.1, ...] == [1.0, 2.0, 4....2.0, 4.0, ...]
E
E         At index 0 diff: 0.1 != 1.0
E         Left contains 241602 more items, first extra item: 0.1
E         Use -v to get more diff

tests\test_learning_service.py:284: AssertionError
------------------------------ Captured log call ------------------------------
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.8-flash prompt_hash=052d035b24b14947 status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.8-flash prompt_hash=052d035b24b14947 status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.8-flash prompt_hash=052d035b24b14947 status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.learning_service:learning_service.py:140 gemini_learning_model_exhausted model=gemini-3.8-flash prompt_hash=052d035b24b14947 status=429 � trying next fallback model
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.7-flash prompt_hash=052d035b24b14947 status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.7-flash prompt_hash=052d035b24b14947 status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.7-flash prompt_hash=052d035b24b14947 status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.learning_service:learning_service.py:140 gemini_learning_model_exhausted model=gemini-3.7-flash prompt_hash=052d035b24b14947 status=429 � trying next fallback model
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.6-flash prompt_hash=052d035b24b14947 status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.6-flash prompt_hash=052d035b24b14947 status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.6-flash prompt_hash=052d035b24b14947 status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.learning_service:learning_service.py:140 gemini_learning_model_exhausted model=gemini-3.6-flash prompt_hash=052d035b24b14947 status=429 � trying next fallback model
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.5-flash prompt_hash=052d035b24b14947 status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.5-flash prompt_hash=052d035b24b14947 status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.5-flash prompt_hash=052d035b24b14947 status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.learning_service:learning_service.py:140 gemini_learning_model_exhausted model=gemini-3.5-flash prompt_hash=052d035b24b14947 status=429 � trying next fallback model
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.5-flash-lite prompt_hash=052d035b24b14947 status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.5-flash-lite prompt_hash=052d035b24b14947 status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.5-flash-lite prompt_hash=052d035b24b14947 status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.learning_service:learning_service.py:140 gemini_learning_model_exhausted model=gemini-3.5-flash-lite prompt_hash=052d035b24b14947 status=429 � trying next fallback model
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.1-flash-lite prompt_hash=052d035b24b14947 status=429 attempt=1 retry_in_s=1.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.1-flash-lite prompt_hash=052d035b24b14947 status=429 attempt=2 retry_in_s=2.0
WARNING  app.services.learning_service:learning_service.py:103 gemini_learning_retryable_error model=gemini-3.1-flash-lite prompt_hash=052d035b24b14947 status=429 attempt=3 retry_in_s=4.0
WARNING  app.services.learning_service:learning_service.py:140 gemini_learning_model_exhausted model=gemini-3.1-flash-lite prompt_hash=052d035b24b14947 status=429 � trying next fallback model
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_learning_service.py::test_generate_learning_pack_exhausts_all_fallback_models_raises
1 failed, 544 passed, 2 warnings in 496.70s (0:08:16)
```

The failure is the same pre-existing Gemini-retry/background-server sleep timing flake
documented in Task 4.2b's PM review, outside this task's allowed files. The failed test
passed immediately in isolation:

`venv\Scripts\python -m pytest tests/test_learning_service.py::test_generate_learning_pack_exhausts_all_fallback_models_raises -q` (exit code 0):

```text
.                                                                        [100%]
1 passed in 0.52s
```

`venv\Scripts\python -m pytest tests/test_video_shell_browser.py -q` (exit code 0):

```text
....                                                                     [100%]
4 passed in 9.44s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/step5_video.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/04-post-beta-polish/tasks/task-4.2c.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step5_video.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step5_video.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_step_nav_browser.py', LF will be replaced by CRLF the next time Git touches it
```

These are Git's Windows line-ending conversion notices; no whitespace error was
reported.

## PM Re-review (2026-09-16) — ACCEPTED

Independently re-verified rather than trusting the report, per AR-06:

- Read the full diff for `frontend/pages/step5_video.html` and
  `frontend/static/js/step5_video.js`: shell structure, `variant: "workflow"`,
  `renderTimeline()` clearing all 3 lanes upfront (proactively addressing Task 4.2b's
  exact bug class before it could recur), the graceful `/script`-failure handling
  (catches, sets `state.timelineError`, does **not** call `showError()`, execution
  continues to templates/render — confirmed this does not block the core workflow),
  and `timingForLine()`'s `Number.isFinite()` guard (never invents timing data) — all
  match the approved plan exactly, no scope creep.
- Confirmed `tests/test_step_nav_browser.py`'s change is exactly the pre-authorized
  one-line branch extension, nothing else touched.
- Re-ran `tests/test_video_shell_browser.py` independently: **4/4 pass**.
- Re-ran the pre-existing `tests/test_video_studio_browser.py` (not in Codex's
  `allowed_files`, the exact file whose real-404-on-`/script` risk was flagged before
  coding started) together with `test_step_nav_browser.py` and
  `test_responsive_layout_browser.py`: **34/34 pass** — confirms the graceful-failure
  design choice was correct and didn't require touching that file.
- **Independent visual stress test**: wrote a disposable script clicking through 6
  line selections in a row (double the plan's own "at least 3" ask) against a real
  running instance, then counted and screenshotted the Music lane. Real result:
  exactly 1 clip (`"focus-bed.mp3"`) survives all 6 re-renders. Screenshot also
  confirmed the Script/Voice tracks render real per-line data and the inspector shows
  correct `M:SS – M:SS` timing (spot-checked the math: `0.4s`/`2.9s` → `0:00 – 0:02`,
  correct floor-based formatting).
- Re-ran `node --check`, `ruff check app/ tests/`, and `git diff --check`
  independently — all clean, matching the Implementer's report exactly.
- Ran the **full suite** myself: **544 passed, 1 failed** — the failure was
  `test_script_service.py::test_generate_script_retries_on_429_then_succeeds`, the
  project's pre-existing Gemini-retry timing flake (unrelated module, 1011.69s run —
  well above the ~250-450s baseline, consistent with the documented pattern). Confirmed
  non-regressive: passes instantly (0.65s) in isolation.

**This closes Task 4.2c.** 3 of 7 pages now use the shell/timeline/inspector
conventions (Script, Learning, TTS, Video). Remaining: Thumbnail, YouTube, Music
Library, Step1-Config. This is the second task delegated end-to-end to Codex, and the
review loop again worked as designed — no real defects found this round, unlike 4.2b,
suggesting the accumulated task-card guidance (explicitly warning about the exact 2
regressions hit before) is paying off.
