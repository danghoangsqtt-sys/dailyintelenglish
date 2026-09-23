# Task 17.1 — Budget-Aware Global Stage (ENH-010)

- **Status:** not started
- **Owner:** Coder
- **Priority:** P0
- **Controlling detail:** plan §0 (re-diagnosis), §3 "17.1", invariants 28–30

## Measured problem (do not re-derive; see plan §0)

- **B-7 B1 run 1:** the first global validation found the total inside ±10% and repetition only,
  so the budget repair was skipped. The repetition repair on section 2 (Task 14.13) then made that
  section longer, and the total became **1,124**. Repetition was still **1.07%**, so the job died
  as a mixed failure. Nothing re-checks the length after the repetition repair.
- **B-7 B1 5-min:** the total was 703 (> 687), so the last-section-only budget repair (Task 14.3
  item 6) asked section 3 for 237 words and got 315. Most of the overshoot sat in section 2
  (345 vs 292 effective).
- In both jobs, a section still over budget after its in-loop repair was accepted
  (`_budget_errors` discarded).

## Allowed files

`app/services/script_pipeline.py` (global validation stage + repair-prompt inputs only),
`app/core/constants.py`, `prompts/script/repair.txt`, `tests/test_script_pipeline.py`,
`tests/fixtures/ai/*`, `CHANGELOG.md`. Anything else → stop and ask the PM.

## Required behaviour

1. **Targeted budget repair:** when the total is outside ±10%, repair the section with the
   largest deviation from its *effective* target in the error's direction, not always the last
   section. The prompt states the exact word target that lands the total in range.
2. **Length-aware repetition repair:** pass the section's effective target and allowed range to
   the repetition repair. Afterwards, re-validate, and if the total is now outside range, run one
   targeted budget repair.
3. **Mixed failure** (word count + repetition): budget repair first, then the repetition repair
   if still needed, then a final validation. Each repair runs at most once per job, under its own
   cap constant.
4. Do not change the in-loop acceptance of over-budget sections (record your view in the design).

## Explicitly forbidden

Changing any pinned threshold (invariant 28). Server-side deletion, truncation or splicing of
lines or words (invariant 29). Unbounded loops (invariant 30).

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending: state the exact order of the global stage, the cap constants and their defaults, the
worst-case extra model calls per job, and how the target word count for the repaired section is
computed._

## Verification (required)

- The run 1 shape: a repetition repair inflates length → a targeted budget repair follows → the
  job completes.
- The 5-min shape: an overshoot concentrated in a middle section → the budget repair targets
  that section, not the last one.
- The mixed-failure path completes when both repairs succeed, and fails cleanly when they don't.
- Each cap set to 0 disables its step. The worst-case call count is asserted.
- Revert-and-confirm-failure on the run 1 shape test. Full suite. `ruff`.

## Evidence

_pending_
