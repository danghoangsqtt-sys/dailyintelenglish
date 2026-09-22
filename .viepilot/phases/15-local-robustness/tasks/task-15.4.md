# Task 15.4 — Gate B-6, Local Only

- **Status:** pending
- **Owner:** PM (execution and report). This card is a description only — the Coder
  mirrors it into the phase folder per plan §4's execution order but does not
  implement or run any part of it.
- **Priority:** P1
- **Dependency:** Task 15.1, 15.2, and 15.3 all done. Coder idle for the duration of
  the run (`OLLAMA_NUM_PARALLEL=1` — concurrent load corrupts timing evidence, same
  rule as every prior Gate B run).
- **Controlling detail:** plan §3 "15.4 — Gate B-6, local only"; plan §4 (order, stop
  conditions, rollback)

## Objective

Re-measure Gate B with Task 15.1's speaker-alias resolution and Task 15.2's
consecutive-lines merge in place, using the same protocol as Gate B-5 plus one new,
directly-motivated sample: the owner's own failing configuration.

## Scope (per plan §3)

- Protocol of Gate B-5 (Task 14.14): 5 × B1 eight-minute local script runs at the
  1,000-word target, learning generation on every completed script, B1 5/10-minute +
  A2/C1 samples, real media pipeline on the winning project, one real thumbnail-text
  and one real YouTube-package generation.
- **Plus a fifth sample: the owner's own failing configuration** — A2, small_talk, 10
  minutes, 2 speakers — the exact shape of project that died at section 3 in real use
  before this phase opened.
- **Pace calibration is not re-done in this phase.** The media gate is reported as
  declared (the same measured 125 wpm B1 default from Task 14.10/D13), not
  re-calibrated — Task 15.5 (optional, owner's word only) is the only path to a
  different pace measurement.

## Pass rule (declared now, not after results)

The unchanged Phase 13 Gate B rule (5/5 complete, content checks pass, learning/media
gates as originally defined), now also requiring the owner's-configuration sample to
complete without an unknown-speaker or consecutive-lines structural failure.

- **Pass** → both structural-repair paths (15.1, 15.2) are evidence-backed at real
  scale, including against the owner's own exact failing shape.
- **Fail** → reported plainly with exactly what still doesn't meet the bar; does not
  reopen D11 (local-only ships regardless, unchanged since Phase 14).

## Evidence and report

- Evidence: `data/quality_reviews/phase15/gate-b6/` (gitignored, PM-owned at runtime;
  Task 15.3's new `--gate` flag is what makes this the real path instead of the old
  runner defect's fixed `phase14/gate-b2/` directory).
- Report: `docs/operations/phase15-gate-b6.md` (PM-owned).

## Execution record

- PM:
