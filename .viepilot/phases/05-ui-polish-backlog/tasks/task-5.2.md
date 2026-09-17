# Task 5.2: Timeline polish — proportional clip width + keyboard resizer

## Meta
- **ID**: 5.2 (second task of Phase 5 — UI Polish Backlog)
- **Phase**: 5
- **Status**: in_progress (2026-09-17)
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
