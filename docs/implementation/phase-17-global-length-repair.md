# Phase 17 Implementation Plan — Budget-Aware Global Validation (ENH-010)

**Status:** Controlling plan, PM, 2026-09-23. The owner opened this phase via `/vp-evolve ENH-010`
right after Phase 16 closed (D20).
**Predecessors:** the Phase 13–16 plans (still controlling where not amended), ADR-001 (+A1, A2).
**Request:** ENH-010 (`.viepilot/requests/ENH-010.md`), plus the outro watch item logged with it.

## 0. Correction to the Gate B-7 report (PM, before planning)

`docs/operations/phase16-gate-b7.md` §3.2 and ENH-010 said the pipeline has "no repair for a
global total overshoot". **That is wrong.** Task 14.3 item 6 already runs one budget repair
(`SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS`) at the global stage when the total is outside
±10%. It rewrites only the **last** section to absorb the overshoot. Reading the B-7 checkpoints
(`trial-data/app.db`, read-only) shows what actually happened.

| Failed job | Sections: words / effective target | Global stage, in order | Why it died |
|---|---|---|---|
| B1 8-min run 1 | 172/200, **219/228**, 243/270, **407/338**, 83/75 → 1,124 | 1st validation: total **inside** ±10%, repetition only → budget repair skipped → **repetition repair on section 2** → re-validation: **1,124** + rep 1.07% | The repetition repair regenerated section 2 **longer** and did not fix the repetition. Nothing re-checks length after it. |
| B1 5-min sample | 43/208, **345/292**, **315/237** → 703 | 1st validation: total 703 > 687 → **last-section budget repair** asked for 237 → model returned 315 | The last section can't absorb an overshoot that sits mostly in section 2, and a 9B model rarely cuts about 25% on request. |

In both jobs, a section still over its budget after the in-loop repair was accepted anyway
(section 4: 407 vs 338, +20%; section 2 of the 5-min job: 345 vs 292, +18%). Its budget
errors are discarded (`_budget_errors`).

## 1. Goal

Make the global validation stage **budget-aware and ordered**, so that a repair never pushes the
total out of range without the total being checked again, and so that the length repair targets
the section that actually overshot. The success test is a new gate: B1 8-min **5/5 complete**,
with no regression.

## 2. Invariants (in addition to Phase 13–16)

28. **Thresholds unchanged.** `SCRIPT_GLOBAL_WORD_TOLERANCE`, `SCRIPT_SECTION_WORD_TOLERANCE`,
    `SCRIPT_MAX_REPEATED_8GRAM_RATIO`, `SCRIPT_MAX_CONSECUTIVE_LINES_PER_SPEAKER` and the speaker
    balance limits stay pinned.
29. **No server-side content deletion or invention.** Length is fixed only by model repairs with a
    word target. The server never drops, truncates or splices lines to hit a number (Phase 15
    invariant 21 extended to length).
30. **Bounded.** Every global-stage repair has its own cap constant (0 disables it without a
    revert). The worst case adds a fixed, documented number of model calls per job.

## 3. Tasks

Order: **17.1 → 17.2** (Coder, doc-first, PM approves each card's design before code)
**→ 17.3** (PM gate, Coder idle) **→** close-out.

### 17.1 — Budget-aware global stage (ENH-010, P0, Coder)

**Allowed files:** `app/services/script_pipeline.py` (global validation stage and the
repair-prompt inputs only), `app/core/constants.py`, `prompts/script/repair.txt`,
`tests/test_script_pipeline.py`, `tests/fixtures/ai/*`, `CHANGELOG.md`.

**Required behaviour (the design details are the Coder's, in the card):**
1. **Targeted budget repair.** When the total is outside ±10%, repair the section with the
   largest deviation from its **effective** target, in the direction of the error. Today the
   code always repairs the last section. The prompt states that section's exact word target,
   computed so the total lands inside range given the other sections as they stand.
2. **Length-aware repetition repair.** The repetition repair (Task 14.13) passes the section's
   effective word target and allowed range into the repair prompt. Afterwards, the total is
   re-validated, and if it is now outside ±10%, one targeted budget repair (item 1) runs.
3. **Mixed failures get a path.** A failure of word count plus repetition (today: straight to
   `global_validation_failed`) runs the budget repair first, then the repetition repair if
   repetition still fails, then a final validation. Each repair runs at most once per job,
   each under its own cap constant (invariant 30).
4. A section's in-loop over-budget acceptance is **not** changed in this task. The global stage
   is where the total is enforced. Record in the card whether any B-7 evidence argues otherwise.

**Verification:** tests that reproduce **both B-7 shapes** with scripted fake-router outputs
(the run 1 shape: a repetition repair that inflates length, which must be followed by a budget
repair and complete; the 5-min shape: an overshoot concentrated in a middle section, where the
budget repair must target that section and not the last). Also: the mixed-failure path; each cap
set to 0 disables its step; the worst-case call count is asserted. Revert-and-confirm-failure on
the run 1 shape. Full suite, `ruff`.

### 17.2 — Final-section sign-off (outro watch item, P2, Coder)

**Allowed files:** `prompts/script/section.txt`, `scripts/run_ai_operational_trial.py`
(diagnostic field only), `tests/test_script_pipeline.py`,
`tests/test_run_ai_operational_trial.py` (if present; otherwise name the test file in the card),
`CHANGELOG.md`.

**Required behaviour:**
1. `section.txt`'s `is_last_section` block states explicitly that the last section **ends with a
   short spoken sign-off/goodbye**, and that a one-sentence recap of the takeaway inside that
   sign-off is allowed. This carves the recap out of rule 5 for the final wrap-up only. The
   evidence trace is B-7 owner run 1, which ended on a call to action with no goodbye.
2. The runner records an **additional diagnostic** `has_outro_last3` (sign-off markers anywhere
   in the last 3 lines) next to the existing `has_outro`. **The gate decision still uses the
   existing field**, so the goalposts don't move. The PM reports both.

**Verification:** the render test confirms the sign-off instruction appears only when
`is_last_section`. A runner unit test covers `has_outro_last3` with the B-7 run 4 ending
(sign-off two lines before the last). Full suite, `ruff`.

### 17.3 — Gate B-8, local only (PM, Coder idle)

Same protocol as Gate B-7 (5 × B1 8-min + 4 samples + learning + media + the owner's
configuration ×2), fresh trial DB. **Script gate: B1 8-min 5/5 complete.** Also required: no
regression on structural 0, learning, media duration or A/V, and repetition 0 deaths. Report:
`docs/operations/phase17-gate-b8.md`. If the gate fails, the PM reports with evidence and the
owner decides (no automatic follow-up task).

## 4. Stop conditions and rollback

Same as Phase 16 §5. Each new global-stage step has a cap constant, and setting it to 0 restores
today's behaviour for that step without a revert.

## 5. Two-session protocol

Unchanged from Phase 16 §6: the PM is Claude Opus (session "Phân tích mã nguồn dự án"); the
Coder is Claude Sonnet; `SendMessage` is the live channel; git is the record. The Coder owns
`.viepilot/phases/17-global-length-repair/**` after the handover commit. Baseline: **956/956**,
`ruff` clean, real DB 7 projects.
