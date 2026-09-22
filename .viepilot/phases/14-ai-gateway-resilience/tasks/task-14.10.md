# Task 14.10 — Pace Calibration (Measured, Not Assumed)

- **Status:** in progress
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
  1. **D14 investigation (done first, per the card's own requirement item 4 — before
     any renderer change):**
     - **Raw finding on the actual Gate B-3 evidence:** the winning project's real
       media (`data/quality_reviews/phase14/gate-b2/7bc713ac-a4b9-4e4b-8d56-1081086f18b1-{audio.mp3,video.mp4}`
       -- Gate B-3's runner writes into a fixed `gate-b2`-named evidence subpath, a
       pre-existing runner quirk, not something this task's allowed files can fix)
       via `ffprobe -show_entries stream=codec_type,duration`: the audio stream is
       **301.52 s** (both the standalone MP3 and the video's embedded AAC track agree
       exactly); the video stream is **304.00 s**. Diff **2.48 s**, matching the PM's
       reported number exactly.
     - **ffmpeg command structure** (`_render_video_sync`,
       `app/services/video_service.py`): `-loop 1 -i background.png -i audio.mp3
       -vf subtitles=... -c:v libx264 -tune stillimage -c:a aac -b:a 192k -pix_fmt
       yuv420p -shortest output.mp4`. No explicit output frame rate, no `-t`, no
       end-frame/fade filter anywhere in this function or its docstring -- nothing in
       the code represents a deliberate decorative tail.
     - **Reproduced directly** (scratch repro, not committed): the exact same command
       structure against a 10 s synthetic sine-tone MP3 + the real `midnight.png`
       background produced **zero** overshoot (video == audio == 10.000000 s exactly,
       with or without the `subtitles` filter). The same command against a **301.52 s**
       synthetic audio (matching the real duration) reproduced the overshoot directly:
       video **304.16 s** vs. audio **301.52 s** (diff 2.64 s -- same phenomenon, same
       order of magnitude, confirmed scale-dependent: negligible at 10 s, ~2.5 s at
       ~300 s). This matches `-shortest`'s known ffmpeg behavior with a B-frame-using
       encoder (`libx264`'s default `-tune stillimage` settings use B-frames, confirmed
       in the encode log's "consecutive B-frames" stats) -- `-shortest` stops *reading*
       once the shorter input (audio) ends, but frames already buffered in the
       encoder's reordering pipeline still get flushed afterward, padding the tail by
       roughly the buffer depth. This is an **encoder-implementation artifact of
       `-shortest`, not a deliberate design element**.
     - **Fix verified directly**: replacing `-shortest` with an explicit
       `-t 301.52` (the real, already-known audio duration) on the same 301.52 s
       repro produced video == audio == **301.520000 s exactly** -- frame-accurate,
       no overshoot.
     - **Decision (D14, unintentional branch): fix it.** `app/services/video_service.py`
       gains one line: `_render_video_sync` takes the audio's real duration (already
       computed and stored precisely by `AudioService` as
       `audio_jobs.duration_seconds` -- `round(len(mixed_audio_ms)/1000, 3)`, already
       passed through as `audio_job["duration_seconds"]` at the existing call site) and
       passes `-t {duration}` instead of `-shortest`. `AV_DIFF_MAX_SECONDS = 1.0` in
       `scripts/run_ai_operational_trial.py` is **unchanged** -- no re-declaration
       needed, since the fix closes the gap to effectively zero rather than shrinking
       it toward the existing 1.0 s threshold.
  2. **Pace calibration constants:** `CEFR_DEFAULT_TTS_SPEED`/revised
     `CEFR_WORDS_PER_MINUTE` exactly per D13's table (card body above); the 6
     `prompts/script/cefr_*.txt` "Pace" lines updated to match.
  3. **Speaker default-speed design** (the card's own open question, resolved before
     code): `frontend/static/js/step1_config.js` currently hardcodes `speed: 1.0` the
     moment a speaker row is created (line ~185) and falls back to `?? 1.0` when
     building the submit payload (lines ~313/~426) -- the server-side model
     (`SpeakerConfig.speed`, currently `float = Field(default=1.0, ...)`) can never
     distinguish "the user picked 1.0" from "nothing was ever set" through this wire
     shape, and there is in fact **no UI control anywhere that lets the user set speed
     at all** (confirmed: `speed` appears nowhere in any frontend file outside those 3
     lines in `step1_config.js` -- it is a fixed, invisible internal value today, not
     an editable one). Design: `SpeakerConfig.speed` becomes `float | None = Field(
     default=None, ...)` (the bounds stay `ge=TTS_SPEED_MIN, le=TTS_SPEED_MAX`, which
     Pydantic only enforces when a value is actually given); `project_service.py`
     resolves `None -> CEFR_DEFAULT_TTS_SPEED[cefr_level]` once, in a small helper,
     called from both `create_project` (using `config.cefr_level`) and `update_project`
     (using the *merged* `cefr_level`, i.e. the patched value if present else the
     current one) -- applied to the speaker list before it is used for both the
     `config_json` snapshot and `_replace_speakers`, so the DB row and the snapshot
     never disagree and the `speakers.speed` column (`NOT NULL`) never receives `None`.
     `frontend/static/js/step1_config.js` stops hardcoding `1.0`: a newly-created
     speaker gets no `speed` key at all (server resolves it), so the level-appropriate
     default always applies at submission time regardless of which CEFR level was
     selected when the row was added vs. when the form is submitted. `SpeakerUpdate`
     (Step 4's *separate*, pre-existing `speed: float | None = None` partial-update
     model, used for "leave field alone" semantics on an already-created speaker) is
     untouched -- a different model, a different meaning of `None`, not in this
     task's scope.
  4. **Test/fixture updates:**
     - Golden-fixture parametrize (`test_compute_target_words_matches_golden_fixtures`):
       450/800/1300 -> 555/1000/1450 (A2 5min @111wpm, B1 8min @125wpm, C1 10min
       @145wpm) -- these assert the *real* function output for real level/duration
       combinations, so they must track the new table exactly.
     - `test_plan_sections_splits_into_roughly_90_second_chunks`: target 800->1000
       (matches the new real B1 8-min figure), comment updated to 125wpm*1.5=187.5->188
       words/section, and strengthened to assert the exact `[200, 200, 200, 200, 200]`
       split per this task's own required-behaviour math, not just `len == 5`.
     - `test_plan_sections_sums_to_target_words`: not strictly required (the function's
       `sum(budgets) == target` invariant holds for any level/target pair by
       construction -- section *count* depends on wpm, but the *sum* never does), but
       updated anyway for consistency (450/800/1300 -> 555/1000/1450) so no stale
       pre-14.10 magic numbers are left sitting next to the corrected table elsewhere
       in the same file.
     - The 7 end-to-end tests using `duration_minutes=8.0` purely as a vehicle to reach
       `target_words = 800` (none of them assert on `duration_minutes` itself, only on
       the *word* totals/effective-target arithmetic that follows from it) change to
       `duration_minutes=6.4` (125 wpm * 6.4 min = 800.0 exactly) -- this is the
       one-line-justification fixture update the card asks for: it preserves every
       existing hand-verified carry/clamp/repair number in those tests completely
       unchanged (they were never actually about "8 minutes", only about the round
       number 800), rather than re-deriving 6-8 large e2e fixtures' worth of
       carry/clamp arithmetic against a new 1000-word total for no behavioural reason.
       Each occurrence's existing comment is updated to explain the new value.
     - `compute_last_section_effective_target`'s own direct unit tests (lines ~136-146)
       use `800`/`150`/etc. as arbitrary literal inputs to a pure function that takes
       no CEFR level at all -- not tied to the real B1 constant in any way -- left
       untouched.
  5. **New tests:** a constants-pin test for both new tables (revert-and-confirm-failure
     planned the same way as Task 14.8's consecutive-lines pin); a
     `project_service`-level test proving a speaker with no `speed` gets the CEFR-level
     default at creation, and a second proving an existing project's already-stored
     `speed` survives an unrelated update untouched.
- Commands and results:
- Deviations:
- Revert-and-confirm-failure evidence:
- Commit(s):
