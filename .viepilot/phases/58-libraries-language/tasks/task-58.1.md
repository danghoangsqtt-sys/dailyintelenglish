# Task 58.1 — Language layer

Status: planned 2026-10-22.

## Paths
- frontend/static/js/i18n.js (new), frontend/static/js/i18n_vi.js (new)
- frontend/pages/*.html (two script tags after `theme.js`; top-bar switch)
- tests/test_i18n_browser.py (new)

## File-Level Plan
`I18n.lang()` / `I18n.set(lang)` (localStorage `dbe.lang`, default `en`, reload-free: re-translates the page, or reloads to restore English). In VI mode: walk text nodes and `placeholder`, `title`, `aria-label` attributes outside `[translate="no"]`, `script`, `style`, `textarea`, `input` values; replace trimmed exact matches from `I18N_VI.text`, then the first matching `I18N_VI.patterns` regex; keep leading/trailing whitespace; remember the English original on the node so switching back restores it. A MutationObserver (childList, characterData, attributes subset) re-runs on changes, batched with `requestAnimationFrame`. `document.title` and `<html lang>` follow. The top bar gets a small "EN | VI" switch next to the theme toggle.

## Tests
Browser: default English untouched; switching to VI translates the sidebar and a dynamic list rendered after load; `translate="no"` content stays English; switching back restores English; the choice survives a reload.
