# Task 17.4 — "Under" Direction via the Full Per-Section Path (ENH-010)

- **Status:** done
- **Owner:** Coder
- **Priority:** P0
- **Dependency:** Gate B-8 (17.3), plan Amendment C
- **Controlling detail:** `docs/implementation/phase-17-global-length-repair.md` Amendment C

## Measured problem (do not re-derive; see `docs/operations/phase17-gate-b8.md` §2)

Gate B-8's owner configuration (A2/small_talk/10 min) regressed from 2/2 (B-7) to 1/2. Owner
run 2, read from the trial checkpoints (read-only):
- Before the global stage, the total was **963**, under the range **[999, 1,221]**.
- `_worst_budget_section` correctly picked section 6 (91 words vs nominal 158, the largest
  under-deviation). New target: `1,110 − (963 − 91) = 238`.
- The "under" direction's plain `_repair_section` call (Task 17.1, C4 — the PM's own
  instruction, now withdrawn) returned **505 words** (2.1× target). The total became **1,377**,
  the single budget-repair slot was already spent, and the job failed.

Root cause: 17.1 C4 kept "under" on the old, direct `_repair_section` call ("repairs already
tend to grow text" — true on average across B-6/B-7, but not bounded), while "over" got the
calibrated full per-section path (`_run_section_pipeline`) specifically *because* that path's
in-loop length-only repair self-corrects an overshoot. "Under"'s repair overshooting needed
exactly that same self-correction, and didn't have it.

## Allowed files

Same as Task 17.1: `app/services/script_pipeline.py` (global validation stage + repair-prompt
inputs only), `app/core/constants.py`, `prompts/script/repair.txt`, `tests/test_script_pipeline.py`,
`tests/fixtures/ai/*`, `CHANGELOG.md`.

## Required behaviour (plan Amendment C, verbatim)

The global budget repair's "under" direction also reruns the chosen section through the full
per-section path (`_run_section_pipeline`, at the new target, with `avoid_phrases` from the
other sections), exactly like "over". The plain-repair branch is removed.

## Design decision

This is a small, fully-specified fix — the PM's Amendment C already states the exact change
(remove the direction branch, always call `_run_section_pipeline`) and the exact required test
shape (the real B-8 numbers). Per the PM's instruction, design and implementation are in this
one commit, not split into a separate doc-first commit; that's noted here rather than silently
skipping the usual two-commit gate.

**Code change:** `app/services/script_pipeline.py`'s global-stage budget-repair block
(`app/services/script_pipeline.py` around the `for _ in range(2):` loop) had an
`if target.direction == "over": ... else: ...` split, where the `else` ("under") built an
error message and called `_repair_section` directly on the existing (already-generated) lines.
That branch is deleted; the code that follows the `if` is unconditional now — both directions
call `_run_section_pipeline` with `target.new_target`, and `new_metrics["global_budget_direction"]`
is set from `target.direction` (was previously hardcoded `"over"` in that branch, `"under"` in
the deleted one).

No other change: the shared checkpoint-save/rebuild code after the if/else (already common to
both branches) is untouched. `_repair_section` itself is untouched (still used inside
`_run_section_pipeline` and by the repetition-repair path). The worst-case call count for the
global stage's budget slot stays 4 (generate + semantic repair + length repair, already
`_run_section_pipeline`'s existing ceiling, now reachable from either direction instead of only
"over") plus the repetition slot — unchanged from Task 17.1's own accounting, since "under" is
now using the exact same bounded path "over" already had.

**Consequence for two Task 17.1 tests** (not part of this task's required test, but broken by
the code change and fixed in this same commit — see `task-17.1.md`'s Amendment note):
`test_pipeline_targeted_budget_repair_under_brings_the_total_inside_tolerance` and
`test_pipeline_global_validation_still_fails_after_one_final_section_repair`.

**Required test** (`test_pipeline_under_budget_rerun_self_corrects_an_overshoot_gate_b8_shape`
in `tests/test_script_pipeline.py`): reproduces the real B-8 owner-run-2 shape verbatim — 7
sections, nominal `[159,158,159,158,159,158,159]` (sum 1,110 = target_words), actual checkpoint
words `[211,124,124,103,99,91,211]` (sum 963). Hand-derived the full carry cascade
(`compute_section_effective_target`/`compute_last_section_effective_target`) to determine which
of the 7 main-loop sections need their own one semantic repair to reach those exact final
numbers: sections 1–3 do (each final value falls outside that section's own carry-shifted ±15%
band but under the length-repair's 35%/50% carry-cap trigger, so accepted off-target after one
repair); sections 4–7 land inside their own effective-target band on the first attempt, no
repair. Verified by computing every section's `effective_target` and tolerance band by hand
before writing the fixture — all matched on the first test run.

`_worst_budget_section` picks section 6 (nominal deviation +67, the largest), new_target 238 —
both numbers match the real gate evidence exactly. The rerun is scripted as: a fresh generation
that's still far short (85 words, echoing the real defect's starting point), then one semantic
repair that overshoots to 505 words (matching the real 91→505 defect, and exceeding both the
±15% tolerance and the 35% carry-cap length-repair trigger), then one length-only repair landing
back inside the ±15% band (260 words). Asserts the job completes, the merged total (1,132) is
inside the global band, and the last 3 recorded calls are
`["script_section", "script_section_repair", "script_section_length_repair"]` all for section
6 — proving the rerun took the full-pipeline route, not a single plain-repair call.

**Revert-and-confirm-failure:** temporarily reintroduced the old "under" plain-repair branch
(direction-gated, calling `_repair_section` directly instead of `_run_section_pipeline`) and
re-ran the new test alone → failed exactly as expected (`global_validation_failed`, "total word
count 957 is outside ±10% of target 1110" — the plain repair consumed only the fresh-generate
mock as its one call and had no length-only follow-up to self-correct, reproducing the real B-8
defect). Restored the fix → the same test and the full file (96 tests) passed again.

## Evidence

- Code: `app/services/script_pipeline.py` — the `if target.direction == "over": ... else: ...`
  split removed; both directions now call `_run_section_pipeline` unconditionally,
  `global_budget_direction` set from `target.direction`.
- Tests: `tests/test_script_pipeline.py` — 1 new test
  (`test_pipeline_under_budget_rerun_self_corrects_an_overshoot_gate_b8_shape`), 2 existing
  tests updated for the new "under" mechanics (see `task-17.1.md`'s Amendment note). File total
  95 (post-17.2) → **96** after this task's 1 new test; targeted run confirmed 96 passed.
- Full suite: `./venv/Scripts/python.exe -m pytest -q` → **964 passed** (963 baseline after
  17.1+17.2 + 1 new test). No prior flake recurred.
- `ruff check .` → all checks passed.
- Revert-and-confirm-failure: above.
