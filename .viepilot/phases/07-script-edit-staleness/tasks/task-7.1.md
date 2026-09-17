# Task 7.1: Downgrade project status + surface staleness signal when script is edited after later steps exist

## Meta
- **ID**: 7.1 (first task of Phase 7 — Script Edit Staleness)
- **Phase**: 7
- **Status**: planned
- **Priority**: high (real data-integrity gap, confirmed via independent code trace)
- **Assignee**: Codex (Implementer) — PM (Claude Code) writes/accepts, per the AR-06
  PM-Implementer contract (`docs/CODEX_CODE_PROMPT.md`, `.viepilot/SYSTEM-RULES.md`)

## Doc-First Gate

Origin: `.viepilot/requests/BUG-013.md`, auto-logged by `/vp-audit` (2026-09-17) while
independently re-verifying a Gemini-authored external audit
(`C:\Users\Admin\Documents\audit_chuyensau_dailyintelenglish`) finding — "forward-only
project status machine with no downgrade/invalidation path." PM's own trace found the
real gap is worse than the audit's general description: it isn't just "no downgrade
path" — the script-edit endpoints have **no status check of any kind**.

## Current state (researched before writing this plan — do not re-derive from scratch)

`app/services/project_service.py::_validate_status_transition` (lines 45-59) enforces
a strict forward-only, one-step-at-a-time state machine
(`draft -> script_generated -> audio_generated -> video_generated -> complete`) —
confirmed correct and working for legitimate forward progress.

`app/api/projects.py`:
- `generate_script` (lines 213-223) and `regenerate_script_line` (lines 226-243) call
  `script_service.generate_script`/`regenerate_line` directly — **no read or check of
  `project["status"]` gates either call**.
- `_advance_to_script_generated` (lines 75-85) is called after every script
  save/regenerate via `_save_script_and_advance` (lines 88-97), but it only acts
  `if project["status"] == "draft"` — a no-op for every other status. It was written
  to move a fresh project from `draft` to `script_generated` on first generation; it
  was never extended to handle the case where a project's status is already past
  `script_generated`.
- Net effect, confirmed via reading both files directly (not inferred): a project at
  `audio_generated`, `video_generated`, or `complete` status can have its script fully
  regenerated or a single line edited via Gemini at any time, with **zero** signal to
  the user or the system that the already-generated audio/video (real files on disk,
  tied to the old script text) no longer match the current script.

`_validate_status_transition` itself would reject an arbitrary backward call (e.g.
`video_generated -> script_generated` fails the `new_index != current_index + 1`
check) — so a naive "just call update with status=script_generated unconditionally"
fix would raise `ValidationError` for exactly the cases that need fixing. Any fix must
either add a deliberate, narrow internal path for this one specific downgrade (audited
and never exposed via the public `PATCH` project endpoint), or extend the validator
with an explicit, intentional exception documented as such.

`frontend/static/js/dashboard.js`'s `STATUS_TO_STEP` map (lines 32-38) already maps
`script_generated` to step 2 — downgrading status to `script_generated` after an edit
would make the Dashboard's "Continue" button correctly resume at the script step
without any new frontend mapping needed. Step 4/5/6/7 pages already fetch their own
fresh generation-job status from their respective APIs on load (`state.audioJob`,
`state.videoReady`, etc.) rather than trusting `project.status` for in-page state, so
downgrading the project-level status does not require rewriting any step page's own
readiness logic.

## Objective

When a script is generated or a line regenerated on a project whose status is already
past `script_generated` (i.e. `audio_generated`, `video_generated`, or `complete`),
the project must be honestly signaled as having a stale downstream pipeline — at
minimum, its status must reflect that audio/video generated from the old script are no
longer guaranteed to match.

### Required decisions (already settled by PM, do not re-litigate)

1. **Non-destructive**: do **not** delete or overwrite the existing audio/video files
   or job records. The user may still want them, or may want to compare. This is a
   staleness *signal*, not a forced regeneration or garbage collection.
2. **Downgrade project status to `script_generated`** whenever `generate_script` or
   `regenerate_script_line` succeeds on a project whose current status is
   `audio_generated`, `video_generated`, or `complete`. This reuses the existing
   status/`STATUS_TO_STEP` mechanism (Dashboard "Continue" naturally resumes at the
   script step) instead of inventing a new concept. No status change when current
   status is already `draft` or `script_generated` (existing behavior for those two
   cases is correct and must not regress).
3. **Implementation must not weaken `_validate_status_transition`'s protection for the
   public API.** The public `PATCH /{project_id}` project-update endpoint must still
   reject any caller-supplied backward status transition exactly as it does today —
   this downgrade path is triggered only internally, from inside the script
   generate/regenerate flow, never from arbitrary user-supplied `status` input.
4. Do **not** invent a new UI staleness banner/warning as part of this task — the
   existing Dashboard status badge (`badge-status-${project.status}`) and "Continue"
   routing already give an honest, truthful signal once status correctly reflects
   reality. A dedicated in-app warning banner is a reasonable future enhancement but
   is not required to close this specific correctness gap and would expand scope
   beyond the audited finding.

## Proposed File-Level Plan

- `app/services/project_service.py`: add a narrow, explicit way to perform this one
  specific downgrade (e.g. a small dedicated function, or a documented internal
  parameter) without loosening `_validate_status_transition`'s guarantee for the
  public API. Codex to confirm the exact shape in the pre-code plan.
- `app/api/projects.py`: extend `_advance_to_script_generated` (or add a sibling
  helper called from `_save_script_and_advance`) to also handle the downgrade case,
  not just the `draft -> script_generated` advance case.
- New or extended backend test coverage proving: (a) generating/regenerating script on
  a `draft` project still correctly advances to `script_generated` (no regression),
  (b) generating/regenerating script on a project already at `audio_generated` /
  `video_generated` / `complete` correctly downgrades its status to
  `script_generated`, (c) the public `PATCH /{project_id}` endpoint still rejects an
  arbitrary caller-supplied backward status transition exactly as before (no
  regression to the existing forward-only guarantee).

## Allowed files
- `app/services/project_service.py`
- `app/api/projects.py`
- Existing or new backend test file(s) — Codex to confirm exact filename(s) in the
  pre-code plan (likely alongside existing project/status tests).
- This task card, for plan/evidence updates.

## Verification checklist
- [ ] Script generate/regenerate on a `draft` project still advances status to
  `script_generated` exactly as today — no regression.
- [ ] Script generate/regenerate on a project at `audio_generated`, `video_generated`,
  or `complete` downgrades status to `script_generated`.
- [ ] No audio/video files, job records, or other project data are deleted or mutated
  by this change — downgrade is status-field-only.
- [ ] The public `PATCH /{project_id}` endpoint still rejects an arbitrary
  caller-supplied backward status transition (e.g. `complete -> draft` via direct
  PATCH) — the existing forward-only guarantee for user-facing input is unchanged.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `git diff --check` — all clean, real output pasted.

## PM Plan Review

(Pending — Codex to present pre-code plan per AR-06 before any implementation.)
