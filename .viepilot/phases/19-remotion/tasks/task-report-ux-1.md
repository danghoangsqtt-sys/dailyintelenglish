# Task Report-UX-1 — Elapsed counter + ETA + Step 4/5 progress parity

- **Status:** not started (doc-first card, awaiting Coder pickup after 19.4)
- **Owner:** Coder
- **Priority:** P0 (report-readiness for T6 2026-10-02; makes AI-speed story tangible to
  live judges — backend is fast, UX makes it *feel* fast)
- **Dependency:** Task 19.4 accepted (2026-09-28); dev-server-live verification with owner
  confirmed Step 2/3 already have stage + % (screenshot 2026-09-28 15:xx)
- **Controlling context:** owner report deadline 2026-10-02; scope pivot from full Phase 19
  to AI-speed-focused deliverables (see PM/owner exchange 2026-09-28)
- **Not part of Phase 19 numbering:** this is a report-readiness task that borrows the
  Phase 19 folder for admin convenience; Phase 19 tasks 19.5/19.6/19.7 remain parked for
  post-report continuation

## Goal

When a user (specifically: a live judging panel at owner's T6 demo) clicks a Generate
button, they see:
1. An elapsed time counter that ticks every second (`0:14`), so they know progress is
   happening even during backend-quiet moments.
2. An ETA hint drawn from a real baseline (Gate B-11 median), so they know approximately
   how much longer to wait.
3. On Step 4 TTS/mix: a real % (not just "line 3/12" text), matching Step 2/3's polish.
4. On Step 5 video: at least an elapsed counter (render is <1s so % and ETA are moot).

**Not in scope** (deferred to post-report):
- Vietnamese label translation for stage names (`outline`, `section_1`, …) — Phase 4.3 UI
  localization was dropped 2026-09-16, staying consistent.
- Making the existing Cancel button actually cancel (backend cancellation is deferred per
  Phase 2.2 audit — architectural change).
- Fake progress bars where no real signal exists.

## Real starting state (verified live 2026-09-28)

- **Step 2 Script:** already renders `Generating script — outline (5%) [Cancel]` with a
  spinner, populated from real `ai_generation_jobs.stage/progress` via
  `app/services/script_pipeline.py::_update_progress` (fires `outline 5%`, then
  `section_{idx} 10+round(80*position/total)%` per section, up through completion).
- **Step 3 Learning:** same pattern, `step3_learning.js` reads `job.stage` + `job.progress`.
- **Step 4 TTS:** `step4_tts.js:493-517` renders progress text: `"Synthesizing line ${i+1}/
  ${state.lines.length}…"`, then `"Mixing final audio…"`, then `"Done…"`. No %, no
  elapsed, no ETA. The `i+1/N` data is client-side — the polling loop already knows both
  numbers.
- **Step 5 Video:** `step5_video.js:406-414` renders `"Rendering with ffmpeg…"` then
  `"Done."`. Nothing else. Real render is well under a second on the demo episode; elapsed
  counter is the only meaningful addition.

## Allowed files

- **New** `frontend/static/js/generation_status.js` — shared component
  `GenerationStatus.mount({ element, baselineSec })` and `GenerationStatus.setProgress(
  { stageLabel, progressPercent, done })`. Owns the elapsed timer (client-side
  `Date.now()` diff, requestAnimationFrame-throttled to per-second update) and the ETA
  formula (`Math.max(0, baseline - elapsed)` when elapsed < baseline, else "wrapping up"
  or similar honest-late label — do NOT project past the baseline as "-15s"). Same
  same-shape pattern as `StepNav`/`SaveIndicator`/`KeyboardShortcuts`.
- **Modify** `frontend/static/js/step2_script.js` — mount `GenerationStatus` on the
  existing spinner banner; when polling the job, forward `stage` + `progress` +
  `done`. Baseline: 45 seconds (Gate B-11 median for B1 8-min script).
- **Modify** `frontend/static/js/step3_learning.js` — same pattern; baseline: 30 seconds
  (Gate B-11 learning stage estimate).
- **Modify** `frontend/static/js/step4_tts.js` — compute `progressPercent = round(100 *
  (i+1) / N)` when synthesizing, `95` when mixing (mix is <10% of total time historically),
  `100` when done. Mount `GenerationStatus`. Baseline: `N * 5 + 15` seconds (5s per line
  synthesis + 15s mix — empirical, refine if better data exists in `audio_jobs.duration_seconds`).
- **Modify** `frontend/static/js/step5_video.js` — mount `GenerationStatus` with baseline
  1 second (real ffmpeg render measurement, see `docs/operations/phase19-spike-remotion.md`
  and `audio_service` timing history). Since render is <1s, ETA is trivially "just now";
  the elapsed counter is the honest signal that anything is happening at all.
- **New** `tests/test_generation_status_browser.py` — 1 Playwright test per step page
  (4 total) that mocks the appropriate API endpoint(s), triggers the Generate action,
  asserts the elapsed counter increments (wait 2s, check counter shows >=2), asserts the
  final-done state (counter freezes on last elapsed value or hides — pick one in the
  design, spec explicitly).
- **Modify** `CHANGELOG.md` — one `[Unreleased]` bullet under a new
  `### Added (Report-readiness UX)` sub-section.
- **Modify** `.viepilot/phases/19-remotion/PHASE-STATE.md` — new evidence log entry for
  Report-UX-1 alongside 19.1-19.4 entries; do NOT touch the 19.5/19.6/19.7/19.8/19.9 rows
  in the task-status table (they stay `provisional (parked)`).

**Not allowed:** any file under `app/api/`, `app/services/`, `app/db/`, `app/core/` —
this is a **frontend-only** task by design; every field the frontend needs is already
in the backend response. If a real gap surfaces mid-implementation (e.g. Step 4 status
response doesn't actually expose `current_line_index`), stop and flag as an explicit
scope question to PM, don't silently touch backend files. `data/app.db` stays `mode=ro`
from the Coder side (backend not touched at all is even stronger — trivially satisfied).

## Design decisions (Coder, doc-first — commit these under `docs(review)` before code)

### DRUX-a: Elapsed counter contract

- Ticks how often (recommend: every 1s, `setInterval(fn, 1000)` — sub-second is noise).
- Displayed format (recommend: `M:SS`, e.g. `0:14`, `1:23`, `2:07`; not `14s` for
  >60s cases).
- Starts when (recommend: on `GenerationStatus.mount` firing — same instant Generate is
  clicked; matches user intuition, avoids RTT skew).
- Stops when (recommend: on `done: true` signal; freezes the final value visibly for
  ~2s then hides, so the user sees the total time before it disappears).

### DRUX-b: ETA formula + honest-late behaviour

- Formula recommend: `remaining = max(0, baseline - elapsed)` in seconds, formatted
  `~Xs còn lại` (or the existing EN copy pattern already in use — check
  `step2_script.js`'s current text and match its language).
- When `elapsed >= baseline` (running over): do NOT show a negative number. Options:
  - (i) Hide ETA, keep elapsed counter running.
  - (ii) Show a "sắp xong…" or "wrapping up…" honest-late label.
  - Recommend (ii) — reassures the user progress is real, honest that we don't know how
    much longer.
- The baseline is a hardcoded constant per page (script 45s, learning 30s, TTS
  `N*5+15`, video 1s). Not read from the backend. If real cloud latency turns out
  materially different at demo time, this is a knob PM can tune with one integer edit
  per page — cheap.

### DRUX-c: Where the counter sits visually

- Existing spinner banner (Step 2/3): `Generating script — outline (5%) [Cancel]`.
  Insert elapsed + ETA between the % and Cancel button, or after Cancel — pick one
  based on real screenshot inspection, cite the specific position. Recommend after the
  `%`, before `Cancel`, so the reading flow is
  `Generating script — outline (5%) · 0:14 · ~30s còn lại [Cancel]`.
- Step 4 (currently just text): same shape once `GenerationStatus` mounts.
- Step 5 (currently just "Rendering…"): same shape with only elapsed (no % / ETA).

### DRUX-d: Test-mock strategy

- Playwright tests must not hit real Gemini/OpenRouter/Ollama. Mock the
  polling endpoint to return `{status: "running", stage: "section_1", progress: 42}`,
  then after some frames, `{status: "complete", ...}`. Use the same network-mock
  pattern the existing browser tests use (grep `route.fulfill` in `tests/test_*_browser.py`
  for the current pattern; do NOT invent a new mocking style).
- The elapsed-counter increment test uses Playwright's real time (wait ~2s, assert
  counter text matches `/0:0[2-3]/`), NOT the mocked-time approach — the whole point of
  the counter is that it advances against real wall clock.

### DRUX-e: Fallback if a field is missing

- If `job.stage` is `null` (older jobs, race condition on first poll): show only
  elapsed + ETA, hide the stage label, don't crash.
- If `job.progress` is `null`: same — show only elapsed + ETA + stage label.
- Backend contract confirmation: after implementation, run one live generation against
  the currently-running dev server (port 8000, PM launched it) and confirm the fields
  populate as expected. Include one screenshot of the real running-state banner in the
  handover.

## Verification

- 4 new Playwright tests pass (one per Step page).
- Full suite **1182+/1182+** (1178 baseline + 4 new). `ruff check .` still clean —
  though this task should touch no Python, so ruff is trivially satisfied.
- **Revert-and-confirm-failure** on 1 of the 4 tests (recommend Step 2 — highest-value
  path): revert the `GenerationStatus.mount` call, re-run test, confirm counter check
  fails (either counter absent or stays at `0:00`). Restore. Confirm green.
- One live-generation screenshot against the dev server (owner's real dev instance on
  port 8000) showing the full banner: `Generating script — outline (5%) · 0:14 · ~30s
  còn lại [Cancel]`.
- `git diff` shows zero changes under `app/` (frontend-only task).

## Evidence (Coder handover)

- Two shas (design + implementation).
- Full-suite + ruff + browser-test lines.
- Which of DRUX-b (i)/(ii) chosen for honest-late.
- The real live-generation screenshot filename in the handover message.
- Any deviation from the recommended baseline constants (with real numbers if changed).

## Definition of done

- Two commits, design **before** implementation.
- All 4 Step pages show elapsed + ETA (where meaningful) + real % (Step 4 gained).
- Live-verified against a real generation on the dev server, screenshot attached.
- Full suite green. `app/` untouched.
- Handover per Evidence checklist.
