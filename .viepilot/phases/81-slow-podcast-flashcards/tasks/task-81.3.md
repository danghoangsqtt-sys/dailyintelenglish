# Task 81.3 — UI

## Objective
The owner can choose both formats in the Shorts batch, Step 1 and the Channel plan, edit slow-podcast translations in Step 2, and Step 5 explains there is no visual plan.

## Paths
frontend/static/js/shorts_batch.js, frontend/static/js/step1_config.js, frontend/static/js/channel.js, frontend/static/js/step2_script.js, frontend/static/js/step5_video.js, frontend/static/js/i18n_vi.js, tests/test_batch_news_browser.py

## File-Level Plan
- shorts_batch.js: two kind cards (Text templates group), preview via sample props.
- step1_config.js / channel.js: style options for both.
- step2_script.js: a "Vietnamese" field under each line for `slowpod` (saved in language_notes.translation_vi).
- step5_video.js: line-drawn note for slowpod / flashcards like chat / wyr.
- i18n_vi.js: copy.

## Verification
Browser tests for the batch cards; `node --check`.
