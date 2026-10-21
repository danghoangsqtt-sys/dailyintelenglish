# Task 59.4 — Step 1, Step 5 and thumbnail for VOX

Status: planned 2026-10-22.

## Paths
- frontend/pages/step1_config.html, frontend/static/js/step1_config.js (third card; narrator text)
- frontend/static/js/explainer_editor.js, frontend/pages/step5_video.html (VOX editor)
- backend/media/thumbnail_compose.py / thumbnail_service.py (no presenter picture for VOX)
- frontend/static/js/i18n_vi.js (new texts)
- tests/test_vox_explainer_browser.py (new)

## File-Level Plan
Step 1: a third type card "🎬 VOX explainer — voice-over with motion graphics" setting `presentation_mode = solo_explainer`, `explainer_style = vox`; the four subject cards and structures apply; the speaker card says "Narrator (voice only)". Step 5: for VOX the explainer editor hides presenter placement, gestures and "Arrange layouts", and offers the visual kinds text card, quote, chart, timeline, map, diagram, photo, activity with simple line-based fields (chart `label | value`, timeline `when | label`, map `name | lat | lon | country`). Thumbnails: VOX uses the composed template without a presenter figure (topic picture + headline). Vietnamese texts added to the dictionary.

## Tests
Browser: the VOX card creates a VOX project; the Step 5 editor shows the VOX kinds and no presenter fields.
