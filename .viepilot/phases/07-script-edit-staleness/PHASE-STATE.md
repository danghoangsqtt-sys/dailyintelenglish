# Phase 7 State — Script Edit Staleness

## Metadata
- **Phase:** 7
- **Slug:** 07-script-edit-staleness
- **Status:** in_progress
- **Started:** 2026-09-17
- **Milestone Progress:** 0 / 1 task done. Scoped after `/vp-audit` (2026-09-17)
  independently re-verified the 4 Gemini audit findings left unscoped after Phase 6
  closed. Confirms BUG-013 as real and more serious than the original audit claim:
  `POST /{project_id}/script/generate` and `/script/regenerate`
  (`app/api/projects.py`) carry **no status guard at all** — a user can edit the
  script after audio/video are already generated, with nothing invalidating the now-
  stale downstream artifacts or signaling this to the user. ENH-004 (single DB
  connection) and ENH-005 (CSS fragmentation) remain logged in
  `.viepilot/requests/` but out of scope for this phase per user decision — low risk
  for a solo local-use app, consistent with the project's standing precedent for
  deferring larger architectural/cosmetic changes.
- **Test Suite Status:** 583/583 pass (2026-09-17, unchanged since Phase 6 close) —
  see TRACKER.md

---

## Tasks Status & Acceptance Evidence

### Task 7.1: Downgrade project status + surface staleness signal on script edit — planned
- **Status:** planned
- See `tasks/task-7.1.md` for the doc-first plan.
