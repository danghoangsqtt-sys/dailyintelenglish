# Phase 92 summary — example clips for every kind of video

Done 2026-11-03 on `owner-runs/20261001-r9` (not pushed, not installed). Defaults D134–D137.

## What changed

- **Clip maker** (92.1): `npm run render:samples` (`renderer/scripts/render-samples.mjs`, settings in
  `renderer/samples.json`) renders a 5 s muted 540×960 MP4 and a poster for the 13 sample templates from the app's own
  renderer (`sampleShort.ts`), Vietnamese and English (one file kept when both are the same), and cuts 5 s 640×360 clips
  for the conversation, presenter and VOX videos from the owner's own finished videos. Output
  `frontend/static/samples/` + `index.json`; 16 kinds, **1.82 MB** in all (budget 8 MB). The word-of-the-day and top-5
  samples now carry a real Vietnamese meaning (`SampleIdea.vi`) instead of the "nghĩa tiếng Việt" placeholder.
- **Cards with clips** (92.2): `frontend/static/js/template_samples.js` adds the clip to every video-type and Short
  template card in Step 1 and every kind card on the Shorts batch page; it plays on hover, focus or when the card is
  chosen, never with reduced motion (the poster stays); the corner "⤢" opens a larger example with "Ví dụ minh hoạ" and
  "Phù hợp cho: …"; clicking the card itself still chooses the kind. The language follows the channel audience (Quốc
  tế → English).
- **Packaging** (92.3): the clips ship with `frontend/` (already in the PyInstaller spec; a test checks the files, the
  spec and the size budget). Run `npm run render:samples` again when a template's look changes or to use other 16:9
  source videos (edit `sources` in `renderer/samples.json`).

## Checks

- Contact sheets of all posters looked at; Shorts batch page and Step 1 checked in the sandbox (clip plays on hover,
  the dialog opens and closes with Esc, choosing a kind still works).
- Found and fixed while checking: "Best for" only translated its prefix (now two spans); the "Best for" line made the
  Step 1 cards too long (now only in the dialog); clicking the middle of a narrow card opened the example instead of
  choosing the kind (the example button is now a corner icon).
- Tests: `tests/test_template_samples_browser.py` (3) + Step 1 / Shorts batch / roots / grammar browser tests, 24 passed.

## Owner review of the Shorts batch page (2026-11-03)

- "bố cục giao diện khá bất hợp lý trong trang short hàng loạt": with the clips, the kind cards were two per row and
  very tall, so steps 2 and 3 were far down, and the preview showed placeholder text before any idea. Step 1 now spans
  the full width with compact cards (clip left, text right; 4 per row at 1300 px; its height went from ~1330 px to
  844 px), and the preview beside steps 2–3 shows the chosen kind's example clip until ideas exist, then the live
  preview of the selected idea.
- "sao trong short lại có cả loại video dài khổ ngang?": the conversation, presenter and VOX kinds of the batch are
  vertical Shorts, but their example clips were cut from the 16:9 long videos. The batch page now uses vertical clips
  cut from the owner's own conversation, presenter and VOX Shorts (`*_short`), Step 1 keeps the 16:9 clips for the
  long video types, and the group is named "Short có nhân vật, người dẫn hoặc hình ảnh (dọc 9:16)". 19 clips, 2.38 MB.
