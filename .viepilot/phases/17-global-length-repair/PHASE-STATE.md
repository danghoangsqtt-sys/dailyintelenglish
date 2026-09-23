# Phase 17 State — Budget-Aware Global Validation (ENH-010)

## Metadata

- **Phase:** 17
- **Slug:** `17-global-length-repair`
- **Status:** planned (handover to Coder pending)
- **Opened:** 2026-09-23
- **Controlling plan:** `docs/implementation/phase-17-global-length-repair.md`
- **Authorization:** the owner opened it with `/vp-evolve ENH-010` on 2026-09-23, after Phase 16
  closed (D20). Execution uses two parallel sessions: PM Claude Opus, Coder Claude Sonnet.
- **Ownership of this folder:** PM until the handover commit, Coder after it.

## Preflight

- Branch `main`; Phase 16 closed (`4b5e3a1`, tag `die-vp-p16-complete`).
- Baseline: **956/956**, `ruff` clean; real DB 7 projects.
- Gate B-7 failures re-diagnosed from the trial checkpoints (plan §0):
  - run 1 died after a length-inflating repetition repair with no length re-check;
  - the 5-min sample died because the last-section-only budget repair couldn't absorb a
    middle-section overshoot.

## Task status

| Task | Description | Owner | Status | Blocking gate |
|---|---|---|---|---|
| 17.1 | Budget-aware global stage (targeted budget repair, length-aware repetition repair, mixed-failure path) | Coder | done | — |
| 17.2 | Final-section sign-off + `has_outro_last3` diagnostic | Coder | done | — |
| 17.3 | Gate B-8, local only | PM | not started | Coder idle |

**Execution order:** 17.1 → 17.2 → 17.3 → close-out.

## Evidence log

(Coder and PM append per task.)
