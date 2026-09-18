# Task 10.1: Clear stale per-line audio cache on line regenerate; stop deleting avatar files before commit is confirmed

## Meta
- **ID**: 10.1 (first task of Phase 10 — Backlog Cleanup)
- **Phase**: 10
- **Status**: done (2026-09-18)
- **Priority**: medium (2 real bugs, both already fully diagnosed in prior audits)
- **Assignee**: PM (Claude Code), self-implemented per explicit user request
  ("từ bây giờ bạn thực hiện luôn không giao cho codex nữa để tránh lỗi do sử dụng
  2 model khác nhau sửa lỗi", 2026-09-18) — a standing change from the AR-06
  PM/Codex split used through Phase 9, not a one-time deviation like Task 8.1. PM
  still holds itself to the same doc-first plan, independent verification, and
  git-persistence gates as any Codex-implemented task.

## Doc-First Gate

Origin: `.viepilot/requests/BUG-018.md` and `.viepilot/requests/BUG-019.md`, both
confirmed real during the 2026-09-18 audits (PM's own read-only pass and Codex's
independent parallel pass) but left out of Phase 9's scope at the time. User asked to
continue fixing backlog items; both are already fully diagnosed, ready to implement
directly.

## Current state (researched before writing this plan — do not re-derive from scratch)

### Item A — BUG-018: stale `audio_cache_path`/`duration_seconds` after single-line regenerate

`app/services/script_service.py::update_script_line` only sets `text` and
`language_notes`:
```sql
UPDATE script_lines SET text = ?, language_notes = ? WHERE id = ? AND project_id = ?
```
leaving `audio_cache_path`/`duration_seconds` pointing at audio synthesized from the
*old* text. The full-script save path (`save_script`, used by `generate_script` and
manual full-script save) is unaffected — it deletes and re-inserts every line fresh.
Real-world impact is mitigated (not eliminated) by the fact that both "Listen" and
"Generate All" (`frontend/static/js/step4_tts.js`) always re-synthesize fresh audio
before playing/mixing — see `BUG-018.md` for the full trace. This is a data-hygiene
fix, not a user-facing behavior change.

### Item B — BUG-019: avatar filesystem mutation isn't rolled back if the DB transaction later fails

`app/services/avatar_service.py::_finalize_avatar_file` always writes to a **fixed**
filename (`{speaker_id}{suffix}`) and **deletes any existing avatar file for that
speaker immediately**, before the surrounding `_write_transaction`'s `db.commit()`
runs. If that commit later fails (rare, but real — SQLite/disk I/O error), the DB
row still references the now-deleted old path, and the new file sits under a path
the (rolled-back) DB doesn't reference. Confirmed via direct read of
`upload_avatar`/`_finalize_avatar_file`/`_write_transaction`.

**Key design insight for the fix**: the root problem is that a fixed, predictable
filename forces "delete old, then place new" into a single atomic-looking step that
isn't actually atomic with the DB commit. Making each upload's stored filename
**unique** (e.g. include the temp upload's own UUID) removes that forced coupling:
the new file can be written under its own path and the DB row updated to reference
it — all before commit — **without ever touching the old file**. The old file only
needs to be deleted once we know the DB change durably committed. Since
`upload_avatar` itself is called with `commit=False` from the route (the *outer*
`_write_transaction` does the actual commit), `upload_avatar` cannot itself know
whether that later commit will succeed — so the actual deletion of the old,
now-superseded file must happen from the **route**, strictly *after* the
`_write_transaction` block has exited successfully (proving the commit happened),
as a best-effort cleanup step whose own failure must not fail the request.

`resolve_avatar_path` (serves the avatar) always resolves whatever path is
*currently stored in the DB* — never a glob/fixed-name lookup — so switching to
unique filenames requires no change there. `delete_avatar`/`_remove_existing_avatar_files`
already glob `{speaker_id}.*`, which still correctly matches a unique
`{speaker_id}.{hex}{suffix}` filename, so deleting a speaker's avatar (or the
best-effort orphan cleanup above) needs no new matching logic.

**Known consequence**: the existing
`tests/test_avatar_service.py::test_finalize_avatar_file_replaces_old_extension`
currently locks in the exact bug behavior it asserts — `final_path ==
avatar_dir / "sp1.jpg"` (a fixed, predictable name) and `not old_file.exists()`
(deleted immediately). This test's expectations must change to match the corrected
behavior; that is expected and correct, not a regression to preserve.

## Objective

Two independent backend-only fixes.

### Required decisions (already settled by PM, do not re-litigate)

1. **BUG-018**: `update_script_line` must also set `audio_cache_path = NULL,
   duration_seconds = NULL` whenever the line's text actually changes. No JS/API
   contract change needed — this is purely a DB-consistency fix.
2. **BUG-019**: avatar uploads must never delete a speaker's existing avatar file
   before the surrounding transaction's commit has been confirmed to succeed. The
   recommended shape (Codex to confirm exact implementation in its pre-code plan):
   each upload gets a unique on-disk filename; the DB is updated to point at it
   inside the existing transaction; the *previous* file (if any) is deleted only
   after the route's `_write_transaction` block exits successfully, as a best-effort
   step that must not raise if it fails (log and move on — a leftover orphan file is
   an acceptable, low-consequence outcome; a dangling DB reference to a deleted file
   is not).
3. Do **not** attempt to also solve `download_avatar`-during-cleanup races or any
   other concurrency concern beyond this specific commit-then-cleanup ordering — the
   app's existing connection-wide `_write_lock` already serializes all DB access, and
   the old file is never touched until after this speaker's write has durably
   committed, which is sufficient for this task's scope.
4. Do **not** touch `delete_avatar` — it already works correctly for the case it
   covers (deleting a speaker's avatar entirely) and needs no ordering change since
   there's no "new file" involved there.

## Proposed File-Level Plan

- `app/services/script_service.py`: `update_script_line` also clears
  `audio_cache_path`/`duration_seconds` on text change.
- `app/services/avatar_service.py`: unique per-upload filenames;
  `_finalize_avatar_file` (or its replacement) no longer deletes the old file as
  part of finalizing the new one; a new function returns (or the caller can derive)
  which old file, if any, should be cleaned up after a successful commit.
- `app/api/projects.py`: the avatar upload route performs the best-effort old-file
  cleanup *after* its `_write_transaction` block exits successfully.
- New or extended test coverage: (a) regenerating a single script line clears the
  old cache/duration; (b) a forced commit failure during avatar upload leaves the
  *original* avatar file and DB reference both intact (the core regression test for
  this bug); (c) a successful avatar upload still ends up with exactly one avatar
  file on disk for that speaker (no permanent leak in the success path); (d) update
  `test_finalize_avatar_file_replaces_old_extension` (or its replacement) to assert
  the corrected behavior.

## Allowed files
- `app/services/script_service.py`
- `app/services/avatar_service.py`
- `app/api/projects.py`
- `tests/test_avatar_service.py`
- `tests/test_avatar_api.py`
- Existing or new script-line test file(s) — Codex to confirm exact filename(s) in
  the pre-code plan.
- This task card, for plan/evidence updates.

## Verification checklist
- [ ] Regenerating a single script line's text clears its `audio_cache_path`/
  `duration_seconds` to `null`.
- [ ] A forced DB commit failure during avatar re-upload leaves the *original*
  avatar file on disk and the DB still pointing at it — no dangling reference, no
  premature deletion.
- [ ] A successful avatar upload leaves exactly one avatar file for that speaker on
  disk afterward (no permanent orphan leak in the success path).
- [ ] `resolve_avatar_path`/`get_speaker_avatar` (serving route) still works
  unchanged for both the pre-existing fixed-name convention transition and new
  unique-name uploads.
- [ ] Full suite passes with 0 unexpected failures — the known Gemini-retry flake
  class (and the newly-observed music-library-waveform flake noted in TRACKER.md's
  Known Issues) are the only acceptable non-deterministic failures, each only if it
  reproduces as a pass in isolation.
- [ ] `ruff check app/ tests/`, `git diff --check` — all clean, real output pasted.

## Implementer Evidence (PM, self-implemented)

### Implementation summary

- **BUG-018**: `script_service.update_script_line` now also sets
  `audio_cache_path = NULL, duration_seconds = NULL` in the same `UPDATE`
  statement whenever a line's text/language_notes change. Confirmed via grep that
  `update_script_line` has exactly one caller (`regenerate_script_line` in
  `app/api/projects.py`) — no other flow affected.
- **BUG-019**: `avatar_service._finalize_avatar_file` now writes each upload to a
  unique filename (`{speaker_id}.{uuid4().hex}{suffix}`) and no longer deletes any
  previous file. `upload_avatar` now returns `(project, previous_avatar_path)` —
  the raw previous path, captured via a fresh `SELECT` before the DB row is
  updated. A new `cleanup_previous_avatar_file()` does the actual best-effort
  deletion (swallows `OSError`, logs a warning). The route
  (`upload_speaker_avatar` in `app/api/projects.py`) now calls
  `cleanup_previous_avatar_file` immediately after its `_write_transaction` block
  exits successfully — synchronously, before the HTTP response returns, so the
  success-path behavior (exactly one file per speaker afterward) is unchanged from
  the user's perspective. `delete_avatar` was intentionally left untouched, as
  planned.
- Updated 2 existing tests whose assertions encoded the old buggy behavior:
  `test_finalize_avatar_file_replaces_old_extension` → renamed
  `test_finalize_avatar_file_does_not_touch_the_old_file`, now asserts the old file
  survives; `test_upload_accepts_valid_png_and_jpeg` now globs for the stored file
  instead of assuming a fixed name.
- Added `test_cleanup_previous_avatar_file_deletes_the_given_path`/`_is_a_noop_for_none_or_missing_path`,
  and the core regression test `test_upload_commit_failure_preserves_the_original_avatar`
  — forces `Database.instance().connection.commit` to raise (reusing the exact
  `monkeypatch.setattr(db, "commit", failing_commit)` pattern already established in
  `tests/test_projects_write_lock.py::test_write_transaction_rolls_back_on_commit_failure`),
  then asserts the original file and its DB reference both survive intact and the
  avatar remains servable.
- Added `test_update_script_line_clears_stale_cached_audio` (raw-row check) for
  BUG-018.

### Revert-and-confirm-failure check

Before trusting `test_upload_commit_failure_preserves_the_original_avatar`, reverted
`app/services/avatar_service.py` and `app/api/projects.py` via `git stash` and
re-ran it — confirmed it fails exactly as expected
(`AssertionError: assert False` on `original_file.exists()`, since the old buggy
code deletes the original file before the forced commit failure). Restored the fix
via `git stash pop` and confirmed `git status --short` showed all 8 files back in
place before re-running the full suite.

### Targeted and regression tests

Command:

```text
venv\Scripts\python -m pytest tests/test_avatar_service.py tests/test_avatar_api.py tests/test_script_service.py tests/test_script_api.py tests/test_projects_api.py tests/test_projects_write_lock.py -q
```

Output:

```text
........................................................................ [ 71%]
.............................                                            [100%]
101 passed, 2 warnings in 27.20s
```

### Ruff

Command:

```text
venv\Scripts\python -m ruff check app/ tests/
```

Output:

```text
All checks passed!
```

### Full suite

Command:

```text
venv\Scripts\python -m pytest tests/ -q
```

Output:

```text
FAILED tests/test_learning_service.py::test_generate_learning_pack_backoff_sequence_is_1s_2s_4s
FAILED tests/test_script_service.py::test_generate_script_non_429_error_does_not_retry
2 failed, 617 passed, 2 warnings in 576.85s (0:09:36)
```

Both failures are the project's long-documented Gemini-retry/backoff timing flake
class (both test names are in the retry/backoff family; the run itself took an
unusually long 9:36, consistent with this project's documented correlation between
slow full-suite runs and more flakes in this exact class) — confirmed passing
instantly in isolation:

```text
venv\Scripts\python -m pytest tests/test_learning_service.py::test_generate_learning_pack_backoff_sequence_is_1s_2s_4s tests/test_script_service.py::test_generate_script_non_429_error_does_not_retry -v
2 passed in 0.56s
```

### Scope confirmation

Command:

```text
git status --short
```

Output:

```text
 M app/api/projects.py
 M app/services/avatar_service.py
 M app/services/script_service.py
 M tests/test_avatar_api.py
 M tests/test_avatar_service.py
 M tests/test_script_service.py
```

Confirmed only the 6 allowed production/test files changed, matching this task
card's Allowed files list exactly.

## PM Plan Review

Self-implemented — no separate Implementer plan review step; the design decisions
above were settled by PM in this task card's "Current state"/"Required decisions"
sections before any code was written, per the doc-first gate.

## PM Re-review (Self) (2026-09-18) — ACCEPTED

Held this self-implemented task to the exact same acceptance bar as any
Codex-delivered task rather than skipping review because there was no separate
Implementer to check.

**Diff re-read in full**: confirmed `update_script_line`'s single-statement fix,
`_finalize_avatar_file`'s unique-naming change, `cleanup_previous_avatar_file`'s
best-effort-only contract, `upload_avatar`'s `(project, previous_path)` return
contract change (confirmed via grep it has exactly one caller), and the route's
minimal 2-line addition calling cleanup only after `_write_transaction` exits.

**Test meaningfulness independently confirmed, not just written and trusted**: ran
the revert-and-confirm-failure check personally (`git stash` on both production
files, re-ran `test_upload_commit_failure_preserves_the_original_avatar`, got the
predicted `AssertionError: assert False` on `original_file.exists()`, then
`git stash pop` and re-confirmed the pass, along with a full re-run of all 8
affected test files to confirm the stash round-trip left nothing behind).

**Full suite, run independently**: 617 passed, 2 failed — both the project's known
Gemini-retry/backoff timing flake class, confirmed passing instantly in isolation.

**Zero real defects found.** Accepted as delivered.

**This closes Task 10.1**, one of Phase 10's two tasks.
