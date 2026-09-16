# Task 4.2b: UI Redesign Slice 2 — TTS Audio Studio page (`/step4`)

## Meta
- **ID**: 4.2b (second sub-task of Task 4.2 — UI Redesign Slice 2, split per-page per
  the 2026-09-15 brainstorm session's explicit pacing decision)
- **Phase**: 4
- **Status**: done (2026-09-16)
- **Priority**: medium
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Precedent: `tasks/task-4.2a.md` (Learning page, done 2026-09-15 — read this first, it is
the closest real reference for shell/inspector conventions and shows 2 real regressions
that were found and fixed, both worth avoiding here). This task wraps
`frontend/pages/step4_tts.html` in the same 3-panel shell, **this time with a timeline**
(Script/Voice/Music tracks) — the 2026-09-14 UI-redesign session decided TTS is one of
the 3 pages (with Video) that has a real "sequential items" concept, unlike Learning.

## Current state (researched before writing this plan — do not re-derive from scratch)

`frontend/pages/step4_tts.html` + `frontend/static/js/step4_tts.js` today: a single-column
page with 3 sections — (1) a `speaker-grid` of per-speaker cards (engine/speed/pitch/
volume sliders, autosaved via `Api.updateSpeaker()` → `PATCH /api/projects/{id}/speakers/
{speaker_id}`, debounced per-field via `scheduleSpeakerSave`/`saveSpeaker`), (2) a
`line-list` of per-line preview rows (`Api.previewTtsLine()` → `POST .../tts/preview`,
plays via `Api.ttsCacheUrl()`), (3) a `generate-card` (background-music `<select>` +
"Generate All" → `Api.generateAudio()` → `POST .../audio/generate`) + a `result-card`
(final MP3/WAV player + downloads). Full function map: `renderSpeakers`, `buildSlider`,
`scheduleSpeakerSave`, `saveSpeaker`, `renderLines`, `previewLine`, `renderMusicOptions`,
`renderResult`, `generateAll`, `init`. No `data-line-id`/`data-section` selection concept
exists yet (unlike Script/Learning) — this task introduces it.

## Objective

Wrap in the shell: `pane-sidebar` (StepNav, `variant: "workflow"` — **do not repeat
Task 4.2a's regression**, that option was missing there and broke
`test_step_nav_browser.py`) + `pane-main` (`pane-stage` + `#resizer-top` + `pane-timeline`)
+ `pane-inspector`. Reuse `frontend/static/js/shell.js`'s `WorkspaceShell.init()` exactly
as Script/Learning do — do not modify `shell.js` itself.

### Required decisions (already settled, do not re-litigate)
1. **Timeline has 3 tracks**: Script (read-only reference — the already-generated lines,
   for context only; editing scripts happens on Step 2, not here), Voice (one clip per
   line reflecting its real synthesis state — not-yet-previewed vs. previewed), Music
   (the single selected background-music track, if any).
2. **No fake actions**: every timeline click / inspector action must map to a real,
   already-existing endpoint (`previewTtsLine`, `updateSpeaker`, `generateAudio`) — no
   invented per-line regenerate-audio-only endpoint, no invented waveform data that
   doesn't exist.
3. **Existing per-speaker autosave state machine is untouched** — keep
   `scheduleSpeakerSave`/`saveSpeaker`'s debounce-then-PATCH behavior exactly as-is; the
   shell wrapping must not change *when* or *how* speaker settings save.
4. **Existing "Generate All" flow is untouched** — sequential per-line
   `previewTtsLine()` calls then one `generateAudio()` call; do not parallelize or change
   this behavior as part of a UI refactor.

### Proposed inspector design (Codex: confirm or refine before implementing, per AR-06's
own "present plan, wait for PM" step — this is a starting point, not a mandate)
Selecting a line in the Voice track (or Script track) shows in the inspector: the line's
text + speaker name (same data already in `renderLines`), a "🔊 Listen" button that calls
the *existing* `previewLine()` logic (same endpoint Script's inspector uses — see
`step2_script.js`'s `handleListen` for the reference pattern: loading state, error
handling, `<audio>` element), and a link/anchor that scrolls the stage to that line's
speaker's voice-slider card in `speaker-grid` (a real, cheap, honest affordance — no new
state, just `scrollIntoView` on an existing element).

## File-Level Plan

- **`frontend/pages/step4_tts.html`** — rewrite to the shell structure (see
  `step2_script.html`/`step3_learning.html` as the 2 existing precedents — step4 is
  closer to Script since both have a real timeline). Move the existing 3 sections into
  `pane-stage`. Trim the local `<style>` block to only what isn't already shared in
  `style.css` (check `.speaker-grid`/`.speaker-card`/`.slider-row`/`.line-list`/
  `.line-card`/`.generate-card`/`.result-card` etc. against `style.css` first — Task
  4.2a found `.generate-panel`/`.spinner`/`#error-banner`/`.empty-state`/`.stage-header`/
  `.stage-title`/`.page-badges`/`.save-status`/`.inspector-*` already shared; don't
  assume, verify with `grep` before deciding what stays local vs. reuses a shared class).
- **`frontend/static/js/step4_tts.js`** — additive changes: `data-line-id` on each line
  card (for the new Voice-track clips + selection), a `state.selectedLineId`, a
  `renderInspector()`/`selectLine()` pair (mirror Script's naming), a `renderTimeline()`
  for the 3 tracks, `WorkspaceShell.init({...sidebar, resizerLeft, inspector,
  resizerRight, timeline, resizerTop, collapseBtn})` call **with `variant: "workflow"`
  on the `StepNav.render()` call** in `DOMContentLoaded`. Keep `renderSpeakers`/
  `scheduleSpeakerSave`/`saveSpeaker`/`generateAll`/`previewLine` logic itself unchanged
  — only add the new selection/inspector/timeline layer alongside it.
- **New `tests/test_tts_shell_browser.py`** (mirror `tests/test_learning_shell_browser.py`
  and `tests/test_new_shell_resize_browser.py`'s patterns exactly — same live-server
  fixture, same route-mocking approach):
  1. Shell resizes/collapses correctly (sidebar + inspector + timeline height drag).
  2. Selecting a line shows its detail in the inspector; Listen button calls the real
     `POST .../tts/preview` endpoint (assert on the mocked call, like
     `test_script_inspector_listen_calls_existing_preview_endpoint_and_exposes_audio`).
  3. Regression: per-speaker slider autosave still fires the real `PATCH .../speakers/
     {id}` call unchanged; "Generate All" still fires preview-per-line then
     `generateAudio` in the existing order.
  4. **Explicitly verify `StepNav.render()` includes `variant: "workflow"`** (e.g. assert
     `#pane-sidebar #step-nav .step-nav-workflow` exists) — Task 4.2a's exact regression,
     catch it here before it ships, not after.

## Allowed files
- `frontend/pages/step4_tts.html`
- `frontend/static/js/step4_tts.js`
- `tests/test_tts_shell_browser.py` (new)
- **`tests/test_step_nav_browser.py` — narrow, pre-authorized fix (PM decision,
  2026-09-15, in response to Codex correctly flagging this exact conflict before
  writing any code):** update line ~120's `if current_step in (2, 3):` to
  `if current_step in (2, 3, 4):` (and its adjoining comment) — the same one-line class
  of fix PM made directly for Task 4.2a's `current_step == 3` case, now pre-approved for
  Codex to apply itself since it's already correctly diagnosed and mechanically
  identical. **Scope is that one branch condition only** — no other change to this file.
- Do **not** touch `app/` (zero API/schema change), `shell.js`, or any other page's
  files. If a real bug is found in any *other* shared file (`style.css`, `shell.js`,
  `step_nav.js`, or any test file not listed above) while implementing, **report it to
  PM, do not fix it silently**.
- State-tracking files (`.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`,
  `.viepilot/HANDOFF.json`, `.viepilot/phases/04-post-beta-polish/PHASE-STATE.md`,
  `CHANGELOG.md`) are updated by **PM only**, after acceptance — Codex does not touch
  these per AR-06.

## Verification (paste real command output in the handoff, not a description)
- `venv\Scripts\python -m pytest tests/ -q` — 100% pass, full suite (not just the new
  file) — paste real output.
- `venv\Scripts\python -m ruff check app/ tests/` — clean, paste real output.
- `node --check frontend/static/js/step4_tts.js` — clean, paste real output.
- `git diff --check` — clean, paste real output.
- Real Playwright screenshot at 1440×900 (both empty state and populated state) —
  attach or describe exactly what's shown, matching Task 4.2a's own bar.

## Implementer Evidence (Awaiting PM Acceptance)

### Implementation summary

- `frontend/pages/step4_tts.html`: migrated `/step4` to the shared resizable shell with
  workflow sidebar, TTS stage, inspector, and Script/Voice/Music timeline. Existing
  workspace controls and selector IDs remain in place.
- `frontend/static/js/step4_tts.js`: added first-line default selection, synchronized
  stage/timeline selection, a read-only line inspector, the existing preview endpoint
  behind Inspector Listen, a real scroll/focus Voice settings affordance, and honest
  current-browser-session preview states. The existing speaker debounce/PATCH functions
  and sequential preview-all-then-mix request order remain intact.
- `tests/test_tts_shell_browser.py`: 5 browser tests cover shell resizing/collapse,
  workflow variant, all three tracks, selection/inspector sync, Listen success/error,
  session-state reset on reload, serialized trailing speaker autosave, and Generate All
  request order.
- `tests/test_step_nav_browser.py`: applied only the PM-authorized `(2, 3)` → `(2, 3,
  4)` branch change and adjoining comment.
- One real implementation defect was caught by the first targeted run: the selection
  updater initially matched every descendant carrying `data-line-id`, so it added
  `.selected` to the line's preview button and audio element as well as its card. The
  selector was narrowed to `.line-card[data-line-id]`; the new suite then passed 5/5.

### Browser verification

- Targeted new suite: `5 passed in 113.30s (0:01:53)`.
- Existing Step 4 browser coverage plus the StepNav step-4 and responsive-1024 cases:
  `10 passed in 219.61s (0:03:39)`.
- Real Playwright screenshots were captured and inspected at exactly 1440×900 (temporary
  evidence files outside the repository):
  - Populated: light shell rendered with the workflow sidebar, two speaker cards, first
    line selected in the stage, matching Line 1 inspector with `Not previewed`, and
    populated Script/Voice plus honest `No music selected` Music tracks.
  - Empty: the same three-pane shell remained stable, the stage showed the no-script
    guidance, the inspector showed its selection prompt, Script/Voice lanes were empty,
    and Music showed `No music selected`.

### Required verification output

`venv\Scripts\python -m pytest tests/ -q` (exit code 0):

```text
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 53%]
........................................................................ [ 66%]
........................................................................ [ 79%]
........................................................................ [ 93%]
.....................................                                    [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
541 passed, 2 warnings in 544.83s (0:09:04)
```

`venv\Scripts\python -m ruff check app/ tests/` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/step4_tts.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/04-post-beta-polish/tasks/task-4.2b.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step4_tts.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step4_tts.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_step_nav_browser.py', LF will be replaced by CRLF the next time Git touches it
```

The messages above are Git's existing Windows line-ending conversion notices; the
command returned 0 and reported no whitespace errors.

## PM Review (2026-09-16) — CHANGES REQUESTED, 1 real bug found

PM independently re-ran every verification command and read the full diff before
touching anything else, per AR-06.

**Re-verified, all matched Codex's report:**
- `node --check frontend/static/js/step4_tts.js` — clean.
- `venv\Scripts\python -m ruff check app/ tests/` — clean.
- `git diff --check` — exit 0, same LF/CRLF-only warnings, no real whitespace issues.
- Full suite: **540 passed, 1 failed** —
  `test_script_service.py::test_generate_script_exhausts_one_model_then_falls_back_to_next`,
  the project's pre-existing, TRACKER-documented Gemini-retry timing flake (unrelated
  module, took 1065.73s — well above the ~250-450s baseline). Confirmed non-regressive:
  passes instantly (0.62s) in isolation. This is the same flake class, not a new one —
  does not block acceptance.
- Diff read in full for both `frontend/pages/step4_tts.html` and
  `frontend/static/js/step4_tts.js`: shell structure, IDs, autosave/Generate-All
  preservation, `variant: "workflow"`, and the `test_step_nav_browser.py` fix all match
  the approved plan exactly. `.spinner`/`@keyframes spin` CSS removal confirmed safe —
  grepped the pre-Codex version of the file, that class was already dead/unused before
  this change. New `tests/test_tts_shell_browser.py` (5 tests) is genuinely thorough:
  notably `test_inspector_listen_calls_preview_and_reload_resets_session_state`
  actually reloads the page and asserts preview state resets to `not-previewed`,
  proving the "honest, session-only, not persisted" design claim for real rather than
  just describing it.

**Real bug found via independent screenshot (not caught by the test suite or the
Implementer's own described screenshots):** `renderTimeline()` calls
`scriptLane.replaceChildren()` and `voiceLane.replaceChildren()` before repopulating
those two lanes, but **never calls `musicLane.replaceChildren()`** before
`musicLane.appendChild(musicClip)`. Since `renderTimeline()` runs on every selection
change, preview-state transition, and music-selector change, the Music track
accumulates one stale duplicate clip per call instead of ever clearing old ones.
Reproduced live: a fresh page load + one line-selection click already showed **2**
"No music selected" badges stacked in the Music lane instead of 1. Not caught by
`tests/test_tts_shell_browser.py` because its Music-track assertions only check
substring presence (`"focus-bed.mp3" in ... .text_content()`), never element count.

**Requested fix (same file, same allowed_files scope — no new file access needed):**
add `musicLane.replaceChildren();` in `renderTimeline()` right before the `musicClip`
creation block (mirroring the pattern already used for `scriptLane`/`voiceLane`).
Please also add one assertion to the existing test suite (e.g. in
`test_tts_shell_resizes_collapses_and_syncs_three_track_selection`, after the
line-selection interactions already in that test) asserting
`await page.locator("#music-timeline .timeline-clip, #music-timeline
.timeline-placeholder").count() == 1` — so this can't silently regress again.

**Not requesting a change, disclosed for awareness only:** `previewLine()` accepts
`button`/`audio` DOM element references from either the line-list card or the
inspector's Listen button. If a user clicks Listen on line A, then selects line B
before A's preview resolves, `renderInspector()` fully replaces the inspector's
DOM (including a new button/audio for B), leaving A's in-flight closure holding
references to now-detached nodes — harmless (no crash, just a silently-discarded
update on an invisible node) and not a regression: the original pre-Codex
`previewLine(lineId, button, audio)` signature already had this same shape for the
line-list case. Not blocking, just noting it exists in case a future task wants to
harden this to a pure state-driven re-render like Script's `handleListen` pattern.

**Verdict: do not mark this task `done`.** One targeted fix + one test assertion
needed, everything else is accepted as-is. Re-review will be fast once the fix lands —
no need to re-plan or re-verify anything beyond the Music-track fix and its new
assertion.

## Implementer Fix Evidence (Awaiting PM Re-review — 2026-09-16)

- Added `musicLane.replaceChildren();` immediately before the Music clip creation block
  in `renderTimeline()`; Script, Voice, and Music lanes now all replace their contents
  before repopulating.
- Added the requested regression assertion after line-selection and music-selection
  rerenders: `#music-timeline .timeline-clip` count must remain exactly `1`.
- Did not change the pre-existing Listen/change-line race disclosed by PM, per the
  explicit non-blocking/no-change instruction.
- Did not rerun the full suite because PM explicitly limited re-verification to this
  Music-track fix and its assertion.

`venv\Scripts\python -m pytest tests/test_tts_shell_browser.py::test_tts_shell_resizes_collapses_and_syncs_three_track_selection -q` (exit code 0):

```text
.                                                                        [100%]
1 passed in 5.95s
```

`venv\Scripts\python -m ruff check tests/test_tts_shell_browser.py` (exit code 0):

```text
All checks passed!
```

`node --check frontend/static/js/step4_tts.js` (exit code 0):

```text
(no stdout or stderr)
```

`git diff --check` (exit code 0):

```text
warning: in the working copy of '.viepilot/phases/04-post-beta-polish/tasks/task-4.2b.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/pages/step4_tts.html', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/step4_tts.js', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_step_nav_browser.py', LF will be replaced by CRLF the next time Git touches it
```

The warnings are the same Windows line-ending notices reviewed previously; no
whitespace error was reported.

## PM Re-review (2026-09-16) — ACCEPTED

Independently re-verified the fix rather than trusting the report, per AR-06:

- Confirmed `musicLane.replaceChildren();` is correctly placed immediately before the
  Music clip creation block in `renderTimeline()` — exact fix requested.
- Confirmed the new test assertion (`#music-timeline .timeline-clip` count `== 1`) is
  present and placed after real prior interactions in the same test (not a fresh-page
  check that would miss a re-render bug).
- Re-ran `tests/test_tts_shell_browser.py` independently: **5/5 pass**.
- **Stress-tested beyond the single assertion**: wrote a disposable script that clicks
  through 5 consecutive selection/music changes (well past the 1-2 interactions the bug
  needed to reproduce originally) against a real running instance of the app, then
  asserted and screenshotted the Music lane. Real result: exactly 1 clip
  (`"focus-bed.mp3"`), confirmed both by DOM count and by looking at the actual
  rendered screenshot. Bug is genuinely fixed, not just no-longer-triggered by the one
  scripted test.
- Re-ran `node --check`, `ruff check app/ tests/`, and `git diff --check` independently
  — all clean, matching the Implementer's report exactly.
- Ran the **full suite** myself (Codex correctly deferred this per PM's explicit
  scope-limiting instruction): **541 passed, 0 failed, 237.33s** — clean, no flakes this
  run (the full 541 includes the previously-flaky
  `test_generate_script_exhausts_one_model_then_falls_back_to_next`, which passed
  normally here).
- Confirmed the previously-disclosed non-blocking Listen/change-line race was correctly
  left untouched, per instruction.

**This closes Task 4.2b.** All of Task 4.2's shell/timeline/inspector conventions now
apply to Script, Learning, and TTS (3 of 7 pages). Remaining: Video, Thumbnail,
YouTube, Music Library, Step1-Config.
