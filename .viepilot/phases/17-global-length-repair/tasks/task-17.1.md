# Task 17.1 — Budget-Aware Global Stage (ENH-010)

- **Status:** in_progress
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

**Current code (for reference).** Today's global stage is two independent, non-nested `if`
blocks after `validate_global`: (1) `if hard_errors and last_section_spec and CAP_BUDGET>0
and total_outside:` repairs **only the last section**, targeting
`max(1, target_words - words_before_last_section)`, then re-validates *inside that same
block*; (2) separately, `if hard_errors and CAP_REPETITION>0 and all(err.startswith("repeated
8-gram ratio") for err in hard_errors):` repairs the worst-by-occurrence-count section (via
`find_repeated_8grams_by_section`), passing only `["repeated phrase used elsewhere...", ...]`
as the repair's error checklist (the section's target/range *is* already rendered into
`repair.txt`'s unconditional "Section Being Repaired" block via `_repair_section`'s existing
`target_words`/`measured_words`/`delta` context — but it is never listed as something to *fix*,
just ambient information), then re-validates. Because these are two independent top-level
`if`s (not a shared loop), block (1) only ever fires when the *original* validation was a pure
budget failure, and block (2) only ever fires when the *original* (or, coincidentally, the
post-repair) hard_errors are pure repetition — there is no path that deliberately runs both
in one job. That gap is exactly run 1's bug: original hard_errors = repetition-only, so block
(1) never runs at all; block (2)'s repair inflates section 2; nothing re-checks length
afterward.

**New design: one shared, ordered, two-slot loop**, replacing both blocks:

```
hard_errors, warnings = validate_global(all_lines, ...)   # unchanged call, unchanged thresholds
budget_repair_used = False
repetition_repair_used = False

for _ in range(2):  # at most 2 iterations ever do real work; a 3rd is a no-op break
    if not hard_errors:
        break
    if _has_budget_error(hard_errors) and not budget_repair_used and SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS > 0:
        <targeted budget repair — see "Target section selection" below>
        budget_repair_used = True
        hard_errors, warnings = validate_global(all_lines, ...)
        continue
    if _has_repetition_error(hard_errors) and not repetition_repair_used and SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS > 0:
        <length-aware repetition repair — see below>
        repetition_repair_used = True
        hard_errors, warnings = validate_global(all_lines, ...)
        continue
    break

if hard_errors:
    fail("global_validation_failed", hard_errors); return
```

Budget is always checked *before* repetition on every pass (matches required behaviour #3's
"budget repair first, then repetition"), but each repair type can only ever *fire* once
(`*_repair_used` flags — this is what makes "each repair runs at most once per job" true
regardless of which order the errors actually appear in). This one loop reproduces **both**
required behaviours from a single mechanism:
- **Mixed-from-the-start** (hypothetically): pass 1 sees both errors, budget checked first →
  repairs budget, re-validates. Pass 2: if repetition still present → repairs repetition,
  re-validates. Pass 3: both slots used → break → final validation. Exactly required
  behaviour #3's stated order.
- **Repetition-only-from-the-start, becomes mixed after repair (run 1's actual shape)**: pass 1
  sees only a repetition error → the budget branch's condition fails (no budget error yet) →
  falls through to the repetition branch → repairs it (now length-aware — see below),
  re-validates. Pass 2: the repetition repair inflated the total → budget error now present,
  and the budget slot was **never used** (its condition never matched in pass 1) → fires now.
  Exactly required behaviour #2's "afterward, if now outside range, run one targeted budget
  repair."
- **Budget-only-from-the-start (the 5-min shape)**: pass 1 repairs budget (now *targeted* at
  the worst section, not always the last), re-validates. If that alone clears it, pass 2 finds
  no errors and breaks immediately.

No new cap constant. `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS` and
`SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS` (both already exist, both already default to 1, both
already documented as "0 disables the pass without a code revert") continue to be each
repair's own cap — reused exactly as-is, not duplicated. `_has_budget_error`/
`_has_repetition_error` are small string-prefix checks (`error.startswith("total episode word
count")` / `error.startswith("repeated 8-gram ratio")`), mirroring the existing
`all(error.startswith("repeated 8-gram ratio") ...)` check already in the code today.

**Worst-case extra model calls per job: 2** (one targeted budget repair + one length-aware
repetition repair), a fixed, documented ceiling independent of episode length — up from
today's de-facto worst case of 1 (the two old blocks could not both deliberately fire in the
same job). Both remain independently disable-able via their existing constant set to 0.

**Target section selection (required behaviour #1).** Today's per-section loop already
computes and checkpoints `target_effective` and `words` for every section (visible in each
checkpoint's `metrics_json`, confirmed directly in the B-7 evidence table in plan §0). Rather
than thread new local state through the per-section loop (out of scope — "global validation
stage... only"), the budget repair fetches fresh checkpoints the same way the *existing*
repetition-repair code already does
(`ai_job_service.get_valid_checkpoints` → filter `stage == "section"` → parse each
`metrics_json`). A new helper, `_worst_budget_section(section_checkpoints, outline,
total_words, target_words) -> tuple[int, list[SectionLineOut], int] | None` (section_index,
current lines, new_target):
1. `direction = "over" if total_words > target_words else "under"` (unambiguous — `hard_errors`
   already contains the budget error only when `total_words` is strictly outside
   `target_words ± SCRIPT_GLOBAL_WORD_TOLERANCE`, never exactly at the boundary).
2. For every section's checkpoint, `deviation = words - target_effective` (over) or
   `target_effective - words` (under). Picks the section with the **largest** deviation;
   ties broken by lowest `section_index` (stable — sections are scanned in index order, and
   `max()` keeps the first of equal maxima).
3. `new_target = max(1, target_words - (total_words - target_section_words))` — generalizes
   today's last-section-only formula (`max(1, target_words - words_before_last_section)`) to
   whichever section was picked: *land the total exactly on the nominal target*, given every
   other section's words stay as they are. Same `max(1, ...)` floor as today, no new clamp.
   The repair prompt states this exact number via `effective_spec = worst_spec.model_copy
   (update={"target_words": new_target})`, identical mechanism to today's
   `adjusted_spec`/`last_section_spec.model_copy(...)`.
4. The repair's error checklist states the total, the target, and names the section:
   `f"total episode word count {total_words} is outside ±10% of target {target_words} words --
   this section is the most {direction}-budget by {abs(deviation)} words"` (generalizes today's
   "...this is a final-section budget repair" message).

**Length-aware repetition repair (required behaviour #2).** Unchanged section selection
(`find_repeated_8grams_by_section`'s existing occurrence-count attribution). The only change:
the errors list gains one more entry alongside the existing per-phrase ones:
`f"keep this section's length between {min_words} and {max_words} words (target
{effective_target}) while removing the repetition -- do not let fixing the repetition push the
length outside this range"`, where `min_words`/`max_words` use the exact same formula
`_generate_section` already uses for its own prompt
(`effective_target * (1 ± SCRIPT_SECTION_WORD_TOLERANCE)`). This makes the length constraint an
explicit checklist item (something the repair prompt's `## Validation Errors To Fix` loop
states as a thing to fix), not just ambient text the model may or may not weight — which is
exactly the gap run 1 exposed: `repair.txt` already renders the section's target/delta
unconditionally, but the errors list is the only place a repair reliably prioritizes.
`prompts/script/repair.txt` itself needs no change: this is an addition to the *data* passed
into the existing `errors` loop, not a template change.

**Mixed failure (required behaviour #3).** Not a separate code path — the emergent behaviour
of the shared loop above when both error types are present at once. No separate handling
needed.

**Item 4 — in-loop acceptance of over-budget sections (not changed in this task, per
explicit instruction; recording my view as asked).** B-7's evidence (both jobs accepted an
over-budget section in-loop, discarding its `_budget_errors`) is the *source* of what this
task now fixes reactively at the global stage, so it's fair to ask whether tightening
acceptance in-loop would be a better fix. I don't think B-7's evidence argues for that change:
forcing another in-loop repair attempt until a section complies risks an unbounded or
open-ended retry loop (or repeatedly trading one property for another — a repair chasing word
count could reintroduce repetition, structural issues, or speaker imbalance), which is exactly
what invariant 30's "bounded" requirement and the existing carry-forward design are built to
avoid. The carry mechanism already means one section's overshoot is *expected* to sometimes
need absorbing elsewhere — the fix belongs where the *total* is actually enforced (the global
stage), targeting whichever section is worst once every section is known, which is what this
task does. Leaving the in-loop behaviour alone is deliberate, not an oversight.

**Refactor note.** A single new helper, `_load_section_checkpoints(db, job_id) ->
dict[int, dict]` (section_index → checkpoint row), replaces the ad-hoc
`get_valid_checkpoints` + filter-by-stage call that's currently inlined only in the
repetition-repair branch — both the new budget-repair path and the existing repetition-repair
path call it, removing the duplication rather than adding a second copy.

**Test plan**
- `tests/test_script_pipeline.py`:
  1. **Run 1 shape**: a repetition-only failure at first validation (one section's checkpoint
     deliberately contains a within-section repeated 8-gram, total in range) whose scripted
     repetition-repair response is *longer* than the target, pushing the total over ±10%.
     Asserts: the repetition repair fires (its prompt contains the new length-checklist entry),
     then a targeted budget repair fires on whichever section is now worst, the job completes,
     and exactly 2 extra repair calls happened (repetition + budget, in that order).
  2. **5-min shape**: total over budget at first validation, with the overshoot concentrated in
     a *middle* section (not the last). Asserts the budget repair's prompt targets that middle
     section specifically (by objective/target_words in the captured prompt), not the last
     section, and the job completes.
  3. **Mixed-from-the-start**: first validation has both a budget error and a repetition error.
     Asserts budget repairs first, then repetition, in that order (2 calls), and completes.
  4. **Each cap at 0 disables its step**: `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 0` on
     the 5-min shape → job fails with the budget error still present, zero extra repair calls.
     `SCRIPT_PIPELINE_MAX_REPETITION_REPAIRS = 0` on the run 1 shape → job fails with the
     repetition error still present, zero extra repair calls.
  5. **Worst-case call count**: the mixed-from-the-start test (3) doubles as this — asserts
     `gemini.call_count` equals exactly `outline + sections + 2` (never more).
  6. A repair failing to fully fix its error (e.g. the budget repair's own response is still
     out of range) → the loop's slot is already spent → falls through to final validation →
     fails cleanly with `global_validation_failed`, not a crash or a silent pass.
- Revert-and-confirm-failure target: test 1 (the run 1 shape) — temporarily restore the old
  "only the last section, no re-check" behavior, confirm it fails (job ends
  `global_validation_failed` instead of `complete`, or repairs the wrong section), then restore.
- Full suite, `ruff`.

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
