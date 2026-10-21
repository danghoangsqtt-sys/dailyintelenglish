# Task 58.2 — Settings left menu

Status: planned 2026-10-22.

## Paths
- frontend/pages/settings.html, frontend/static/js/settings.js
- tests/test_settings_*browser*.py (existing ones follow), tests/test_i18n_browser.py

## File-Level Plan
Left menu (General · AI · AI providers), one section shown at a time, remembered in the URL hash. General: language radio (English / Tiếng Việt, through `I18n.set`), theme radio (light / dark, through `Theme`), build info. AI: the existing mode, order and fallback-rate blocks. AI providers: the existing three provider forms, each in a card whose header shows a status dot (key saved / not set up) from the data the page already loads. All existing ids, forms and API calls stay.

## Tests
Browser: the menu switches sections; the language radio switches the app to Vietnamese; existing Settings tests pass.
