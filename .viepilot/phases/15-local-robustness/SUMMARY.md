# Phase 15 Summary — Local Script Robustness (Structural Failures)

- **Status:** complete
- **Started:** 2026-09-22
- **Closed:** 2026-09-22
- **Controlling plan:** `docs/implementation/phase-15-local-robustness.md`
- **Full state/evidence log:** `PHASE-STATE.md` (this folder)

## Objective

The owner's first hands-on real run after Phase 14 closed died at section 3 on
`section_validation_failed: unknown speaker_id(s): ['ff5f20e0-417b-8d9f-752e844d46f0']`
against the real id `ff5f20e0-4082-417b-8d9f-752e844d46f0` (Alex) — the model dropped
one UUID group mid-generation. The PM verified this directly against `data/app.db` and
traced it to the same failure *class* (not the same exact bug) that had independently
killed samples at both Gate B-3 (consecutive-lines rule) and Gate B-4 (truncated UUID)
in Phase 14 — three real hits of the same two structural checks across three different
evidence sources. Phase 15 set out to eliminate that whole failure class — unknown
speaker ids and consecutive-lines-per-speaker violations — with deterministic,
non-generative fixes (never inventing a speaker or editing a line's words), then
re-measure with a Gate B-6 that added the owner's own failing configuration as an extra
sample.

## Tasks (15.1–15.4, chronological)

| Task | Description | Owner | Commits |
|---|---|---|---|
| 15.1 | Speaker aliases in the section contract (deterministic id resolution) | Coder | `a749224` (plan+accept), `ebd79e2` (impl) |
| 15.2 | Deterministic consecutive-lines fix (merge, never re-attribute) | Coder | `bf872da` (plan), `3381c21` (impl), `a08908a` (accept) |
| 15.3 | Trial runner per-gate evidence path + `set_job_metric` layering | Coder | `ccc160d` (plan), `d2c0d20` (impl) |
| 15.4 | **Gate B-6**: local only, owner's config as a 5th sample | PM | `d83d18d` (report + state + accept 15.3) |

15.5 (multi-script pace calibration) was explicitly optional, gated on the owner's word,
and was not started — see Residuals.

## Gate B-6 measurement (`docs/operations/phase15-gate-b6.md`)

| Gate | Script (B1 8-min) | Samples | Owner's config (A2/small_talk/10min, ×2) | Learning | Media | Verdict |
|---|---|---|---|---|---|---|
| Gate B-6 | 3/5 complete, 3/3 of those pass — both deaths are repetition (8-gram ratio 1.00%/1.42% after one repetition repair) | 4/4 complete | **2/2 complete**, with learning | 3/3 matrix + 2/2 owner | **PASS, first time** — 487.3 s ∈ [432, 528], A/V diff 0.00 s | **FAIL on script gate (repetition)**, PASS everywhere else |

**Zero structural failures in all 11 jobs run** (9 matrix + 2 owner-config) — Phase 15's
objective, met outright. `structural_fix` (Task 15.2's merge) never even needed to fire;
the deterministic id resolution and the merge fix removed the failure class before Gate
B-6 could exercise the repair path itself, which is the strongest possible result for a
robustness fix. The owner's own configuration — the exact one that died in their hands —
completed twice, with learning, on the same model, using nothing but speaker aliases in
the contract.

Media passed the duration gate for the first time across Phases 14–15 (487.3 s vs. Gate
B-5's 413.3 s, -4.3% FAIL): D13's pace calibration is now confirmed end to end at the B1
default speed on a script that landed near the 1,000-word target.

Repetition is the one failure class Phase 15 did not target and did not improve:
identical code produced 5/5 in Gate B-5 and 3/5 here, both B-6 deaths within 0.42 points
of the 1% threshold after Task 14.13's one bounded repetition repair. This is variance
in an untouched check, not a regression introduced by 15.1–15.3.

## Decision

Per the plan's own schedule and the PM's Gate B-6 report: Phase 15 achieved its stated
objective (the structural failure class — unknown speaker ids, consecutive-lines
violations — is gone from the evidence, 0/11 jobs) and closes here. Overall Gate B-6
verdict is FAIL, but strictly on the script gate's repetition count, a pre-existing and
separately-scoped residual, not on anything Phase 15 set out to fix. No threshold was
changed to reach this result.

## Known residuals (not fixed in this phase, flagged for whoever picks up the next one)

- **Repetition is now the dominant and variable residual failure class.** Both Gate B-6
  script deaths were within 0.42 points of the 1% repeated-8-gram threshold after one
  bounded repetition repair (Task 14.13) fired and wasn't enough. The PM's report lists
  three options, none started: allow a second bounded repetition repair targeting the
  next-worst section; strengthen the section prompt's "avoid" list with the specific
  framing phrases the model actually reuses (visible in the checkpoints); or accept a
  3-5/5 completion rate with the in-app Retry button, since a failed job costs ~2.5
  minutes and never corrupts anything.
- **Multi-script pace calibration (15.5) remains optional and undone.** It is no longer
  needed for the media gate to pass at B1 (Gate B-6 confirmed this), but the underlying
  calibration is still a single-script measurement (Phase 14's known residual); it
  stays open for other CEFR levels, on the owner's word only.
- **The C1 sample's `word_count_in_range`/`intro_present` runner checks are noisy, not
  wrong.** Gate B-6's C1 8-min sample failed the runner's word-count check by +11.4%
  while the pipeline's own ±10% gate passed on its own count — the two counters differ
  by a few tokens on hyphens/contractions. Disclosed in the gate report, not
  investigated further since samples are informational, not gating.
- **Legacy single-line `regenerate_line` (`script_service.py`) still echoes raw speaker
  ids**, not aliases — explicitly out of scope for Task 15.1, noted but untouched.

## Full history

See `PHASE-STATE.md` in this folder for the complete task-by-task execution record
(plans, commands, deviations, revert-and-confirm-failure evidence) and the individual
`tasks/task-15.*.md` cards for each task's full doc-first design record. The Gate B-6
report lives at `docs/operations/phase15-gate-b6.md`.
