# Task 15.5 — Multi-Script Pace Calibration (Optional)

- **Status:** not started — deferred until 15.1–15.4 land, and only on the owner's
  explicit word
- **Owner:** PM (measurement) → Coder (constants update, if authorized). This card is a
  description only for now — the Coder mirrors it into the phase folder per plan §3 but
  does not implement or run any part of it unless and until the PM confirms the owner
  has asked for it.
- **Priority:** P2
- **Dependency:** Tasks 15.1–15.4 all done.
- **Controlling detail:** plan §3 "15.5 — Multi-script pace calibration (optional)";
  Phase 14 close-out `SUMMARY.md`'s first flagged residual (single-script pace
  calibration)

## Objective

Only if the owner wants the media gate to actually pass (not just report cleanly as
declared): Task 14.10's `CEFR_WORDS_PER_MINUTE` table was measured from one script
(the Gate B-3 winner). Gate B-5's media-duration miss (-4.3%) is consistent with normal
script-to-script pace variance around that single sample, not a new defect. This task
would measure real pace across the five Gate B-5 (or Gate B-6) scripts per level
instead of one, to see whether a mean-based target closes that gap.

## Scope (per plan §3, if authorized)

- PM measures real Edge TTS pace (mean and spread) on the five completed B1
  eight-minute scripts from a real Gate B run (B-5 or B-6), the same measurement method
  Task 14.10's D13 already used for one script.
- If the mean differs meaningfully from the current 125 wpm B1 figure, the Coder updates
  `CEFR_WORDS_PER_MINUTE`/`CEFR_DEFAULT_TTS_SPEED` the same way Task 14.10 did (measured
  value, pin test, revert-and-confirm-failure, the 6 `cefr_*.txt` Pace lines kept in
  sync).
- The media gate is then declared against whichever script's completion lands closest
  to the new target, not silently redefined after the fact.

## Explicitly forbidden (if this task proceeds)

- Widening any tolerance (`SCRIPT_GLOBAL_WORD_TOLERANCE`, `SCRIPT_SECTION_WORD_TOLERANCE`,
  the media duration/A-V thresholds) instead of re-measuring the actual constant — this
  task is about correcting the *target*, exactly as Task 14.10 was, never relaxing the
  *gate*.

## Status

Not started. Requires an explicit owner request (relayed by the PM) before either
session begins any work on it — this card exists only so the option is doc-first
recorded, not because it is authorized yet.

## Execution record

- PM:
