# Phase 14 Specification — AI Gateway Resilience and Section Budget Rebalancing

The controlling implementation contract is
`docs/implementation/phase-14-ai-gateway-resilience.md`. The design record is
`docs/brainstorm/session-2026-09-21.md` (decisions D1–D8). ADR-001 is amended (A1).

## Goal

Make both providers survive ordinary transient conditions (restore bounded backoff),
make every repair/retry/fallback measurable on the job row, enforce the script word
budget exactly as the product defines it (±10% of the total, not ±15% per section as a
job-killing gate), then re-run Gate B for both providers and let the evidence choose the
rollout mode for Task 13.10.

## Required gates

- **Doc-first:** this spec, the controlling plan, the ADR amendment, and all six task
  cards exist and are pushed before any product code changes.
- **P0 gate:** 14.1 (backoff proven to wait) and 14.2 (telemetry written to the row)
  pass their tests and PM diff review before 14.3 starts.
- **Governance gate:** `SCRIPT_GLOBAL_WORD_TOLERANCE == 0.10` and
  `SCRIPT_SECTION_WORD_TOLERANCE == 0.15` are pinned by a test and unchanged for the
  whole phase.
- **Gate B-2:** both providers run the declared matrix sequentially under the declared
  decision rules (plan §4.4); infra and content failures are reported separately.
- **Record-integrity gate:** the Phase 13 acceptance report carries its correction with
  the original text preserved.
- **Rollout gate:** Task 13.10 resumes only with the evidence-selected mode (plan §6,
  14.6 table) or an explicit stop-condition record.

## Definition of Done

Use §7 of the controlling plan without relaxation. Deviations require updating the plan
(PM), the affected task card, and PHASE-STATE before implementation continues.

## Session partition

PM owns `docs/**`, `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`,
`.viepilot/HANDOFF.json`. Coder owns `app/**`, `tests/**`, `scripts/**`, `prompts/**`
and this folder after the handover commit. Only the PM runs
`scripts/run_ai_operational_trial.py`. See plan §10.
