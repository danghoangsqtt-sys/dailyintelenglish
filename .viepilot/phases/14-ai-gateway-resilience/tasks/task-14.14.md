# Task 14.14 — Gate B-5, Local Only (Phase 14 Close-Out)

- **Status:** pending
- **Owner:** PM (execution and report). This card is a description only — the Coder
  mirrors it into the phase folder per plan §14's execution order but does not
  implement or run any part of it.
- **Priority:** P1
- **Dependency:** Task 14.4a-d done; Task 14.13 done. Coder idle for the duration of
  the run (`OLLAMA_NUM_PARALLEL=1` — concurrent load corrupts timing evidence, same
  rule as every prior Gate B run).
- **Controlling detail:** plan §14 "14.14 — Gate B-5, local only"; Amendment H
  decisions D17-D18

## Objective

Re-measure Gate B under Task 14.4a-d's runner fix (the level-default speed the
product already applies, finally applied in the runner too) and Task 14.13's
repetition-repair pass — the same protocol and unchanged pass rule as every prior
Gate B run, not a renegotiated threshold.

## Scope (per plan §14)

- Protocol of Task 14.12 (Gate B-4): 5 × B1 eight-minute local script runs at the
  corrected 1,000-word target, learning generation on every completed script, B1
  5/10-minute + A2/C1 samples, real media pipeline on the winning project, one real
  thumbnail-text and one real YouTube-package generation.
- **Media now measured at the level default speed** (Task 14.4a-d) instead of the
  runner's old hard-coded 1.0 — Gate B-4 already confirmed A/V diff is 0.00s at any
  speed (Task 14.10's D14 fix is speed-independent), so this run is expected to
  finally also pass the duration threshold that only failed because of the runner
  defect, not a real product gap.
- Script gate benefits from Task 14.13's repetition-repair pass — Gate B-4's two
  failures were both repetition-only global misses; this run measures whether one
  targeted repair actually recovers them in practice, not just in the FakeProvider
  test suite.

## Pass rule (declared now, not after results)

The unchanged Phase 13 Gate B rule (5/5 complete, content checks pass, learning/media
gates as originally defined).

- **Pass** → local-only (D9-D11) is now evidence-backed at the corrected targets with
  the repetition-repair and runner-speed fixes in place.
- **Fail** → reported plainly with exactly what still doesn't meet the bar.

**Phase 14 closes after this Gate B-5 run regardless of verdict** — the verdict is
recorded either way, and Phase 14 does not chase gates indefinitely; any further
hardening becomes a new phase.

## Evidence and report

- Evidence: `data/quality_reviews/phase14/gate-b5/` (gitignored, PM-owned at runtime).
- Report: `docs/operations/phase14-gate-b5.md` (PM-owned).

## Execution record

- PM:
