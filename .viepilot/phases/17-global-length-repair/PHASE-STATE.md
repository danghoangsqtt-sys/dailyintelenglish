# Phase 17 State — Budget-Aware Global Validation (ENH-010)

## Metadata

- **Phase:** 17
- **Slug:** `17-global-length-repair`
- **Status:** complete
- **Closed:** 2026-09-23 (re-gate 17.5 PASS)
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
| 17.3 | Gate B-8, local only | PM | done: runner PASS; owner 1/2 → 17.4 | `docs/operations/phase17-gate-b8.md` |
| 17.4 | Under via full per-section path | Coder | done (`5008792`) | — |
| 17.5 | Re-gate B1 ×5 + owner ×4 | PM | **PASS** (5/5, 4/4) | `docs/operations/phase17-gate-b8r.md` |
| 17.4 | "Under" direction via the full per-section path (Amendment C, Gate B-8 fix) | Coder | done | — |
| 17.5 | Short re-gate (B1 ×5 + owner config ×4) | PM | not started | Coder idle |

**Execution order:** 17.1 → 17.2 → 17.3 → 17.4 → 17.5 → close-out.

## Evidence log

(Coder and PM append per task.)
