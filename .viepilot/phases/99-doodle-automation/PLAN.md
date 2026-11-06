# Phase 99 — Doodle story in the Channel plan, the batch and automatic videos (plan, written before code)

Owner (2026-11-06, `/vp-auto`): "hoàn thành luôn Phase 98 99 và cài bản mới nhất đã hoàn thiện sau khi xong Phase 98 99".
Phase 98's plan names this phase: "Automation, Channel and Shorts batch (Phase 99)". No owner decision was asked for; the defaults
below follow Phase 98 (D161-D167) and the way earlier kinds joined the channel (Phase 63, 80, 88.3).

## What is missing today (read from the code at `b94e1e7f` + the Phase 98 workspace)

1. A Channel-plan series has no story type: `SeriesInput` and `channel_series` have no `explainer_subject`, so
   `channel_service.create_projects` builds a Doodle `ScriptConfig` without one and the project schema refuses it.
2. The Channel-plan series form and the batch page do not offer "Doodle story".
3. The night runner sends every plan with the generic review flag to the AI fact check. For an original short story
   `fact_check.check` refuses with "Original fiction ... does not require a fact check", so the step fails twice and the episode stops.
4. Drawing a Doodle story's pictures takes about 30 s a picture (8 minutes ≈ 62 pictures ≈ 31 minutes). The runner waits at most
   `JOB_TIMEOUT_SECONDS` = 1800 s for a picture job, then stops the episode.

## Decisions (defaults)

- **D168, a series keeps its story type.** Migration `042_series_subject.sql` adds `channel_series.explainer_subject` (plain text,
  NULL for other kinds). `SeriesInput` / `SeriesPatch` take `explainer_subject`, valid only with `explainer_style = "doodle"` and one of
  `history`, `myth`, `field`, `story`; a Doodle series without one is `story`. A Doodle series lasts 3-12 minutes, 8 by default, like
  Step 1. `create_projects` passes the story type, the length and an episode's pasted material (`source_kind = "article"`).
- **D169, the batch makes a Doodle series.** A new batch template `doodle` ("Doodle story", 16:9, not a Short): 5-10 story ideas of one
  story type on one topic, saved as a dated series with the chosen length, or made into projects at once. The batch request takes
  `explainer_subject` and `duration_minutes` for this template only.
- **D170, truth by kind in automatic videos (D165).** History and specialised subjects go through the AI fact check and stop for the
  owner on any doubt, as VOX does. A myth is checked too (it must be named as a myth with its culture). An original short story skips
  the fact check: its generic review flag is accepted as a person would on Step 5. Every automatic video still ends at
  "waiting for review": the owner watches it before publishing.
- **D171, time for the pictures.** A picture job of a Doodle story may run 90 minutes (`DOODLE_PICTURE_TIMEOUT_SECONDS`); other kinds
  keep 30 minutes. A Doodle story whose pictures cannot be drawn (no GPU model, Lite) stops for the owner instead of rendering without
  pictures.

## Amendment (2026-11-06, found by the first real automatic run, before code)

The first automatic 3-minute short story (cloud AI) stopped twice at the script with `doodle_vocabulary_incomplete` ("Use each target
term at least three times: belongings, notice, get off, honesty", then "faded, lost and found"). The production database has the same
error twice. Cause: after the sections are written, one repair rewrites **one** section, so four words short of three uses across a
two-section story cannot be fixed; a person retried by hand in Phase 98, the night run cannot.

- **D172, the target words are repaired across the story.** The Doodle word repair walks every section once, in story order, asking for the
  words still short; a rewrite is kept when it lowers the total shortfall (uses missing to reach three) and the script still validates.
  A word that is still short after that is dropped from the story's target words, never forced in (Phase 98's own rule: "a word that cannot
  be used naturally is replaced ... not pushed into it"), as long as at least five words remain (D164's 5-8); with fewer the job still
  fails. Dropped words are recorded with the story's words on its first line.

## Tasks

- 99.1 **Series and projects:** migration 042, `schemas/channel.py`, `channel_service.create_series/patch/create_projects`, tests in
  `backend/tests/test_channel_api.py` style (a Doodle series makes a valid Doodle project with its subject and length; other kinds
  unchanged).
- 99.2 **Batch:** `batch_service.TEMPLATES["doodle"]`, request fields, the idea prompt, `create_batch` for a 16:9 Doodle series; tests.
- 99.3 **Night runner:** story skips the fact check, picture timeout, no-picture stop; tests with the existing fake client.
- 99.3b **Word repair (D172):** `script_pipeline._vocabulary_repair` takes a chosen section and keeps a rewrite that lowers the total
  shortfall; the Doodle branch walks every section and drops words still short when five or more remain; tests in
  `backend/tests/test_doodle_story.py` style.
- 99.4 **UI:** the Channel-plan series form and the batch page offer Doodle story with the four story types and 3-12 minutes;
  Vietnamese copy in `i18n_vi.js`; a browser test.
- 99.5 **Verification:** full pytest, Vitest, renderer type check; one real automatic run of a 3-minute Doodle story from a Channel-plan
  series through to "waiting for review" in an isolated data copy, with the MP4 checked by ffprobe and a black-frame scan.

## Risks

- A real automatic Doodle run needs the cloud AI, Edge TTS and about 12 minutes of Qwen drawing for 3 minutes of story.
- The picture timeout is a guess from Phase 98's measured ~30 s a picture; the real run records the actual time.
