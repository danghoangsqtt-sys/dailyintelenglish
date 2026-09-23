# Phase 17 Specification — Budget-Aware Global Validation (ENH-010)

The controlling contract is `docs/implementation/phase-17-global-length-repair.md`.

## Goal

Make the script pipeline's global validation stage budget-aware:
- a targeted budget repair of the most over- or under-budget section;
- a length-aware repetition repair that is followed by a re-check;
- a repair path for mixed word-count + repetition failures.

It also makes the last section end with a sign-off. The trigger is the two Gate B-7 failures,
re-diagnosed in plan §0.

## Required gates

- **Doc-first:** each card's *Design decisions* section is committed and PM-approved before code.
- **Invariant 28:** all script thresholds stay pinned.
- **Invariant 29:** no server-side deletion, truncation or splicing of content to hit a word count.
- **Invariant 30:** every new global-stage repair is capped by its own constant (0 disables it),
  with a documented worst-case call count.
- **Gate B-8 (17.3):** B1 8-min 5/5 complete, no regression, repetition 0 deaths.

## Session partition

As in Phase 16: the PM owns `docs/**`, TRACKER, ROADMAP, HANDOFF and `.viepilot/requests/**`.
The Coder owns `app/**`, `tests/**`, `scripts/**`, `prompts/**`, `CHANGELOG.md`, and this folder
after the handover commit. Only the PM runs gates.
