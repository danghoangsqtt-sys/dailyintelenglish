# Phase 7 State — Script Edit Staleness

## Metadata
- **Phase:** 7
- **Slug:** 07-script-edit-staleness
- **Status:** complete
- **Started:** 2026-09-17
- **Closed:** 2026-09-18
- **Milestone Progress:** 1 / 1 task done. Scoped after `/vp-audit` (2026-09-17)
  independently re-verified the 4 Gemini audit findings left unscoped after Phase 6
  closed. Confirmed BUG-013 as real and more serious than the original audit claim:
  `POST /{project_id}/script/generate`, `/script/regenerate`, and
  `PUT /{project_id}/script` (`app/api/projects.py`) carried **no status guard at
  all** — a user could edit the script after audio/video were already generated,
  with nothing invalidating the now-stale downstream artifacts or signaling this to
  the user. ENH-004 (single DB connection) and ENH-005 (CSS fragmentation) remain
  logged in `.viepilot/requests/` but out of scope for this phase per user decision —
  low risk for a solo local-use app, consistent with the project's standing precedent
  for deferring larger architectural/cosmetic changes.
- **Test Suite Status:** 596/598 pass (2026-09-18, after Task 7.1) — 2 failures are
  the project's long-documented Gemini-retry/backoff timing flake class, confirmed
  passing instantly in isolation, unrelated to this task's files. See TRACKER.md.

---

## Tasks Status & Acceptance Evidence

### Task 7.1: Downgrade project status + surface staleness signal on script edit — ✅ DONE (2026-09-18)
- **Status:** done
- A new `project_service.mark_script_changed()` internal operation (no
  caller-selected target status) re-reads the live project status inside the
  existing write transaction and applies exactly the 4 rules the task card locked in:
  `draft -> script_generated` (via the existing validated path, unchanged),
  `script_generated` idempotent, and `audio_generated|video_generated|complete ->
  script_generated` via a narrow, status-and-`updated_at`-only direct update — no
  audio/video files or job records touched. Wired into all 3 real script-mutation
  call sites: full generation, single-line regeneration, and manual script save
  (`PUT /{project_id}/script` — the Step 2 UI's normal autosave path, correctly
  identified by Codex during plan review as sharing the same bug even though the
  original task card only named the two AI-driven endpoints). The public
  `PUT /{project_id}` endpoint and `_validate_status_transition` are byte-for-byte
  unchanged — confirmed via diff and a new end-to-end test that drives a project
  through all 4 real forward transitions before proving `complete -> draft` still
  returns 422. Implemented by Codex, accepted by PM per AR-06. **Zero real defects
  found on PM review** — PM independently re-ran every verification command, read
  the full diff for all 5 production/test files, and confirmed a disk-and-DB test
  proves real audio/video files and job rows survive the downgrade byte-for-byte
  unchanged. 596/598 full suite passes; the 2 failures are the known Gemini-retry
  flake class, confirmed non-regressive in isolation. See `tasks/task-7.1.md` for
  the full record, including Codex's honestly-reported mid-implementation discovery
  that a pre-existing write-lock regression suite called the renamed helper by name
  (resolved by preserving the legacy private helper's name/signature, not by
  touching the out-of-scope test file).

**This closes Phase 7 (Script Edit Staleness) in full**, since Task 7.1 was its only
task.
