# Task 14.10 — Pace Calibration (Measured, Not Assumed)

- **Status:** pending
- **Owner:** Coder (measurement itself was done by PM — see below)
- **Priority:** P1
- **Dependency:** Task 14.6 done (Phase 13 Task 13.10 complete under D11); Gate B-3
  report (`docs/operations/phase14-gate-b3.md`)
- **Controlling detail:** plan §13 "14.10 — Pace calibration"; Amendment G decision D13;
  `docs/brainstorm/session-2026-09-21.md` §Addendum 2

## Objective

Replace the never-achieved `CEFR_WORDS_PER_MINUTE["B1"] = 100` (and the other four
levels' equally unmeasured figures) with values the PM actually measured against real
Edge TTS output, and give every CEFR level a matching default speaker `speed` so the
planned pace and the spoken pace are the same number.

## Measured problem (do not re-derive — PM already measured this for real)

PM ran real Edge TTS synthesis of the Gate B-3 winning script (730 words / 43 lines,
including 20.6 s of silence) at five speaker speeds and measured the resulting audio
duration for real (`data/quality_reviews/phase14/gate-b3/pace-calibration.json`):

| Speaker `speed` | Total seconds | Words per minute (incl. silences) |
|---:|---:|---:|
| 0.75 (floor `TTS_SPEED_MIN`) | 394.3 | **111** |
| 0.85 | 350.7 | **125** |
| 0.90 | 332.5 | **132** |
| 1.00 (default) | 301.5 | **145** — reproduces the Gate B-3 media run exactly |
| 1.10 | 276.2 | **159** |

Even at the slowest supported speed (0.75, `TTS_SPEED_MIN`), the real pace is 111
wpm — never 100. No amount of slowing alone reaches the currently-planned B1 target;
the *word target* has to follow the *measured* pace, not the other way around.

## Allowed files

`app/core/constants.py`, `prompts/script/cefr_a1.txt` … `cefr_c2.txt` (the "Pace" line
only), `app/models/project.py` (default speed derived from level),
`app/services/project_service.py` (apply the level default at speaker creation when no
speed is given), `frontend/static/js/step1_config.js` and
`frontend/pages/step1_config.html` (only if the speed control's default must follow the
level), `app/services/video_service.py` (D14 investigation/fix only),
`scripts/run_ai_operational_trial.py` (only `AV_DIFF_MAX_SECONDS`, only if D14
re-declares it), `tests/test_script_pipeline.py`, `tests/test_project_service.py`,
`tests/test_video_service.py`, `tests/fixtures/ai/*`.

Anything else → stop and ask the PM to amend the plan.

## Required behaviour

1. **New constants** in `app/core/constants.py`: `CEFR_DEFAULT_TTS_SPEED` and a revised
   `CEFR_WORDS_PER_MINUTE`, both from D13's measured table:

   | Level | `CEFR_DEFAULT_TTS_SPEED` | `CEFR_WORDS_PER_MINUTE` | 8-min target words |
   |---|---:|---:|---:|
   | A1 | 0.75 | 111 | 888 |
   | A2 | 0.75 | 111 | 888 |
   | B1 | 0.85 | 125 | 1,000 |
   | B2 | 0.90 | 132 | 1,056 |
   | C1 | 1.00 | 145 | 1,160 |
   | C2 | 1.10 | 159 | 1,272 |

   `SCRIPT_GLOBAL_WORD_TOLERANCE`, `SCRIPT_SECTION_WORD_TOLERANCE`, the Task 14.3 carry
   caps, and Task 14.8's `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS` are **unchanged** — this
   task changes the *target* the whole apparatus aims at, not any tolerance/repair rule.
2. **Prompt/constant single source of truth**: update the "Pace: target about N words per
   minute" line in each of the 6 `prompts/script/cefr_*.txt` files to the matching new
   `CEFR_WORDS_PER_MINUTE` value (`app/core/constants.py`'s own comment already states
   these prompts are that constant's copied source — keep that true).
3. **Speaker default speed**: a speaker created with no explicit `speed` gets
   `CEFR_DEFAULT_TTS_SPEED[project.cefr_level]` instead of the current hardcoded `1.0`
   default. An **existing** project's already-stored speaker `speed` values are never
   touched — this is a default for new speakers only, not a migration.
4. **D14 investigation (do before any renderer change):** inspect
   `app/services/video_service.py`'s actual render pipeline for the ~2.5 s audio/video
   tail mismatch Gate B-2/B-3 measured. Write the finding in this card's execution record
   before making any change:
   - If it's unintentional (encoder priming, `-shortest` rounding, trailing silence in
     the audio mix, etc.) — fix it, and the existing `AV_DIFF_MAX_SECONDS = 1.0` in
     `scripts/run_ai_operational_trial.py` stays as-is.
   - If it's a deliberate design element (e.g. a static end frame/fade already relied on
     elsewhere) — do not remove it; instead re-declare `AV_DIFF_MAX_SECONDS = 3.0` in
     the runner, with the reason written here.
   - No silent change either way — the decision and its evidence are recorded before the
     diff, not justified after the fact.
5. **Fixtures**: any existing fixture/test that assumed the old 800-word B1-8-minute
   figure is updated to the new 1,000-word figure, each with a one-line comment saying
   why (mirrors the existing convention already used for other constant-driven fixtures
   in this suite).

## Explicitly forbidden

- Editing `SCRIPT_GLOBAL_WORD_TOLERANCE`, `SCRIPT_SECTION_WORD_TOLERANCE`,
  `SCRIPT_SECTION_CARRY_CAP`, `SCRIPT_LAST_SECTION_CARRY_CAP`,
  `SCRIPT_PIPELINE_MAX_LENGTH_REPAIRS`, or `SCRIPT_PIPELINE_MAX_GLOBAL_BUDGET_REPAIRS`.
- Retroactively changing a stored speaker's `speed` on an existing project.
- Changing `AV_DIFF_MAX_SECONDS` without the D14 investigation finding recorded first.
- Widening `TTS_SPEED_MIN`/`TTS_SPEED_MAX` — the new per-level defaults must fit inside
  the existing `[0.75, 1.5]` band (they do: 0.75–1.10).

## Verification (all must be in the diff)

1. `compute_target_words("B1", 8) == 1000` (and the matching figure for every other
   level from the table above) — a direct pin test.
2. A pin test asserting `CEFR_DEFAULT_TTS_SPEED` and `CEFR_WORDS_PER_MINUTE` equal the
   D13 measured table exactly (revert-and-confirm-failure: temporarily edit one value,
   confirm the pin test fails for the right reason, restore, confirm green).
3. A new speaker created with no `speed` gets the CEFR-level default; an existing
   project's stored speaker `speed` is provably unchanged by this task (a test asserting
   a pre-existing stored value survives).
4. FakeProvider e2e script-pipeline tests still green at the new targets.
5. D14 outcome recorded in this card before any `video_service.py` change, with the
   decision (fix vs. re-declare) and its evidence.
6. Full suite green; `ruff check app tests scripts` clean; `node --check` on any touched
   `.js` file.

## Rollback

Revert the two constants and the 6 prompt "Pace" lines to their pre-14.10 values; no
migration involved (new-speaker-only default, no stored-data change).

## Execution record

- Plan/decisions before code:
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
