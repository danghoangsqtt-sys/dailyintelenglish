# PHASE-STATE — Phase 46: Audit bug fixes

- **Status:** owner-authorized trial installed, verified and published 2026-10-15. Extended usage feedback and formal visual/operational gates remain pending.
- **Release:** trial 1.4.0-rc.1; last stable version remains 1.3.0.

| Task | Description | Status |
|---|---|---|
| 46.1 | Reconcile historical phase state/checkpoints and current documentation | implemented_verified |
| 46.2 | Local fonts, initial sidebar geometry and bounded browser transport recovery | implemented_verified |
| 46.3 | Diagnose and recover the observed transient Remotion navigation failure | implemented_verified |
| 46.4 | Regenerate title/folder fixes in the actual episode outputs | implemented_verified |
| 46.5 | Center and harmonize portrait layout | implemented_verified |
| 46.6 | Richer portrait motion library | implemented_verified |
| 46.7 | Shared YouTube motion and phrase-level dialogue gestures | implemented_verified |
| 46.8 | Branded one-click EXE, measured GPU compositor improvement and GitHub trial | owner_trial_delivered |

Pending owner gates B-25, B-26, B-27 and B-28 remain pending.

## Owner trial follow-up (2026-10-15)

Task 46.8 is **delivered under the owner's explicit trial authorization**. The branded GUI EXE replaced the old build with a full backup, Desktop shortcut was created, current data/runtime smoke passed, and GitHub v1.4.0-rc.1 was published with ZIP/checksum. This lifts the earlier packaging/persistence hold for the trial; outstanding visual/operational owner gates remain pending. Evidence: docs/operations/exe-trial-20261015.md and tasks/task-46.8.md.

## Initial audit verification
- Full pytest: 1,621 passed, one existing dependency deprecation warning, 871.13 s (14:31).
- Renderer: TypeScript check and 72 Vitest tests passed; Ruff, modified JavaScript syntax and git diff --check passed.
- Full real episode: 194.886 s render, 240.917333 s output, 1280x720 H.264/AAC, A/V duration difference <0.1 s, source DB opened read-only with zero changes.
- All four requests are fixed_pending_review. No new phase completion/release tag or commit/push is declared without PM acceptance.
