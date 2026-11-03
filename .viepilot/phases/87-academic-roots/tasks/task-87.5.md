# Task 87.5 — UI wiring

See [PLAN.md](../PLAN.md) task 87.5.

**Order, honestly:** this card was written after the code. The plan's 87.5 paragraph (committed in cbc3dbb) was the
guide; the details below record what was done.

## Done

- Step 1: a "🌱 Word roots, prefixes & suffixes" Short template card; its lengths are 1.5 / 2 / 2.5 min, default 2 (D126).
- Shorts batch: a "Word roots, prefixes & suffixes" kind card (one Short per idea, 2 minutes each); the silent preview
  plays the roots sample (`sampleShort.ts`, bundled into `solo-preview/player.js` at build time).
- Channel plan: the series mode list has "Short: word roots, prefixes & suffixes"; Automatic videos label it.
- Step 2: no editor review for roots (the beats are built by the server, like flashcards); the cards survive a save.
- Step 4: a VieNeu speaker gets a Vietnamese voice picker (25 presets with gender, region and style, from
  `/api/tts/engines`), the engine status and the setup hint when VieNeu is not installed; Edge speakers are unchanged.
- Step 5: roots is a vertical, line-drawn Short.
- Vietnamese UI copy for all new texts (`i18n_vi.js`, including patterns for the dynamic ones).

## Verification

`tests/test_roots_browser.py` (Step 1 card, Step 2 save keeps the cards, Step 4 VieNeu picker saves "Thiện Minh"),
`tests/test_roots_script.py::test_the_shorts_batch_makes_roots_shorts_of_two_minutes`, `tests/test_tts_api.py`;
the Shorts / batch browser tests now count the new template (12 Step 1 Shorts, 15 batch kinds).
