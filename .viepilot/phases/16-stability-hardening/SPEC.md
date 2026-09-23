# Phase 16 Specification — Stability Hardening

The controlling implementation contract is
`docs/implementation/phase-16-stability-hardening.md`. Predecessors: the Phase 13–15 plans
(still controlling where not amended), ADR-001 (+A1, A2).

## Goal

Close the four gaps the 2026-09-23 `/vp-audit` found between "works" and "stable":
- a worker loop that can die silently (BUG-022);
- ffmpeg calls with no timeout (ENH-008);
- the variable repetition failure in local script generation (ENH-009);
- leaked test data in the real DB, plus CHANGELOG drift (BUG-023).

## Required gates

- **Doc-first:** this spec, `PHASE-STATE.md` and the task cards exist and are pushed
  before any product code changes. Each card's *Design decisions* section is committed
  and PM-approved before that task's code.
- **Invariant 24:** `SCRIPT_MAX_REPEATED_8GRAM_RATIO`, both word tolerances and
  `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER` stay pinned for the whole phase.
- **Invariant 25:** after 16.1 the worker loop survives any per-iteration exception,
  never swallows `CancelledError`, and exposes `worker_alive` on `/api/ai/health`.
- **Invariant 26:** only the PM writes the real `data/app.db` (16.3 cleanup), after a
  backup and after the owner has seen the dry-run.
- **Invariant 27:** every prompt change in 16.4/16.6 traces to observed repeated
  8-grams in gate evidence, and the trace is recorded in the card.
- **Gate B-7 (16.5):** script 5/5 complete, with no regression on any gate B-6 passed.

## Definition of Done

§4–§5 of the controlling plan, without relaxation. Deviations require the PM to update
the plan, the affected card and `PHASE-STATE.md` before implementation continues.

## Session partition

Plan §6. PM: `docs/**`, TRACKER, ROADMAP, HANDOFF, `.viepilot/requests/**`. Coder:
`app/**`, `tests/**`, `scripts/**`, `prompts/**`, `README.md`, `CHANGELOG.md`, and this
folder after the handover commit. Only the PM runs trials, gates and the real-DB cleanup.
