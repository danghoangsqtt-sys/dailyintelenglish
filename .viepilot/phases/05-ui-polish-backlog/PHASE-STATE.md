# Phase 5 State — UI Polish Backlog

## Metadata
- **Phase:** 5
- **Slug:** 05-ui-polish-backlog
- **Status:** in_progress
- **Started:** 2026-09-16
- **Milestone Progress:** 2 / 3 tasks done. New phase, scoped in the 2026-09-16
  brainstorm session (`docs/brainstorm/session-2026-09-16.md`) after Phase 4 formally
  closed. Addresses the real, still-current P1/P2 findings from the 2026-09-16 Codex
  UI audit — PM re-verified each finding against the current codebase before scoping
  (2 of the original 9 findings turned out to already be fixed as side effects of Task
  4.2d/4.2e's shell redesign work, not carried forward). Progress cancellation and
  real LivePortrait lip-sync remain explicitly deferred, not part of this phase; Task
  4.3 (Vietnamese UI localization) was dropped by explicit user decision, not part of
  this phase either.
- **Test Suite Status:** 569/569 pass (2026-09-17, after Task 5.2) — see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 5.1: Dashboard scale (pagination) — ✅ DONE (2026-09-17)
- **Status:** done
- Client-side pagination for the Dashboard's project grid, no backend change (the
  measured problem is unbounded DOM rendering — 176 real project cards / 358 buttons
  in one `innerHTML` pass, ~17,000px page height — not the data fetch, which already
  returns the full list in one small payload). Fixed page size of 24. The clamp logic
  lives centrally inside `render()` itself (recomputed on every call), so the delete
  handler needed zero changes to satisfy "clamp after delete" — a cleaner design than
  the explicit post-delete clamp the task card anticipated. Filter/search changes
  reset to page 1; pagination controls hidden entirely for a single page; no
  `localStorage`/reload persistence (session-only, by design). Implemented by Codex,
  accepted by PM per AR-06. 4 new browser tests using an isolated
  `_pagination_projects()` fixture — confirmed the pre-existing shared `MOCK_PROJECTS`
  constant and its 6 existing consumers were left completely untouched, per PM's
  explicit plan-review requirement. **Zero real defects found on PM review** — PM
  independently re-ran every verification command and read the full diff. 566/566
  full suite passes (up from 562; 6 known Gemini-retry timing flakes seen on PM's
  independent run, all confirmed passing instantly in isolation — non-regressive,
  Task 5.1 touched zero backend code). See `tasks/task-5.1.md` for the full record.

### Task 5.2: Timeline polish (proportional width + keyboard resizer) — ✅ DONE (2026-09-17)
- **Status:** done
- PM's research corrected the original audit's scope: Script's timeline has **no**
  timing data at all (never will, at that stage of the pipeline) and is explicitly
  excluded from the width change — only Video (already has real per-line timing via
  `timingForLine()`) and TTS (already calls `Api.getAudioStatus()`, just needed to
  store the result — a small state addition, not a new API call) get proportional
  clip width. Formula: 16px/second, clamped 72-240px, derived from 78 real timing
  samples (p90 5.97s, max 7.66s) — a 3s clip stays at the 72px floor, a 7s clip
  reaches 112px. Invalid/zero/negative/missing durations keep today's auto-width,
  never a guessed value. TTS additionally stores the job from **both**
  `Api.getAudioStatus()` and `Api.generateAudio()` — an endorsed addition beyond the
  original plan, so widths update immediately after a first Generate All instead of
  requiring a reload; PM independently verified both endpoints return the identical
  job shape with real `timestamps` before endorsing it. The shared shell's horizontal
  timeline resizer (`shell.js`) gained a keydown handler mirroring the existing
  vertical-resizer pattern exactly — fixes keyboard access on all 3 timeline pages at
  once since they share the same component. Implemented by Codex, accepted by PM per
  AR-06. 3 new/extended browser tests using real bounding-box width assertions (not
  style-attribute presence checks), including a full 4-step keyboard round-trip test.
  **Zero real defects found on PM review** — PM independently re-ran every
  verification command, read the full diff, and confirmed `step2_script.js` and
  `style.css` were genuinely untouched. 569/569 full suite passes. See
  `tasks/task-5.2.md` for the full record.

### Task 5.3: Small polish batch — 🔄 IN PROGRESS
- **Status:** in_progress (2026-09-17)
- Three independent, low-risk fixes, bundled per the brainstorm session's decision:
  (1) Learning's item cards gain `role="button"`/`tabindex="0"` + a keydown handler
  for `Enter`/`Space`, so a keyboard-only user can select them — they stay `<div>`s
  (not real `<button>`s) since they contain other interactive inline-edit children,
  which cannot legally nest inside a native button. (2) Learning's inspector
  auto-selects the first item of the active tab whenever nothing is selected (first
  load, first generate, or after switching tabs) — never overriding an existing
  selection. (3) Video's "Speaker avatars (optional)" section (not-yet-functional
  LivePortrait feature) moves into a native `<details>`/`<summary>`, collapsed by
  default, reusing the exact pattern already established for Script's language notes
  — no custom JS collapse widget needed. Handed to Codex as Implementer per AR-06.
  See `tasks/task-5.3.md` for the full plan.
