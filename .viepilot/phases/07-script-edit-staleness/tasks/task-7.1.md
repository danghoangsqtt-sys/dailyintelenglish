# Task 7.1: Downgrade project status + surface staleness signal when script is edited after later steps exist

## Meta
- **ID**: 7.1 (first task of Phase 7 — Script Edit Staleness)
- **Phase**: 7
- **Status**: done (2026-09-18)
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
- [ ] The public `PUT /{project_id}` endpoint (correction from PM's original
  `PATCH /{project_id}` — the real route is `PUT`, caught by Codex during plan review;
  `PATCH` only exists for nested speaker/thumbnail resources) still rejects an
  arbitrary caller-supplied backward status transition (e.g. `complete -> draft`) —
  the existing forward-only guarantee for user-facing input is unchanged.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class is the only acceptable non-deterministic failure, and only if it reproduces as
  a pass in isolation.
- [ ] `ruff check app/ tests/`, `git diff --check` — all clean, real output pasted.

## PM Plan Review

### Implementer Pre-Code Plan (Awaiting PM Confirmation)

**Target behavior**

- Add a dedicated internal service operation with no caller-supplied target status
  (proposed name: `mark_script_changed`). It will read the project's current status
  inside the existing connection-wide write transaction and apply only these rules:
  `draft -> script_generated`, `script_generated -> script_generated` (no-op), and
  `audio_generated|video_generated|complete -> script_generated`.
- The internal operation will issue a narrow `projects` update for `status` and
  `updated_at` only. It will not call artifact cleanup, delete or overwrite files, or
  update audio/video job rows.
- Leave `_validate_status_transition` and `update_project` unchanged. Therefore the
  public project-update endpoint continues to enforce the existing forward-only,
  exactly-one-step transition rule. The internal operation cannot be repurposed for an
  arbitrary downgrade because it accepts no requested status value.
- Replace/rename `_advance_to_script_generated` with a helper whose name reflects both
  advance and downgrade behavior, and call it in the same `_write_transaction` as the
  successful script persistence. Full generation and manual script save already share
  `_save_script_and_advance`; line regeneration will call the same status helper after
  `update_script_line`, before that transaction commits. Reading current status in the
  write transaction avoids acting on the pre-Gemini snapshot if another request changed
  status while the network call was in flight.

**Allowed files to modify**

- `app/services/project_service.py`
- `app/api/projects.py`
- `tests/test_project_service.py`
- `tests/test_script_api.py`
- `tests/test_projects_api.py`
- `.viepilot/phases/07-script-edit-staleness/tasks/task-7.1.md` (plan/evidence only;
  do not change `Status`)

**Test coverage**

1. Preserve the existing draft behavior: generating/saving a script still advances
   `draft -> script_generated`; the internal service operation is also covered for this
   forward case and for the `script_generated` idempotent case.
2. Parameterize the downstream states `audio_generated`, `video_generated`, and
   `complete`; after a successful full generation, per-line regeneration, or manual
   script save, assert the project status is `script_generated`. Assert the change is
   status-only: sentinel downstream job data and on-disk artifact files remain present
   and unchanged.
3. Preserve the public boundary: advance a project to `complete` through legal public
   steps, then assert a client-supplied `complete -> draft` project update still returns
   422. The task text says `PATCH /{project_id}`, but the actual route in
   `app/api/projects.py` and `ARCHITECTURE.md` is `PUT /api/projects/{project_id}`;
   `PATCH` exists only for nested speaker/thumbnail resources. The regression test will
   target the real `PUT` endpoint; no new project-level PATCH route will be invented.
4. Keep/adjust the existing transaction rollback regression so a failure in the new
   internal status operation rolls back the script mutation and status change together.

**Known risks and limits**

- The initial project snapshot is intentionally released before the Gemini call. The
  status helper must therefore re-read current status under `_write_transaction`, not
  trust that snapshot.
- This is backend-only. No dashboard or step-page UI change, no schema/API signature
  change, and no audio/video/job invalidation beyond the project status signal.
- Gemini remains monkeypatched in API tests; Task 7.1 does not require network,
  ffmpeg, GPU, or model weights. No special system-dependency preflight is needed.

**Verification commands**

```powershell
venv\Scripts\python -m pytest tests/test_project_service.py tests/test_projects_api.py tests/test_script_api.py -q
venv\Scripts\python -m pytest tests/ -q
venv\Scripts\python -m ruff check app/ tests/
git diff --check
git status --short
```

Implementation is paused pending PM approval per AR-06.

### PM Plan Review (2026-09-17) — APPROVED

Independently re-verified rather than accepting the plan on its word.

**Route correction confirmed real, and correctly caught rather than silently worked
around**: grepped `app/api/projects.py` for every `@router.` decorator — confirmed
the project-level update route is genuinely `PUT /{project_id}` (line 129), and the
only `PATCH` route in this file is the unrelated nested
`PATCH /{project_id}/speakers/{speaker_id}` (line 140). This task card's original
"PATCH /{project_id}" wording was a PM error — Codex's correction is accepted; the
task card's Verification checklist has been fixed to say `PUT` above. Read
`update_project`'s handler directly (lines 129-137): confirmed it calls
`project_service.update_project`, which still calls `_validate_status_transition`
unconditionally — Codex's plan to leave both of those functions untouched correctly
preserves the public forward-only guarantee.

**Third call site (`PUT /{project_id}/script`, manual script save) — approved
addition, not scope creep.** PM's own original File-Level Plan only named
`generate_script`/`regenerate_script_line` explicitly, but independently read
`save_script`'s handler (lines 246-262): it already routes through the exact same
`_save_script_and_advance` → `_advance_to_script_generated` path as the two AI-driven
endpoints, carrying the identical bug. This is arguably the *most* important call site
to fix, since it's the Step 2 UI's normal autosave path — hit far more often in real
use than explicit "Generate"/"Regenerate" actions. Squarely within this task's
Objective ("when a script is generated or a line regenerated... or edited") and both
files were already in the locked Allowed files list — approved without needing a
scope amendment.

**Re-reading current status inside the write transaction (not the pre-Gemini
snapshot)** — a real correctness detail PM had not explicitly required but is the
right call: `generate_script`/`regenerate_script_line` release the initial project
read before the (potentially slow) Gemini network call per the existing `# no lock
held — Gemini call` comments; re-reading status under `_write_transaction` avoids
acting on stale status if another request changed it during that window. Approved.

**Test plan**: covers exactly the 3 scenarios required (draft no-regression,
downstream-state downgrade parametrized across all 3 real statuses with an explicit
assertion that job/artifact data is untouched, and the public-endpoint boundary using
the real `PUT` route) plus a 4th transaction-rollback regression check beyond what was
asked — approved.

**Allowed files — confirmed/locked, exactly as Codex named them**:
- `app/services/project_service.py`
- `app/api/projects.py`
- `tests/test_project_service.py`
- `tests/test_projects_api.py`
- `tests/test_script_api.py`
- This task card, for evidence only (`Status` field remains PM-only)

**Plan approved as presented, with the PATCH→PUT correction folded into this task
card's checklist. No changes requested.** Codex may proceed to implementation.

## Implementer Evidence (Awaiting PM Acceptance)

### Implementation summary

- Added `project_service.mark_script_changed()`, an internal operation with no
  caller-selected target status. It re-reads the live status inside the existing write
  transaction, keeps `script_generated` idempotent, preserves the existing validated
  `draft -> script_generated` path, and performs only the three intentional downstream
  downgrades to `script_generated`.
- Left `_validate_status_transition`, `project_service.update_project`, and the public
  `PUT /api/projects/{project_id}` handler unchanged. A new API regression test proves
  `complete -> draft` still returns 422 and leaves the stored status at `complete`.
- Wired status synchronization into full generation, per-line regeneration, and manual
  script save. Each script mutation and its status update share one
  `_write_transaction`, so either both commit or both roll back.
- Kept the private `_save_script_and_advance` name/signature because the existing
  write-lock regression suite calls it directly. Its implementation no longer trusts
  the pre-Gemini project snapshot; the live status is re-read by
  `mark_script_changed()`.
- Added 15 effective test cases: draft/idempotent service behavior; all three downstream
  statuses; preservation of audio/video job rows and real sentinel files; all 3 statuses
  x all 3 mutation routes; and the public backward-transition rejection. Updated the
  existing rollback test to fail the new internal status operation.

### Files changed

- `app/services/project_service.py`
- `app/api/projects.py`
- `tests/test_project_service.py`
- `tests/test_projects_api.py`
- `tests/test_script_api.py`
- `.viepilot/phases/07-script-edit-staleness/tasks/task-7.1.md` (evidence only; `Status`
  unchanged)

### Verification evidence

Targeted final command:

```text
> venv\Scripts\python -m pytest tests/test_project_service.py tests/test_projects_api.py tests/test_script_api.py -q
........................................................................ [ 93%]
.....                                                                    [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
77 passed, 2 warnings in 20.63s
```

Existing write-lock regression suite, rerun after retaining the private helper
compatibility contract:

```text
> venv\Scripts\python -m pytest tests/test_project_service.py tests/test_projects_api.py tests/test_script_api.py tests/test_projects_write_lock.py -q
........................................................................ [ 90%]
........                                                                 [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
80 passed, 2 warnings in 20.39s
```

Full suite, final run:

```text
> venv\Scripts\python -m pytest tests/ -q
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 36%]
........................................................................ [ 48%]
........................................................................ [ 60%]
........................................................................ [ 72%]
........................................................................ [ 84%]
........................................................................ [ 96%]
......................                                                   [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
598 passed, 2 warnings in 757.28s (0:12:37)
```

Lint:

```text
> venv\Scripts\python -m ruff check app/ tests/
All checks passed!
```

The first full-suite attempt exposed three pre-existing tests that directly referenced
the renamed private helper. This was not a product defect or an accepted flaky failure;
it was corrected within the allowed production file by retaining the old private
name/signature and then rerunning the affected regression suite and full suite above.
Exact first-run summary:

```text
FAILED tests/test_projects_write_lock.py::test_write_lock_prevents_cross_project_transaction_interleaving
FAILED tests/test_projects_write_lock.py::test_read_transaction_waits_for_write_and_sees_no_phantom_rows
FAILED tests/test_projects_write_lock.py::test_write_transaction_rolls_back_on_commit_failure
3 failed, 595 passed, 2 warnings in 451.72s (0:07:31)
```

Final whitespace check (exit code 0; Git emitted only its Windows line-ending notices):

```text
> git diff --check
warning: in the working copy of '.viepilot/phases/07-script-edit-staleness/tasks/task-7.1.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/api/projects.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/services/project_service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_project_service.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_projects_api.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_script_api.py', LF will be replaced by CRLF the next time Git touches it
```

Final worktree scope:

```text
> git status --short
 M .viepilot/phases/07-script-edit-staleness/tasks/task-7.1.md
 M app/api/projects.py
 M app/services/project_service.py
 M tests/test_project_service.py
 M tests/test_projects_api.py
 M tests/test_script_api.py
```

### Limits / residual risks

- No audio/video files or job rows are invalidated; they intentionally remain available
  and may be stale. The project-level status is the approved signal.
- No UI warning was added. Dashboard badge and Continue routing reuse the corrected
  project status as approved.
- The two warnings are dependency deprecations in FastAPI/Starlette test infrastructure,
  unrelated to Task 7.1. There were zero test failures and zero Gemini retry flakes in
  the final full-suite run.

## PM Re-review (2026-09-18) — ACCEPTED

Independently re-verified everything rather than accepting the report on its word.

**Diff review** — read the full `git diff` for all 5 production/test files:
- `app/services/project_service.py`: `mark_script_changed()` reads the live `status`
  column directly via `db.execute("SELECT status FROM projects WHERE id = ?", ...)`
  inside the caller's transaction (never trusts a pre-Gemini snapshot), is a true
  no-caller-input operation (takes no `status` parameter at all), keeps
  `script_generated` idempotent, routes the `draft` case through the existing
  `update_project`/`_validate_status_transition` path unchanged, and for the 3
  downstream statuses issues a direct, narrowly-scoped
  `UPDATE projects SET status = 'script_generated', updated_at = ?` — confirmed via
  reading `_build_config_snapshot` that `config_json` never embeds `status`, so this
  narrow raw update cannot desync any cached snapshot field.
- `app/api/projects.py`: `_advance_to_script_generated` was renamed to
  `_sync_status_after_script_change` and now unconditionally calls
  `mark_script_changed`; `_save_script_and_advance` (used by both full generation and
  manual save) calls it inside the existing `_write_transaction`; `regenerate_script_line`
  now also calls it inside its own `_write_transaction`, alongside `update_script_line`
  — confirmed both operations commit or roll back together.
- Confirmed via direct read of `update_project`/`_validate_status_transition`: both are
  byte-for-byte unchanged. The public `PUT /{project_id}` endpoint's forward-only
  guarantee for caller-supplied input is fully intact — `mark_script_changed` cannot be
  reached from any public request body since it accepts no target status.
- Test diffs read in full: `test_project_service.py`'s 3 new tests include a real
  disk-and-DB check (`test_mark_script_changed_preserves_downstream_jobs_and_files`)
  that writes real audio/video files and real `audio_jobs`/`video_jobs` rows, then
  asserts both the DB rows and the file bytes are byte-identical after the downgrade —
  not just "no exception was raised." `test_projects_api.py`'s new test drives a
  project through all 4 real forward transitions via the actual `PUT` endpoint before
  proving `complete -> draft` still returns 422 and the stored status is unchanged.
  `test_script_api.py`'s new test is fully parametrized (3 downstream statuses × 3
  real mutation routes = 9 real end-to-end HTTP scenarios), and the pre-existing
  rollback regression was correctly updated to monkeypatch the new
  `mark_script_changed` call boundary rather than the old `update_project` one.

**Mid-implementation self-correction, reported honestly rather than hidden**: Codex's
first full-suite run surfaced 3 failures in `tests/test_projects_write_lock.py` because
that pre-existing regression suite calls `_save_script_and_advance` directly by name.
Rather than silently renaming that suite's calls (out of its `allowed_files`) or
quietly leaving the coupling unresolved, Codex kept the legacy private helper name/
signature intact specifically for that compatibility contract, documented why in the
function's own docstring, and re-ran the affected suite plus the full suite to confirm
the fix. This is exactly the "not a defect, not a hidden workaround" standard the
project's own contract requires — verified via `git diff` that
`tests/test_projects_write_lock.py` itself has zero changes (not in `git status
--short`'s output at all), confirming the compatibility was preserved by adapting the
production helper, not by touching the out-of-scope test file.

**PM independently re-ran every verification command**: 80/80 targeted + write-lock
regression pass, `ruff check app/ tests/` clean, `git diff --check` exit 0 — all
matched the Implementer's report exactly. Confirmed via `git status --short` that
exactly the 6 allowed files were touched, nothing else.

**Full suite, run independently**: 596 passed, 2 failed
(`test_generate_script_retries_on_429_then_succeeds`,
`test_generate_script_backoff_sequence_is_1s_2s_4s`) in 1353.31s (22:33) — both are
the project's long-documented Gemini-retry/backoff timing flake class (unrelated to
this task's files: `tests/test_script_service.py`, not among the 6 touched files),
and both confirmed passing instantly in isolation (0.71s for both together) on
re-run. Non-regressive.

**Zero real defects found on PM review.** Accepted as delivered — no changes
requested.

**This closes Task 7.1 — and Phase 7 (Script Edit Staleness) in full**, since it was
the phase's only task.
