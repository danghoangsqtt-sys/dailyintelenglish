# Task 4.2b: UI Redesign Slice 2 — TTS Audio Studio page (`/step4`)

## Meta
- **ID**: 4.2b (second sub-task of Task 4.2 — UI Redesign Slice 2, split per-page per
  the 2026-09-15 brainstorm session's explicit pacing decision)
- **Phase**: 4
- **Status**: in_progress
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
- Do **not** touch `app/` (zero API/schema change), `shell.js`, or any other page's
  files. If a real bug is found in a shared file (`style.css`, `shell.js`,
  `step_nav.js`) while implementing, **report it to PM, do not fix it silently** — same
  rule as Task 4.2a's own `test_step_nav_browser.py` fix, which PM made directly, not
  Codex.
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

## PM Acceptance
_Pending — filled in by PM (Claude Code) after independently re-running every
verification command above and reading the full diff, per AR-06. Do not mark this task
`done` — that is PM's decision alone._
