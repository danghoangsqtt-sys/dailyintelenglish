# Phase 9 State — Regeneration Integrity

## Metadata
- **Phase:** 9
- **Slug:** 09-regeneration-integrity
- **Status:** in_progress
- **Started:** 2026-09-18
- **Milestone Progress:** 0 / 1 task done. Opened after the user had Codex run its own
  independent, parallel read-only `/vp-audit` pass alongside PM's own audit. Codex
  found 10 issues (0 critical, 1 high, 4 medium, 5 low); PM independently
  re-verified all 5 of the "important" ones (1 high + 4 medium) by reading the actual
  source directly — all 5 confirmed real, no false positives. User chose to open this
  phase to fix the 2 most serious: BUG-017 (a failed audio/video regeneration attempt
  destroys the DB record of a still-valid previous success — real data loss from the
  DB's perspective) and BUG-016 (changing a speaker's voice settings doesn't
  invalidate downstream project status — the same bug class as BUG-013, already fixed
  for script edits under Task 7.1, just reached via a different mutation path PM's
  Task 7.1 scoping missed). BUG-018 (stale per-line audio cache after single-line
  regenerate), BUG-019 (avatar filesystem/DB rollback mismatch), and ENH-007
  (ARCHITECTURE.md diagram staleness) are logged in `.viepilot/requests/` but
  explicitly out of scope for this phase per user decision.
- **Test Suite Status:** 601/602 pass (2026-09-18, unchanged since Phase 8 close) —
  see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 9.1: Preserve prior job data on regeneration failure; downgrade status on voice-settings change — planned
- **Status:** planned
- See `tasks/task-9.1.md` for the doc-first plan.
