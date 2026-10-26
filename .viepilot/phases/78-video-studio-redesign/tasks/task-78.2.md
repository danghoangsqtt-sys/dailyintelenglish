# Task 78.2 — Storyboard review redesign

## Objective
The owner judges each beat from a picture and the lines, edits it in an aligned form and approves; nothing floats over the content.

## Paths
- `frontend/static/js/beat_preview.js` (new): `BeatPreview.frame(preview, {aspect, hook, caption})` → a DOM frame (16:9 or 9:16) composed from the 78.1 data with the renderer geometry (horizontal: sprite box height 1.2H, centres 27% / 73%; vertical: picture 0–830 of 1920 with fade, sprites 960 px tall at head 1045, centres 355 / 725, caption band 790–1040).
- `frontend/static/js/storyboard.js`: card layout, debounced preview fetch (`Api.previewStoryboard`), aspect switch stored per viewer (localStorage, try/catch).
- `frontend/static/js/api.js`: `previewStoryboard(projectId, beats)`.
- `frontend/pages/step5_video.html`: storyboard markup/CSS (toolbar, aspect switch, beat grid), Step 5 rule that keeps `#step-guide` in the flow.
- `frontend/static/js/i18n_vi.js`: Vietnamese copy for every new and previously untranslated storyboard text.
- `tests/test_storyboard_browser.py`: assert previews render and the form keeps working.

## File-Level Plan
- Beat card = header (number, lines, place/insert, status chips) + body grid `[preview | form]`, single column under 900 px.
- Preview column: the frame, a one-line note (scene without picture, missing sprites, illustration missing / pending), lines listed (speaker: text) in a scrollable box — no `<details>`.
- Form: each field is `<label class="sb-field"><span>Label</span><control></label>` in a 2-column grid: Kind, Place (search + select together), New place / Shows, Action, Expression; "On screen" chips row; actions row (Split at + select, Merge with next).
- Keep ids/names/texts the tests rely on (`#beat-N-kind|place|scene-search|new-place|action|expression|speaker-I|split-at`, button "Merge with next", h4 text "Beat N · lines a–b · place", summary texts).
- Edits mark dirty and schedule a preview refresh (400 ms); a failed preview shows a note, never blocks editing.
- `#step-guide` on Step 5: `position: static` at the end of the stage.

## Best practices
No innerHTML with data (build nodes); labels wrap controls; keyboard reachable; works at 390 px; no layout shift when previews load (fixed aspect boxes).

## Verification
`pytest tests/test_storyboard_browser.py tests/test_video_studio_browser.py tests/test_video_shell_browser.py -q`; `node --check` on changed JS; browser check in the sandbox at 1440 px and 390 px.
