# Task 14.12 — Gate B-4, Local Only

- **Status:** pending
- **Owner:** PM (execution and report). This card is a description only — the Coder
  mirrors it into the phase folder per plan §13's execution order but does not
  implement or run any part of it.
- **Priority:** P1
- **Dependency:** Task 14.10 done; Task 14.11 done. Coder idle for the duration of the
  run (`OLLAMA_NUM_PARALLEL=1` — concurrent load corrupts timing evidence, same rule as
  Gate B-2/B-3).
- **Controlling detail:** plan §13 "14.12 — Gate B-4, local only"; Amendment G decisions
  D13-D15; ADR-001 amendment A2

## Objective

Re-measure Gate B under the new, measured pace targets (Task 14.10) and the learning
repair-by-removal path (Task 14.11), using the same protocol and the same unchanged
pass rule as Gate B-3 — not a renegotiated threshold, a re-run at corrected targets.

## Scope (per plan §13)

- Same protocol as Task 14.9 / Gate B-3: 5 × B1 eight-minute local script runs, learning
  generation on every completed script, B1 5/10-minute + A2/C1 samples, real media
  pipeline on the winning project, plus one real thumbnail-text and one real
  YouTube-package generation.
- **B1 8-minute target is now 1,000 words** (Task 14.10's measured `CEFR_WORDS_PER_MINUTE["B1"] = 125`),
  not the old, never-achieved 800. The runner's own per-run acceptance ranges derive
  from the constant, so no separate threshold edit is needed beyond picking up
  Task 14.10's change.
- Media gate: same thresholds as declared by Task 14.10's D14 outcome (either the
  existing `AV_DIFF_MAX_SECONDS = 1.0`, if D14 found and fixed an unintentional tail, or
  the re-declared `3.0`, if D14 found a deliberate design element) — evaluated as
  declared, not renegotiated after seeing this run's results.
- Learning gate: every completed script's learning generation now goes through Task
  14.11's repair-by-removal path when needed; a pack that publishes with dropped items
  is reported as such (not indistinguishable from a pack that needed no repair at all).

## Pass rule (declared now, not after results)

The unchanged Phase 13 Gate B rule (5/5 complete, content checks pass, learning/media
gates as Task 13.9 originally defined them, just measured against Task 14.10's corrected
word targets and Task 14.10's D14-declared A/V threshold).

- **Pass** → the local-only path (D9-D11) is now evidence-backed at the corrected
  targets, closing the open question Gate B-3 left about pace.
- **Fail** → reported plainly with exactly what still doesn't meet the bar; does not
  reopen D9-D11 (the owner's local-only decision does not depend on this gate, per D11 —
  same non-negotiable point already established at Gate B-3) but does inform whatever
  Phase 14 close-out or follow-on task addresses the remaining gap.

## Evidence and report

- Evidence: `data/quality_reviews/phase14/gate-b4/` (gitignored, PM-owned at runtime).
- Report: `docs/operations/phase14-gate-b4.md` (PM-owned).

## Execution record

- PM:
