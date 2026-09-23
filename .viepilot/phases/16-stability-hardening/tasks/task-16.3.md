# Task 16.3 — Test-Data Leak: Root Cause, Guard, Cleanup Tool, CHANGELOG (BUG-023)

- **Status:** not started
- **Owner:** Coder (investigation, guard, script); PM (dry-run → owner → `--apply` on the real DB)
- **Priority:** P1
- **Dependency:** 16.2 accepted
- **Controlling detail:** plan §4 "16.3", invariant 26, owner decision D19;
  `.viepilot/requests/BUG-023.md`

## Measured problem (do not re-derive)

The real `data/app.db` holds 426 projects. 419 are fixtures:
- "Learning API Test Episode" ×126
- "YouTube API Test Episode" ×107
- "Export API Test Episode" ×98
- "Script API Test Episode" ×88

The newest is from 2026-09-22T09:51:09Z. Every `client` fixture in those test files already
monkeypatches `settings.DATA_DIR`, yet rows leaked. Two split runs on 2026-09-23 (non-browser,
then `-k browser`) leaked nothing. Suspect to confirm or eliminate: the `Database` process
singleton — `connect()` returns an already-open connection, so a test that opened it against
the real path and didn't close it makes later lifespans reuse the real DB.
CHANGELOG `[Unreleased]` has no Phase 15 entry (15.1–15.3 changed code).

## Allowed files

`tests/conftest.py`; the leak-source test files **named in the design section before
editing**; new `scripts/cleanup_test_projects.py`; new `tests/test_cleanup_test_projects.py`;
`CHANGELOG.md`.

## Required behaviour

1. **Investigation (record here):** one full single-process `pytest -q`, with the real DB
   project count read before and after (`sqlite3` `mode=ro` only). Name the leaking test(s)
   and the mechanism.
2. **Guard:** an autouse safeguard in `tests/conftest.py` so that no test can ever open the
   real `data/app.db`. It fails loudly if one tries.
3. **Cleanup script:** dry-run by default (counts per name + ids). `--apply` = backup to
   `data/backups/app-before-cleanup-<UTC>.db` and then delete **exact-name matches of the 4
   names only**, via the same service path as the API delete route (cascaded rows + per-project
   directories). `--db` / `--data-dir` are overridable.
4. CHANGELOG: add the missing Phase 15 entry (15.1 aliases, 15.2 merge fix, 15.3 runner
   `--gate`) plus this task's entry.

## Explicitly forbidden

Running `--apply` against the real DB (PM-only, invariant 26). Opening the real DB
read-write for any reason. Deleting by `LIKE` or any pattern other than the 4 exact names.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending — include the investigation findings_

## Verification (required)

The guard fails when the leak is reintroduced (revert-and-confirm-failure). A full
single-process `pytest -q` leaves the real project count unchanged. Script tests on a tmp DB:
exact names only, backup written, dry-run writes nothing, directories removed. `ruff`.

## PM run on the real DB (filled by PM)

_pending: dry-run output → owner OK → `--apply` output + backup path + new count_

## Evidence

_pending_
