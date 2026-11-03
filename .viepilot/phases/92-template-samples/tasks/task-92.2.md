# Task 92.2 — Cards with clips

See [PLAN.md](../PLAN.md), D137.

## Design (written before code)

- `frontend/static/js/template_samples.js` (new, `TemplateSamples.attach(root, {selector, keyOf, language})`): reads
  `/static/samples/index.json` once; for each card found by `selector` whose kind has a clip, adds a 9:16 (or 16:9)
  thumbnail `<video muted loop playsinline preload="none" poster>` and a "Xem ví dụ" button; plays on `mouseenter`,
  `focusin` and when the card is selected (`aria-checked` / `aria-pressed` true), pauses otherwise; with
  `prefers-reduced-motion: reduce` it never plays (the poster stays). The dialog (`<dialog>`) shows the larger clip,
  "Ví dụ minh hoạ" and the "Phù hợp cho…" line; Esc and the close button close it. Clicks on the thumbnail / button do
  not select the card.
- "Best for" copy per kind (English in the script, Vietnamese in `i18n_vi.js`).
- Language: the channel audience when known (`Api.getChannelSettings` or the Shorts batch audience select): Quốc tế →
  `en`, otherwise `vi`.
- Step 1: the video type cards (`[data-mode]`) and the Short template cards (`[data-template]`); Shorts batch: the kind
  cards (`#template-grid [data-template]`).

## Paths

`frontend/static/js/template_samples.js`, `frontend/pages/step1_config.html`, `frontend/pages/shorts_batch.html`,
`frontend/static/js/step1_config.js`, `frontend/static/js/shorts_batch.js`, `frontend/static/css/style.css`,
`frontend/static/js/i18n_vi.js`, `tests/test_template_samples_browser.py`.

## Verification

`pytest tests/test_template_samples_browser.py tests/test_shorts_browser.py tests/test_batch_news_browser.py -q`.
