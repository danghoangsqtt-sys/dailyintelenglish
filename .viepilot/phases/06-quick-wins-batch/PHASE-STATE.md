# Phase 6 State — Quick Wins Batch

## Metadata
- **Phase:** 6
- **Slug:** 06-quick-wins-batch
- **Status:** in_progress
- **Started:** 2026-09-17
- **Milestone Progress:** 0 / 1 task done. New phase, scoped in the 2026-09-17
  brainstorm session (`docs/brainstorm/session-2026-09-17.md`) after Phase 5 formally
  closed. Addresses 3 real, independently-verified findings from a user-commissioned
  deep-dive Gemini audit (`C:\Users\Admin\Documents\audit_chuyensau_dailyintelenglish`)
  — theme flash on 4 pages, a dead-end "Missing project" error with no way back to the
  Dashboard, and default (non-accent-colored) TTS range sliders. A 4th audit claim
  (YouTube chapters always using an estimated timestamp) was independently traced and
  found to be a **false positive** — the real-measurement code path already exists and
  is already wired up correctly — so it is explicitly excluded from this phase.
  Several deeper architectural findings from the same audit (single-connection DB
  lock, unused Gemini rate-limiter constant, forward-only project status machine,
  inline CSS fragmentation) remain explicitly deferred, consistent with this
  project's established precedent for Progress cancellation and real LivePortrait
  lip-sync.
- **Test Suite Status:** 571/571 pass (2026-09-17, end of Phase 5) — see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 6.1: Theme flash + dead-end error link + range slider styling — 🔄 IN PROGRESS
- **Status:** in_progress (2026-09-17)
- Three independent, low-risk, PM-verified fixes bundled per the precedent set by
  Task 2.3/4.4/5.3: (1) remove the hardcoded `data-theme="dark"` from 4 pages'
  `<html>` tag so `theme.js`'s already-correct light-default logic applies before
  first paint instead of after; (2) a new, narrowly-scoped
  `showMissingProjectError()`-style function on each of the 6 pipeline pages (step2-7)
  renders a real "Go to Dashboard" link for the one specific "no project_id" error
  state, without changing the existing `showError()` contract for any other message;
  (3) CSS-only `accent-color` styling for the TTS speed/pitch/volume range sliders,
  no new JS state. Handed to Codex as Implementer per AR-06. See `tasks/task-6.1.md`
  for the full plan.
