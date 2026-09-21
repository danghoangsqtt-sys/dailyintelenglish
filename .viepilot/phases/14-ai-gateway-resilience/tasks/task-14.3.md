# Task 14.3 — Running Section Budget; Hard Gate Only at the Global ±10%

- **Status:** done
- **Owner:** Coder
- **Priority:** P1
- **Dependency:** 14.2 done (repair telemetry must exist first so this change is
  measurable in 14.4b)
- **Controlling detail:** plan §4.3, §5, §6 Task 14.3

## Governance note — read before anything else

**This task is not a threshold relaxation.** The product standard is ±10% of the total
(720–880 words for B1 eight minutes, `SCRIPT_GLOBAL_WORD_TOLERANCE = 0.10`) and it stays
the only hard word-count gate. `SCRIPT_SECTION_WORD_TOLERANCE = 0.15` also keeps its
value; it changes *role* — from a job-killing gate to the trigger for the one repair
pass and the signal for carrying drift forward. If you find yourself editing either
constant, or wanting ±25%, **stop and ask the PM** — that is a plan stop condition.
A constants-pin test added in this task makes any such edit fail CI.

## Measured problem (do not re-derive)

Per-section pass rate 66.7% (18/27), five consecutive passes needed → 13.2% predicted vs
11% observed job pass rate. The one completed job: sections `[137,152,163,164,165]` =
781/800 (−2.4%) — errors cancel at the total. Accepted sections mean 145.9 vs 160 (−9%,
σ 19.5). Failing sections went both ways (41 … 252 words against ~160).

## Allowed files

`app/services/script_pipeline.py`, `app/core/constants.py`,
`prompts/script/section.txt`, `prompts/script/repair.txt`,
`tests/test_script_pipeline.py`, `tests/fixtures/ai/*`.

## Required behaviour

1. Nominal targets: unchanged (`plan_sections`, outline call, outline prompt untouched).
2. Effective target for section *i*:
   `effective_i = clamp(nominal_i + carry, nominal_i × (1 − SCRIPT_SECTION_CARRY_CAP),
   nominal_i × (1 + SCRIPT_SECTION_CARRY_CAP))`, `SCRIPT_SECTION_CARRY_CAP = 0.35`.
   Residual beyond the clamp stays in `carry`. After acceptance:
   `carry = carry + (effective_i − actual_words_i)`.
3. Last section: `effective_last = clamp(target_words − words_so_far,
   nominal_last × (1 − SCRIPT_LAST_SECTION_CARRY_CAP), nominal_last × (1 +
   SCRIPT_LAST_SECTION_CARRY_CAP))`, `SCRIPT_LAST_SECTION_CARRY_CAP = 0.5`.
4. Split `validate_section` into structural hard checks (no lines, unknown speaker,
   consecutive-lines limit) and a word-deviation check against the **effective** target
   with `SCRIPT_SECTION_WORD_TOLERANCE`. Either triggers the single repair pass
   (unchanged budget). After repair: structural error → `section_validation_failed`
   (unchanged); schema-invalid → unchanged failure; word deviation only → **accept**,
   log `script_section_accepted_off_target job_id= section= effective= actual=`, carry
   the drift.
5. `validate_global` unchanged (hard ±10%).
6. Final-section budget repair: if the merged total is outside ±10% after the last
   section, regenerate the last section once via the repair prompt with
   `target_words = target_words − words_before_last_section`, count it as a repair
   (`record_generation_call(is_repair=True)` → `repair_count += 1`), overwrite the last
   section's checkpoint (upsert), re-run `validate_global`; still outside →
   `global_validation_failed`. Bounded by `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 1`.
   Total repair calls per job ≤ `num_sections + 1`.
7. Resume: recompute `carry` from checkpointed sections' actual word counts against the
   outline's nominal targets; no new column, no new stage.
8. Prompts receive the effective target in the existing `target_words` variable; a
   short sentence that the budget is adjusted for earlier sections is allowed. No other
   prompt change.
9. Checkpoint `metrics_json` (from 14.2) now carries the real `target_effective`.
10. The −9% undershoot is **not** compensated here. Record your reasoning in this card
    (open question, decided with 14.4b data).

## Explicitly forbidden

- Editing `SCRIPT_GLOBAL_WORD_TOLERANCE` or `SCRIPT_SECTION_WORD_TOLERANCE`.
- Removing the structural section checks or the global speaker-balance/duplicate/8-gram
  checks.
- More than one repair per section or more than one final budget repair per job.
- Touching `ai_job_service.py`, `ai_worker.py`, or the outline prompt (not allowed here;
  ask the PM if genuinely needed).

## Verification (all must be in the diff)

1. Pure-function tests: effective target/clamp/residual carry; last-section rule;
   carry recomputation from checkpoints.
2. Constants-pin test: `SCRIPT_GLOBAL_WORD_TOLERANCE == 0.10` and
   `SCRIPT_SECTION_WORD_TOLERANCE == 0.15`. Revert-and-confirm-failure by temporarily
   editing one value; record the output.
3. E2E (FakeProvider): five sections each outside ±15% of nominal, total inside ±10%
   → `complete`; `repair_count` equals the number of per-section repairs; every
   checkpoint `metrics_json` has nominal/effective/actual/deviation.
4. E2E: total outside ±10% after all sections → one final-section repair brings it
   inside → `complete`, `repair_count` one higher, last checkpoint overwritten.
5. E2E: still outside after the final repair → `global_validation_failed`; prior script
   untouched; repair calls == `num_sections + 1` at most.
6. E2E: structural error surviving repair → `section_validation_failed` (unchanged).
7. E2E: interrupted after section 2 with drift, resumed → same total as uninterrupted.
8. Existing 13.4 tests updated where they asserted the old per-section hard fail, with a
   one-line justification per changed assertion in this card.
9. `ruff` clean; full suite green.

## Rollback

`SCRIPT_SECTION_CARRY_CAP = 0.0` and `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 0`
restore fixed targets; the accept-and-carry behaviour itself is reverted by git only.

## Execution record (Coder fills in)

- Plan/decisions before code (including the −9% question):
  - **Functions added (pure, unit-testable directly):**
    - `clamp(value, low, high) -> float`: generic bound helper.
    - `compute_section_effective_target(nominal: int, carry: float) -> int`:
      `round(clamp(nominal + carry, nominal*(1-SCRIPT_SECTION_CARRY_CAP),
      nominal*(1+SCRIPT_SECTION_CARRY_CAP)))` -- item 2, non-last sections.
    - `compute_last_section_effective_target(nominal_last, target_words,
      words_so_far) -> int`: `round(clamp(target_words - words_so_far,
      nominal_last*(1-SCRIPT_LAST_SECTION_CARRY_CAP),
      nominal_last*(1+SCRIPT_LAST_SECTION_CARRY_CAP)))` -- item 3.
    - `validate_section_structure(lines, known_speaker_ids) -> list[str]`: exactly
      today's structural checks (no lines / unknown speaker / consecutive-lines
      limit), extracted verbatim from the current `validate_section`.
    - `validate_section_word_budget(lines, target_words) -> list[str]`: exactly
      today's word-count check, extracted verbatim; returns `[]` for empty
      `lines` (the "no lines" case is a structural error, not a budget one --
      avoids a redundant second error for the same root cause).
    - `validate_section(lines, target_words, known_speaker_ids) -> list[str]`
      **kept**, redefined as `validate_section_structure(...) +
      validate_section_word_budget(...)` -- byte-for-byte same error set as
      today for every existing pure-function test (all of which assert with
      `any(... in error for error in errors)`, so the reordered concatenation
      -- structural first, then budget, vs today's budget-then-structural --
      does not break them; confirmed no test indexes `errors[0]` directly).
  - **Orchestrator (`_run_script_job`) changes:**
    - `_generate_section`/`_repair_section` keep their existing signatures
      (already carry `db`/`job_id` from Task 14.2) but now return a 3-tuple
      `(lines, structural_errors, budget_errors)` instead of `(lines, errors)`,
      using the two split validators above. The **effective** target is
      threaded through by passing a *modified* `OutlineSectionSpec` (via
      `section_spec.model_copy(update={"target_words": effective_target})`)
      into these functions instead of the outline's original spec -- so
      neither function needs a new parameter, and the section/repair prompts
      automatically receive the effective target through the existing
      `target_words` template variable (item 8) with zero template-plumbing
      changes.
    - Before the per-section loop, one pass over `outline.sections` recomputes
      `carry` (float, starts at 0.0) and `words_so_far` (int, starts at 0) from
      any already-checkpointed sections (resume case) -- see the "Resume/carry"
      decision below. For a fresh job this loop is a no-op (no checkpoints
      exist yet beyond the outline).
    - Inside the loop, for each **not-yet-checkpointed** section: compute
      `effective_target` (last-section formula if `position == total_sections`,
      else the carry formula); build `effective_spec`; call
      `_generate_section(..., effective_spec, ...)`. If `structural_errors or
      budget_errors`: repair once via `_repair_section(..., effective_spec,
      ...)` (unchanged one-repair budget). After repair (or immediately, if no
      repair was needed): `structural_errors` (from whichever pass ran last)
      → `section_validation_failed` (unchanged, matches "schema-invalid →
      unchanged failure" since a schema failure surfaces as a structural error
      via `validate_section_structure([])`'s "no lines" check). Otherwise
      (only `budget_errors` survived a repair) → **accept**, log
      `script_section_accepted_off_target job_id=... section=... effective=...
      actual=...`, and let it through -- this is the actual behavior change
      item 4 asks for. `carry += effective_target - actual_words` after every
      accepted non-... section (see below for why the last section also
      updates it, harmlessly, even though nothing reads it afterward).
    - `last_section_spec`/`last_section_lines` are tracked whenever
      `position == total_sections`, in **both** the resumed-from-checkpoint
      branch and the freshly-generated branch, so the final-budget-repair step
      below has the right data regardless of whether the last section was
      generated this run or a prior one.
  - **Final-section budget repair (item 6):** after `validate_global` runs (as
    today), if `hard_errors` is non-empty, recompute `total_words` via
    `section_word_count(all_lines)` and check the **word-count condition
    specifically** (not "any hard error") against `SCRIPT_GLOBAL_WORD_TOLERANCE`.
    Only when *that specific* condition is true (and
    `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS > 0` and a last section exists)
    is the one extra repair attempted: reuse `_repair_section` again (not a new
    function) with `adjusted_spec = last_section_spec.model_copy(update=
    {"target_words": target_words - words_before_last_section})`, `is_repair`
    already `True` inside `_repair_section`'s own `_call_router` wiring so
    `repair_count` increments correctly. A structural error from this repair
    still hard-fails (`section_validation_failed`); otherwise the last
    section's checkpoint is overwritten (`save_checkpoint` already upserts on
    `(job_id, stage, section_index)`) with fresh metrics, `all_lines` has its
    trailing `len(last_section_lines)` entries replaced, and `validate_global`
    re-runs once. Still failing → `global_validation_failed` (unchanged code,
    now possibly reached only after the extra attempt). This correctly leaves
    a *non*-word-count hard error (e.g. speaker balance) to fail immediately
    without wasting a repair call on a problem the word-budget repair can't
    fix -- the final re-check of `hard_errors` after the repair still catches
    it if it persists.
  - **Resume/carry -- explicit deviation from the plan's literal wording,
    flagged rather than silently decided:** §4.3 item 7 says carry is
    recomputed "from the checkpointed sections' actual word counts against the
    outline's **nominal** targets". Taken literally (`carry = Σ(nominal_i −
    actual_i)`), this would NOT reproduce the same `carry` an uninterrupted run
    would have reached at the same point, because the uninterrupted run's own
    formula (item 2) is `carry = carry + (effective_i − actual_i)`, which uses
    each section's **effective** target, not nominal -- and once carry starts
    accumulating, `effective_i != nominal_i` in general. Verification item 7
    requires "interrupted-then-resumed job recomputes carry from checkpoints
    and reaches the same total as an uninterrupted run", which the literal
    nominal-based formula cannot satisfy in general (only coincidentally, when
    a section's effective target happened to equal its nominal one). Since
    Task 14.2 already stores `target_effective` on every section checkpoint's
    `metrics_json`, and Task 14.3 (this task, item 9) makes that field carry
    the *real* effective target, the resume recomputation reads
    `target_effective` from each checkpoint (falling back to that section's
    nominal target only if a checkpoint predates this shape, which cannot
    happen within a single pipeline version) and applies the *same* formula as
    the live path: `carry = Σ(target_effective_i − actual_i)`. This satisfies
    the literal testable requirement (same total) using data the plan's own
    item 9 already puts within reach; reported here per the plan's own
    "record your reasoning" instruction for open questions, not applied
    silently.
    - **PM review (2026-09-21): agreed**, with the mathematical justification
      that the two approaches are the same value by construction -- `carry_0 =
      0; effective_i = clamp(nominal_i + carry_{i-1}, ...); carry_i =
      carry_{i-1} + (effective_i − actual_i)` is deterministic, so replaying it
      from the outline's nominal targets (checkpoint 0) plus each checkpoint's
      actual word count reproduces the exact same `effective_i`/`carry_i`
      sequence a live run would have produced; reading the cached
      `target_effective` off each checkpoint is the same value, just already
      computed, and more honest (it reflects the number actually sent to the
      model, not a value re-derived after the fact). Two conditions attached,
      both implemented:
      1. **Fallback:** if a checkpoint's `metrics_json` is empty or lacks
         `target_effective` (a row from before this task, or a genuinely empty
         `"{}"`), that section's `effective_i` in the replay falls back to its
         own **nominal** target (`section_spec.target_words`) -- resume must
         never crash on older data, and this is the mathematically correct
         substitution (a section with no recorded drift contributes
         `effective_i == nominal_i` to the replay, i.e. as if `carry` had been
         0 going into it).
      2. **Equivalence test:** verification item 1's pure-function tests
         include one that, for the same nominal+actual sequence, computes
         `carry` two ways -- (a) a pure "replay from nominal" helper that
         calls `compute_section_effective_target` forward through the whole
         sequence using only nominal targets and actual word counts (no
         checkpoint I/O), and (b) reading `target_effective` values already
         computed/stored -- and asserts they produce an identical final
         `carry`. This is evidence the two are one formula, not two sources of
         truth that could silently diverge.
  - **−9% systematic undershoot (item 10):** **not compensated in this task**,
    per the plan's explicit instruction. No change to `plan_sections`, the
    outline prompt, or any target-inflation logic. This stays an open question
    for 14.4b: only a second Gate B run under the *new* accept-and-carry
    behavior can show whether the −9% figure (measured under the old
    hard-fail-per-section regime, where under-shooting sections were
    disproportionately likely to survive the ±15% gate at all -- the 66.7%
    pass rate was already a survivorship-filtered sample) still holds once
    off-target sections are no longer silently excluded from the "accepted"
    population. Requesting extra words now, without that data, risks
    overcorrecting into a systematic overshoot instead.
  - **Constants added** (`app/core/constants.py`, Task 14.3 comment):
    `SCRIPT_SECTION_CARRY_CAP = 0.35`, `SCRIPT_LAST_SECTION_CARRY_CAP = 0.5`,
    `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS = 1`. A constants-pin test
    asserts `SCRIPT_GLOBAL_WORD_TOLERANCE == 0.10` and
    `SCRIPT_SECTION_WORD_TOLERANCE == 0.15` (unchanged, per the governance
    note) -- revert-and-confirm-failure done by temporarily editing one value
    (see below).
  - **Prompts** (`prompts/script/section.txt`, `prompts/script/repair.txt`):
    read both in full before deciding. Both already phrase the budget as
    "Target length: about `{{ target_words }}` spoken words (stay within
    ±15%)" -- generic, never claims this number equals the outline's original
    per-section figure, and `target_words` will now literally *be* the
    effective target at render time (since the orchestrator passes a
    `model_copy`'d spec with `target_words` already overridden, per the
    "Orchestrator" decision above). **No prompt text changes** -- the existing
    wording is already accurate for an effective, possibly-adjusted number,
    and item 8's "a short sentence... is allowed" is optional, not required;
    adding one would be an unrequested wording change for no functional gain.
- Commands and results:
  - `venv\Scripts\python.exe -m ruff check app/core/constants.py app/services/script_pipeline.py tests/test_script_pipeline.py` → All checks passed (checked incrementally while writing).
  - `venv\Scripts\python.exe -m pytest tests/test_script_pipeline.py -q` → 47 passed
    (32 pre-existing, including the 1 updated assertion, + 15 new: 7
    effective-target/carry pure-function tests, 3 validate_section-split
    pure-function tests, 1 constants-pin test, 4 e2e scenarios covering
    verification items 3/4/5/7).
  - `venv\Scripts\python.exe -m pytest tests/test_learning_pipeline.py tests/test_ai_job_service.py tests/test_ai_jobs_api.py tests/test_ai_router.py tests/test_ai_logging.py tests/test_ai_contracts.py -q` → 129 passed (no regressions in adjacent AI-layer tests).
  - `venv\Scripts\python.exe -m ruff check app tests scripts` (full) → All checks passed.
  - `venv\Scripts\python.exe -m pytest -q` (full suite) → **865 passed**, 0 failed,
    in 383.82s (850 baseline after Task 14.2-b + 15 net new in `test_script_pipeline.py`).
- Deviations:
  - **Existing 13.4 assertion changed (verification item 8):**
    `test_pipeline_fails_transparently_when_repair_also_fails` previously used
    two word-count-only failures (5 then 6 words against a 100-word target) to
    reach `section_validation_failed`. Under 14.3, a word-deviation-only
    failure surviving repair is now *accepted* (the whole point of this task),
    so that fixture no longer reaches `section_validation_failed` at all.
    Switched the fixture to an unknown-speaker id (a structural error, which
    still unconditionally hard-fails after repair) -- one-line justification
    recorded in the test's own docstring and here.
  - Resume/carry recomputation reads `target_effective` from checkpoints
    rather than literally replaying nominal targets -- see the "Resume/carry"
    decision above (PM-reviewed and agreed before implementation, not a
    post-hoc deviation).
  - **PM observation (2026-09-21, accepted as harmless, no fix required):** the
    resume upfront-recompute loop adds *every* checkpointed section's delta to
    `carry`, including the last section's (`carry += cp_effective - cp_words`
    unconditionally), whereas the live per-section loop skips the last section
    (`if not is_last: carry += ...`). This is a real asymmetry, but inert: no
    code path reads `carry` after the last section is processed on the live
    path either (the final-section budget repair computes its target from
    `target_words - words_before_last_section`, never from `carry`), so the
    extra term the resume path computes is simply never consumed. Left as-is
    rather than special-cased, since "compute a value nothing reads" is lower
    risk than adding an `if not is_last` branch to the resume loop that would
    then diverge from -- and need to stay in sync with -- the live loop's own
    condition for no behavioural benefit.
  - No other deviations -- all edits stayed within
    `app/services/script_pipeline.py`, `app/core/constants.py`,
    `tests/test_script_pipeline.py`. `prompts/script/section.txt` and
    `prompts/script/repair.txt` were read but not edited (see "Prompts"
    decision above). No `tests/fixtures/ai/*` changes were needed.
- Revert-and-confirm-failure evidence:
  - Constants-pin: temporarily changed `SCRIPT_SECTION_WORD_TOLERANCE` from
    `0.15` to `0.25` and re-ran
    `venv\Scripts\python.exe -m pytest tests/test_script_pipeline.py::test_constants_pin_word_tolerances_are_unchanged_by_task_14_3 -q`:
    **1 failed** (`assert 0.25 == 0.15`). Restored `0.15` and re-ran: **1 passed**.
  - Core behavior change: temporarily changed the post-repair check from
    `if structural_errors:` to `if structural_errors or budget_errors:`
    (reverting to the pre-14.3 hard-fail-on-any-remaining-error rule) and
    re-ran
    `venv\Scripts\python.exe -m pytest tests/test_script_pipeline.py::test_pipeline_accepts_off_target_sections_when_total_lands_inside_tolerance -q`:
    **1 failed** (`final_job["status"]` was `"error"`, not `"complete"`),
    confirming the test actually depends on the accept-and-carry behavior, not
    something else. Restored `if structural_errors:` and re-ran the full file:
    **47 passed**.
- Commit(s): (next) -- feat(ai): Task 14.3 running section budget + this task
  card's execution record and PHASE-STATE update.
