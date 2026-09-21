# Task 14.3 — Running Section Budget; Hard Gate Only at the Global ±10%

- **Status:** pending
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
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
