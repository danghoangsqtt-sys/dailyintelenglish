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

## Design decisions — Coder answers (2026-09-28)

**Real finding that changes the implementation shape (read this before DRUX-a):**
`step2_script.js`/`step3_learning.js`'s `renderJobStatus(job)` currently does
`el.innerHTML = "...full banner string..."` **on every poll tick** (every 2s, via
`AiJob.run`'s `onStateChange`, confirmed in `ai_job.js:57`). If `GenerationStatus`'s markup
is inserted into that same string (the card's literal "insert between % and Cancel"), the
counter's DOM node gets destroyed and recreated every 2 seconds -- an elapsed timer built on
a `setInterval` closure tied to that node would either leak (orphaned intervals) or, if
correctly cleaned up, **visibly reset to `0:00` every 2 seconds** in front of the judging
panel. `GenerationStatus.mount()` is therefore called **once**, the first time a job becomes
active/non-terminal (not on every `onStateChange`); after that, only
`GenerationStatus.setProgress({stageLabel, progressPercent, done})` is called on each poll,
which updates existing DOM nodes' `textContent` directly -- no `innerHTML` replacement, no
timer disruption. `renderJobStatus` is restructured accordingly (still the same function,
same call sites, same `AiJob` integration -- just an `if (!generationStatus)` guard around
the one-time markup build). Step 4/5 don't have this problem (no poll loop, no repeated
`innerHTML` replacement of the same container), so `mount()` there is a plain one-time call
at the start of `generateAll()`/`generateVideo()`.

### DRUX-a: Elapsed counter contract

- Ticks every 1s (`setInterval`, matches the card's recommendation).
- Format `M:SS` (`0:14`, `1:23`).
- **Starts from `job.started_at` when available, not always `Date.now()` at mount time.**
  Real finding: `ai_generation_jobs.started_at` (`app/db/migrations/006_ai_generation_jobs.sql`)
  is a real column already returned by the job-status endpoint (confirmed in the existing
  browser test's own job fixture, `test_script_jobs_browser.py`'s `_job()`:
  `"started_at": "2026-01-01T00:00:00Z"`). If `GenerationStatus.mount()` always started from
  "now," a page refresh mid-generation (`AiJob.resume()`, already-tested behaviour --
  `test_refresh_resumes_an_active_job_instead_of_showing_empty_state`) would incorrectly
  reset the visible elapsed time to `0:00` even though the job has genuinely been running for
  a while. `mount({element, baselineSec, startedAtIso})` accepts an optional real timestamp;
  `startedAtIso ?? Date.now()` -- Step 2/3 pass `job.started_at` (present on both fresh-create
  and resumed jobs), Step 4/5 have no durable job or resume case, so they omit it (defaults
  to `Date.now()`, correct for their single-page-load lifecycle).
- **Stops when `done: true`, but the freeze-then-hide duration differs by page, and this is
  a deliberate asymmetry, not an oversight:**
  - **Step 4/5:** freeze the final elapsed value, matching `SaveIndicator`'s own
    "show final state, no artificial extra hide timer needed" shape -- these pages already
    leave `#generate-progress`'s final text ("Done — episode ready below.", "Done.") visibly
    on screen after completion (confirmed in `step4_tts.js:513`, `step5_video.js:410`), so
    the frozen elapsed counter sits right next to that existing, permanent "Done" text with
    no extra hide logic needed at all.
  - **Step 2/3: no artificial 2s freeze-then-hide.** Real tension worth flagging explicitly
    rather than silently applying the card's generic recommendation: today, completion
    (`currentAiJob.promise` resolving) immediately calls `renderJobStatus(null)` and reveals
    the finished script (`watchScriptAiJob`'s `.then()`, `step2_script.js:73-76`) -- snappy,
    no pause. Inserting an artificial "freeze the counter for 2s before hiding" delay would
    directly fight this task's own purpose: the report's message is "the backend is fast,"
    and adding a manufactured 2-second pause right before the fastest, most satisfying moment
    (finished script appearing) undercuts that in front of the exact audience this task
    exists for. **Recommendation: keep today's immediate reveal for Step 2/3** --
    `generationStatus.destroy()` + `renderJobStatus(null)` fire together, no delay. The
    elapsed counter's job was to reassure the user *during* the wait; once the wait is over
    and the result is already on screen, there's nothing left for it to reassure about.

### DRUX-b: ETA formula + honest-late behaviour

- `remaining = Math.max(0, baselineSec - elapsedSec)`, displayed `~Xs left` while
  `elapsed < baseline`.
- **Chosen: (ii) "wrapping up…" label when running over** -- matches the card's own
  recommendation and reasoning (reassures progress is real without projecting a false
  negative number).
- **Language: English throughout, not the card's Vietnamese phrase suggestions
  ("còn lại"/"sắp xong").** Real finding: every existing piece of UI copy in this app is
  English (`Generating script`, `Cancel`, `Mixing final audio…`, `Rendering with ffmpeg…`,
  the terminal messages) -- confirmed by reading every string touched in this task's own
  allowed files. Phase 4.3 UI localization was dropped 2026-09-16 (cited by the card's own
  "not in scope" section); introducing Vietnamese strings in exactly one new component would
  contradict that standing decision, not follow it. `~14s left` / `wrapping up…` in English.
- Baseline constants exactly as the card specifies (script 45s, learning 30s, TTS `N*5+15`,
  video 1s) -- not re-derived from any backend field, per the card's own instruction.

### DRUX-c: Where the counter sits visually

- Step 2/3: `Generating script — outline (5%) · 0:14 · ~30s left [Cancel]` -- exactly the
  card's recommended position (after `%`, before `Cancel`), using `·` as the same visual
  separator style already implied by the existing banner's spacing. Implemented via the
  one-time-mount restructuring above, not a literal string splice on every render.
- Step 4: `Synthesizing line 3/12… (25%) · 0:08 · ~52s left` -- same shape, replacing the
  current bare `Synthesizing line ${i+1}/${N}…` text. During the `"Mixing final audio…"` and
  `"Done…"` phases, `progressPercent` is `95` then `100` per the card's spec.
- Step 5: `Rendering with ffmpeg… · 0:01` -- elapsed only, no `%`/ETA suffix at all (not even
  a `~1s left` -- with a 1-second baseline, an ETA string would flicker between "left" and
  "wrapping up" within the same second and add visual noise for zero information value).

### DRUX-d: Test-mock strategy

- Same `page.route("**/api/**", handle)` dispatcher pattern as
  `tests/test_script_jobs_browser.py`/`tests/test_tts_audio_browser.py` -- no new mocking
  style introduced.
- Step 2/3: mock the `ai-jobs` GET-poll endpoint to return `status: "running"` for the first
  ~2 real seconds (the natural 2000ms `AiJob` poll interval already provides this real-time
  gap for free -- no artificial delay needed in the route handler), then `"complete"`.
- Step 4/5 (no poll loop -- a single `await Api.previewTtsLine(...)` /
  `await Api.generateVideo(...)` per step): the mocked route handler itself
  `await asyncio.sleep(2.5)` before fulfilling, so the elapsed counter has real wall-clock
  time to tick past `0:02` before the operation "completes" client-side. This is the one
  place this task's tests hold a mocked response open on purpose, and it's called out here
  so it doesn't look like an accidental slow test.
- The counter-increment assertion itself uses Playwright's real clock (`page.wait_for_timeout`
  then a text-content regex `/0:0[2-3]/`), never Playwright's clock-mocking API -- the whole
  point is proving the counter advances against real wall time (matches the card's own
  instruction).

### DRUX-e: Fallback if a field is missing

- `job.stage == null`: `setProgress` renders no stage label, elapsed + ETA only.
- `job.progress == null`: same -- stage label (if present) + elapsed + ETA, no `(NaN%)`.
- Neither case throws -- `setProgress` checks each field independently, never assumes both
  arrive together.
- Backend contract will be confirmed live against the running dev server (port 8000) once
  implementation lands, per the card's own instruction; screenshot included in the handover.

## PM review — APPROVED (2026-09-28, session a01f96)

All four findings accepted verbatim: the DOM-lifecycle catch (finding 1) is recorded as a
real demo-blocker avoided; `started_at`-anchored elapsed (finding 2) confirmed as the honest
choice for the resume case; the asymmetric completion behaviour (finding 3) confirmed as the
right read of intent -- Step 2/3 get no artificial delay, Step 4/5 keep the freeze (their
"Done." text already persists, no reveal-swap moment to protect); English throughout
(finding 4) confirmed, Vietnamese phrasing in the card was PM error re Phase 4.3. No changes
requested.

One pre-implementation check requested and completed: confirmed `started_at` is a real
ISO-8601 string with UTC offset (`app/services/ai_job_service.py::_now_iso`, ==
`datetime.now(timezone.utc).isoformat()`), matching `AIJobOut.started_at: str | None` --
`new Date(job.started_at)` needs no adjustment. No design pivot.

Proceed to implementation.

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

## Implementation notes (2026-09-28)

**HTML script-tag gap, found and disclosed mid-implementation:** the design doc didn't
account for `generation_status.js` needing a `<script src="...">` tag on each of the 4 Step
pages to actually load -- none of the 4 `.html` files were in "Allowed files." Flagged to PM
immediately on discovery; PM pre-approved the one-line-per-file addition as the same
mechanical scope-extension class as 19.2's test-file fixes (no design change, load-order
plumbing only). Touched: `frontend/pages/step2_script.html`, `step3_learning.html`,
`step4_tts.html`, `step5_video.html` -- each gained exactly one
`<script src="/static/js/generation_status.js"></script>` line, positioned immediately before
that page's own script tag (matching every other shared component's existing convention).

**A real discovery from the revert-and-confirm-failure exercise itself, worth recording
honestly:** the first revert attempt removed only the `if (!generationStatus)` one-time-mount
guard (Finding 1's specific fix) while leaving the `startedAtIso: job.started_at` anchor
(Finding 2) in place -- and the test **still passed**. Investigated rather than declared
"good enough": because the elapsed calculation anchors to the job's real, fixed
`started_at` timestamp rather than `Date.now()` at mount time, re-mounting on every poll
recomputes the *same* correct growing elapsed value each time (redundant work + an
un-cleared `setInterval` leak, but not a visibly wrong counter) -- Finding 2's fix
incidentally also masks Finding 1's specific "resets to 0:00" symptom once both are
implemented together. The mount-once guard is still correct practice (avoids the interval
leak and unnecessary DOM churn), but the original design narrative overstated it as the sole
fix for the visible symptom. The revert test was redone properly -- reverting the *entire*
`GenerationStatus` integration for Step 2 (matching the card's literal instruction) -- and
that failed as expected (`TimeoutError` waiting for `.generation-status-elapsed`, i.e. the
"counter absent" case the card names). Restored and re-confirmed green.

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
