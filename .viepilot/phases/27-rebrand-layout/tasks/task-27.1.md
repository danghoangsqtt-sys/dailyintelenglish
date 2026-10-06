# Task 27.1: Brand pack (Daily Beyond English: logo, name, green/yellow palette)

## Objective

Every page shows the owner's logo and the name **Daily Beyond English** in the owner's palette (green,
lime, yellow, white, a red accent). Behaviour, ids, roles and flows do not change.

## Owner decisions behind it (brainstorm 2026-10-06: D57, D60, D62)

- Name: Daily Beyond English; logo `data/Daily Beyond English Avatar Logo.png` (1254 x 1254 RGBA, 1.4 MB).
- Palette: green `#3a9d3f` -> lime `#9bd13c`, yellow `#ffd60a`, white, red `#e5322d` (calls to action),
  navy `#151a5c` (titles on light). Replaces the violet -> cyan palette.
- The name applies to the app and logo, the video intro/outro and Jenny's greeting (27.5), and the YouTube
  package prompts (this task).

## Facts found in the code

- The header of the 11 pages repeats the same markup: `<a class="brand"><span class="brand-mark">DI</span>
  <span class="brand-word"><b>Daily Intel</b><small>English Studio</small></span></a>`; `<title>` ends with
  "Daily Intel English Studio"; `step1_config.js` sets four titles itself.
- The palette lives in `style.css` tokens (`--accent`, `--brand-violet`, `--brand-cyan`, `--brand-gradient`,
  `--brand-gradient-soft`, `--focus-ring`, `--accent-soft`, dark-mode variants) with a few hard-coded
  violet values in `step2_script.js` and `waveform.js`.
- `app/core/config.py` names the packaged data folder `DailyIntelEnglishStudio`: it is **not renamed**
  (that would orphan the owner's data). `tests/test_run_ai_operational_trial_outro.py` quotes an old script
  line and is unrelated.
- No test pins the page titles or the "DI" mark (grep).

## Paths

- `frontend/static/brand/logo.png` (new, 512 px), `frontend/static/brand/logo-64.png` (new, header and
  favicon), `frontend/static/brand/logo-full.png` (new, the original for the video and the package)
- `frontend/static/css/style.css`
- `frontend/pages/dashboard.html`
- `frontend/pages/characters.html`
- `frontend/pages/music_library.html`
- `frontend/pages/settings.html`
- `frontend/pages/step1_config.html`
- `frontend/pages/step2_script.html`
- `frontend/pages/step3_learning.html`
- `frontend/pages/step4_tts.html`
- `frontend/pages/step5_video.html`
- `frontend/pages/step6_thumbnail.html`
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step1_config.js`
- `frontend/static/js/step2_script.js`
- `frontend/static/js/waveform.js`
- `app/main.py`
- `app/services/youtube_ai.py` (the package prompts, if the product name appears; checked first)
- `tests/test_brand_assets.py` (new)

## File-Level Plan

1. **Assets:** resize the logo with PIL (LANCZOS) to 512 and 64 px, keep the original as `logo-full.png`;
   serve them from `/static/brand/` (the static mount already exists). The logo is the owner's own file.
2. **`style.css`:** new tokens `--brand-green #3a9d3f`, `--brand-lime #9bd13c`, `--brand-yellow #ffd60a`,
   `--brand-red #e5322d`, `--brand-navy #151a5c`; `--brand-gradient` green -> lime; `--accent` a readable
   green (AA on white: `#1f7a2e` for text/buttons, `#e8f6e6` soft), `--accent-ink` white on green; the focus
   ring green; the primary button green, the call-to-action red; dark-mode variants kept in step. The
   `.brand-mark` square becomes the logo image (a 36 px circle, no gradient box).
3. **The 11 pages:** replace the header brand block with one markup (logo `<img alt="">` + wordmark
   "Daily Beyond" / "ENGLISH" in Montserrat); every `<title>` ends "Daily Beyond English"; aria-labels say
   "Daily Beyond English dashboard"; add `<link rel="icon" href="/static/brand/logo-64.png">`.
4. **`step1_config.js`:** the four `document.title` strings. **`step2_script.js`, `waveform.js`:** the
   hard-coded violet becomes the token (read from CSS) or the new green.
5. **`app/main.py`:** the FastAPI title and docstring.
6. **YouTube package prompts:** if `youtube_ai.py` mentions the channel/product name, change it to
   Daily Beyond English and add the tagline "Learn English by real topics" to the channel line.
7. **Tests:** `tests/test_brand_assets.py`: the three logo files exist with the expected sizes; every page in
   `frontend/pages` has the new title suffix, the new header block and the favicon link, and none still says
   "Daily Intel" or the "DI" mark; the CSS defines the new tokens and no violet token remains
   (`--brand-violet`, `--brand-cyan`); the `AA` contrast of accent on white and of white on accent is at least
   4.5 (computed in the test).

## Verification

- `pytest tests/test_brand_assets.py` green; then the browser tests that cover the header and pages, then
  the full suite (about 16 minutes) green.
- Screenshots (light and dark, desktop and narrow) of the dashboard, a step page, characters and music,
  looked at by Claude and sent to the owner.
- Console without errors; the logo loads (network 200).

## Out of scope

The sidebar (27.2), the grid libraries (27.3), the studio frame (27.4), the video intro/outro (27.5).

## Implementation notes (2026-10-06)

- Done as planned: logo assets (`logo-full.png` = the owner's file, `logo.png` 512, `logo-64.png`), the green/yellow
  tokens with `--btn-gradient` (dark green, white text 5.4:1) and `--cta` (red `#c92a25` light, `#e5322d` dark),
  the new header on 11 pages, titles, favicon, the dashboard project-card mark, step 1 titles, the two hard-coded
  violets, `app/main.py`.
- Palette contrast is tested: accent on white 5.41, white on the red CTA 5.47, lime on the dark page 9.9.
- **Found while verifying in the browser:** the server sent no cache headers, so after an upgrade the new HTML
  showed with the old CSS and scripts. Fixed with `RevalidateUi` (a pure ASGI middleware: pages and `/static`
  get `Cache-Control: no-cache`; the ETag still gives a cheap 304). Test: `tests/test_static_cache.py`.
- **Found:** the character form hint still said "different-colour bottom"; changed to allow one colour.
- Not done here (by plan): `youtube_service.py` has no product-name text, so there was nothing to rename; the
  video intro/outro and the greeting are Task 27.5.
- Screenshots: `docs/operations/ui-audit/after-27-1/` (44 images + `overview-light.png`, `overview-dark.png`).
