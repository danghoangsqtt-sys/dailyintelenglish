# Task 18.4 — Fallback-rate readout + runner `--matrix cloud_first`

- **Status:** not started
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** 18.3 accepted
- **Controlling detail:** `docs/implementation/phase-18-cloud-first-ai.md` §3 "18.4", invariants 31–35;
  evidence in `docs/operations/enh011-nemotron-smoke.md`; decisions D21–D24

## Allowed files

See plan §3 "18.4", which is binding. Anything else → stop and ask the PM.

## Required behaviour (summary; the plan is binding)

The fallback rate over the last N jobs (the share of calls and of jobs) appears in health and on the Settings page. The trial runner gains `--matrix cloud_first` and records provider/model/fallback per call.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending_

## Verification (required)

See plan §3 "18.4". Always: revert-and-confirm-failure on the key new test, the full suite, `ruff`,
and the real DB untouched.

## Evidence

_pending_
