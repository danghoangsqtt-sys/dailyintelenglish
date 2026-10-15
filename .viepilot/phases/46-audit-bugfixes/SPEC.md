# Phase 46 — Audit bug fixes (BUG-037–040)

Owner instruction 2026-10-15: fix the bugs from the audit. Mode: bug fixes/refactor; patch candidate 1.3.1, with released version 1.3.0 retained until the existing owner gates and release step. Execution continues through vp-auto under this instruction.

## Scope and compatibility
- Reconcile HANDOFF and historical completion checkpoints against recorded owner decisions; preserve pending Gates B-25/B-26/B-27/B-28.
- Refresh current architecture/structure documentation and changelog without rewriting historical reports.
- Keep Inter typography while serving its font locally; normal browser load checks must work without Internet.
- Recover only Remotion's observed transient navigation/no-response failure once, within the existing total time budget; retain complete diagnostic logs and preserve prior successful media.
- No database migration, project data deletion, running-app restart, release, exe rebuild or change to thumbnail feature scope.

## Tasks
| Task | Scope | Status |
|---|---|---|
| 46.1 | BUG-037/038: phase state, tags and current documentation | in_progress |
| 46.2 | BUG-040: deterministic local page loading | planned |
| 46.3 | BUG-039: bounded render recovery, diagnostics and real sandbox render | planned |

## Verification
- Check all phase rows, pending gates and historical tag targets; embedded Mermaid equals required sidecars.
- Failing-then-passing offline browser regression; run the four previously failing browser modules together.
- Remotion subprocess contract tests for transient recovery, terminal errors, timeout budget and old-output preservation; full real render to disposable output and ffprobe integrity checks.
- Ruff, renderer typecheck/Vitest and full pytest after the fixes.
