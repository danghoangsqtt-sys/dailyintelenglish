# Task 16.4 — Repetition: Evidence-Driven Avoid List (ENH-009 step A)

- **Status:** not started
- **Owner:** Coder
- **Priority:** P0 (the core pipeline's remaining variable failure)
- **Dependency:** 16.3 accepted
- **Controlling detail:** plan §4 "16.4", invariants 24 and 27, owner decision D18;
  `.viepilot/requests/ENH-009.md`; `docs/operations/phase15-gate-b6.md`

## Measured problem (do not re-derive)

Gate B-6: script 3/5. Both deaths were `repeated 8-gram ratio` (1.00%, 1.42%) after the one
bounded repetition repair (Task 14.13). The same code scored 5/5 at B-5. Today's
`avoid_phrases` (`frequent_repeated_phrases`, top `SCRIPT_SECTION_AVOID_PHRASES_MAX = 8`)
lists only 8-grams that have **already** repeated. The second occurrence, the one that
creates the repeat, is never prevented.

## Allowed files

`prompts/script/section.txt`, `prompts/script/repair.txt`,
`app/services/script_pipeline.py` (avoid-phrase selection only),
`app/core/constants.py`, `tests/test_script_pipeline.py`, `tests/test_prompt_loader.py`,
`tests/fixtures/ai/*`, `CHANGELOG.md`.

## Required behaviour

1. **Evidence (the design section, reviewed by the PM before code):** from
   `data/quality_reviews/phase15/gate-b6/` (JSON + `trial-data/app.db`, **read-only**),
   extract the repeated 8-grams of every B-6 script run (failures, runs 2 and 5, first),
   with section attribution. Classify each as *framing* (openers, closers, transitions,
   topic restatements) or *content* (the topic's own key terms). Put the table here.
2. **Proposal:** close the "second occurrence" gap with a bounded mechanism. Candidates:
   - pass prior sections' opening and closing lines as "don't reuse this framing";
   - a static rule block in `section.txt` against the observed framing *patterns*.

   Recommend one, state the prompt-size bound, and trace every added rule or phrase to a
   row of the evidence table (invariant 27).
3. No threshold change, and no new repair pass (that is 16.6, conditional).

## Explicitly forbidden

Changing `SCRIPT_MAX_REPEATED_8GRAM_RATIO` or any other pinned threshold. Adding the topic's
content words to an avoid list. Writing to any gate evidence DB.

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending — evidence table + recommendation_

## Verification (required)

Unit tests for the selection logic (bound, empty case, dedupe). A render test of
`section.txt` with the new block. Prompt-contract tests pass. Revert-and-confirm-failure on
the selection test. Full suite. `ruff`. Real-model effect is measured by the PM in 16.5
(Gate B-7), not here.

## Evidence

_pending_
