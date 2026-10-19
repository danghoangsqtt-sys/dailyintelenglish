# Task 50.1 — BUG-042 cancellation-safe shared transactions

Status: implemented_verified (technical)2026-10-16. Owner authorized `vp-evolve`+`vp-auto` for audit bugs.

## Objective

Cancellation must not expose or commit abandoned shared-connection writes. Preserve original exceptions and allow a later request only after rollback completes.

## Paths

- backend/db/transactions.py
- tests/test_transactions.py
- backend/library/explainer_service.py
- .viepilot/phases/50-audit-recovery/PHASE-STATE.md
- .viepilot/phases/50-audit-recovery/tasks/task-50.1.md
- .viepilot/requests/BUG-042.md
- .viepilot/TRACKER.md
- .viepilot/ROADMAP.md
- .viepilot/HANDOFF.json
- CHANGELOG.md
- docs/operations/task49-5b-recovery-20261016.md

## File-Level Plan / allowed_files

- `backend/db/transactions.py`: rollback for cancellation/BaseException as well as ordinary exceptions; keep lock held while queued rollback finishes, propagate cancellation. No connection architecture change.
- `tests/test_transactions.py`: real in-memory SQLite isolation tests, controlled commit/rollback cancellation, repeated cancellation, ordinary/commit errors and successful writes. Fail old helper first.
- `backend/library/explainer_service.py`: remove obsolete local cancellation workaround only after shared helper supplies equivalent guarantees; preserve all domain/CAS behavior.
- State/request/changelog/report paths above: record exact results and authorization, separate technical verification from acceptance.

## Risk / stack policy

Shared helper high impact. aiosqlite worker may continue a queued SQL operation after caller cancellation; rollback must be awaited before lock release. Never swallow cancellation or run filesystem/network under DB lock. Use cache sqlite-versioned-assets plus Python asyncio cancellation semantics from recovery audit.

## Verification

First run `pytest tests/test_transactions.py -q` against old helper: targeted failure expected. After fix, focused transactions/worker/jobs/plan/API suites pass. Full `pytest tests/ -x -q`, Ruff, renderer tests/typecheck and JS syntax before final handoff. No real DB writes.

## Verification result 2026-10-16

Full **1848 passed in 741.01s**, 175 focused, 104 renderer/TypeScript/Ruff/JS passed; 2 fresh-process persistence checks and doc/schema parity clean. See `docs/operations/task49-5b-recovery-20261016.md`. Technical verification is separate from owner acceptance and actual Git persistence; no release.
