# Task 14.9 — Gate B-3, Local Only

- **Status:** pending
- **Owner:** PM (execution and report). This card is a description only — the Coder
  mirrors it into the phase folder per plan §12's "Execution order and partition" but
  does not implement or run any part of it.
- **Priority:** P1
- **Dependency:** Task 14.7 done; Task 14.8 done. Coder idle for the duration of the run
  (`OLLAMA_NUM_PARALLEL=1` — concurrent load corrupts timing evidence, same rule as
  Gate B-2).
- **Controlling detail:** plan §12 Task 14.9; ADR-001 amendment A2; brainstorm decision
  D11

## Objective

A third local Gate B run, under the Task 14.7/14.8 changes, to establish whether the
owner's local-only decision (D11) is an evidence-backed promotion or remains an explicit
override. Same protocol and thresholds as Task 13.9 / Gate B-2's local matrix — not
weakened, not re-negotiated after seeing results.

## Scope (per plan §12)

- Same protocol as Task 13.9 / plan §4.4's local matrix, same thresholds (5 × B1
  eight-minute, learning per completed script, B1 5/10-minute + A2/C1 samples, real
  media pipeline on the winning project).
- Plus one real thumbnail-text generation and one real YouTube-package generation on the
  winning project (schema validity, human-read) — Task 14.7's `FakeProvider` tests only
  prove local-mode wiring; this is where their real-Ollama structured-output quality
  actually gets measured.
- Media gate: run the pipeline and record durations; the duration and A/V-diff
  thresholds are evaluated **as declared** (unchanged from Gate B-2's thresholds). If the
  owner has not separately decided the pace-calibration question (the ~135 wpm actual vs
  100 wpm planned issue Gate B-2 surfaced, explicitly out of Phase 14 scope) before this
  run, the media gate is reported **FAIL** with the measured pace, and that open question
  is recorded as still open — not silently resolved by this task.

## Pass rule (declared now, not after results)

The unchanged Phase 13 Gate B rule (5/5 complete, content checks pass, learning/media
gates as Task 13.9 defines them).

- **Pass** → D11 becomes an evidence-backed promotion rather than an override.
- **Fail** → D11 stands as an owner override, recorded as such in the report; Task 13.10
  still resumes per D11 regardless (the owner's decision to ship local-only does not
  depend on Gate B-3 passing) — the report states plainly what the local path does and
  does not achieve, rather than treating a fail as a fresh stop condition.

## Evidence and report

- Evidence: `data/quality_reviews/phase14/gate-b3/` (gitignored, PM-owned at runtime).
- Report: `docs/operations/phase14-gate-b3.md` (PM-owned).

## Execution record

- PM:
