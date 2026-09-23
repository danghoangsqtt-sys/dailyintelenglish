# Task 17.2 — Final-Section Sign-Off + `has_outro_last3` Diagnostic

- **Status:** not started
- **Owner:** Coder
- **Priority:** P2
- **Dependency:** 17.1 accepted
- **Controlling detail:** plan §3 "17.2"; the ENH-010 watch item

## Measured problem (do not re-derive)

Gate B-7 had 2 `has_outro: false` results (0 at B-6):
- **B1 run 4 is a runner false negative.** The sign-off ("It was a genuine pleasure talking to
  you both … we will be back very soon next episode") sits two lines before the last line.
- **Owner run 1 genuinely ends on a call to action with no goodbye.** A possible cause is 16.4's
  rule 5 (no repeated takeaway sentence) discouraging a closing recap.

## Allowed files

`prompts/script/section.txt`, `scripts/run_ai_operational_trial.py` (diagnostic field only),
`tests/test_script_pipeline.py`, and a runner test file named in the design section,
`CHANGELOG.md`.

## Required behaviour

1. `section.txt`'s `is_last_section` block states that the last section **ends with a short
   spoken sign-off/goodbye**, and that a one-sentence recap of the takeaway inside it is allowed.
   This exempts the final wrap-up from rule 5. Describe it abstractly, with no quoted example
   sign-off (N6 principle).
2. The runner records `has_outro_last3` (sign-off markers in any of the last 3 lines) next to
   `has_outro`. **The gate decision keeps using `has_outro`.**

## Design decisions (Coder, doc-first — commit before code, PM approves)

_pending_

## Verification (required)

The render test checks that the sign-off instruction appears only for the last section. A
`has_outro_last3` unit test uses the B-7 run 4 ending. Full suite, `ruff`.

## Evidence

_pending_
