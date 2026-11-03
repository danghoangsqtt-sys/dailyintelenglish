# Task 88.3 — UI wiring

## Objective

The `grammar` Short can be made from every place a `roots` Short can: Step 1 template card (1.5 / 2 / 2.5 min), Shorts
batch kind card (a list of grammar points → one Short each, silent preview), Channel plan, Automatic videos, Step 2
(no editor review; cards kept), Step 5 (no visual plan), Vietnamese UI copy.

## Design (written before code)

Follow the Phase 87.5 changes for `roots` one by one (same files): `step1_config.html/js` (card + `ACADEMIC_SHORTS`),
`shorts_batch.js`, `channel.js`, `automation.js`, `step2_script.js`, `step5_shorts.js`, `step5_video.js`, `i18n_vi.js`;
batch `TEMPLATES` entry. The optional quick quiz is part of the lesson (88.1), shown as the last card with a 3-2-1
countdown ring (88.2); no new option is added.

## Paths

`frontend/pages/step1_config.html`,
`frontend/static/js/{step1_config,shorts_batch,channel,automation,step2_script,step5_shorts,step5_video,i18n_vi}.js`,
`tests/test_grammar_browser.py` (new), counts in `tests/test_shorts_browser.py` / `tests/test_batch_news_browser.py`.

## Verification

`pytest tests/test_grammar_browser.py tests/test_shorts_browser.py tests/test_batch_news_browser.py -q`.
