# Task 4.2c: UI Redesign Slice 2 — Video Studio page (`/step5`)

## Meta
- **ID**: 4.2c (third sub-task of Task 4.2 — UI Redesign Slice 2, split per-page per
  the 2026-09-15 brainstorm session's explicit pacing decision)
- **Phase**: 4
- **Status**: in_progress
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
