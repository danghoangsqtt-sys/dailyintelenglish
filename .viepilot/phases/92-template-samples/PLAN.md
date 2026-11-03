# Phase 92 — Example clips for every kind of video (2026-11-03, planned)

Owner (2026-11-03): "các dạng video nếu chỉ có mỗi tên và mô tả thì người dùng mới sẽ khó hiểu và không biết dùng
ntn, có nên thêm các dạng gif video ví dụ để người dùng dễ lựa chọn không?", then "Lập kế hoạch".

## Today

- Step 1 shows 4 video types (conversation 16:9, solo presenter, VOX, Shorts) and 13 Short templates as cards with a
  name and one line of text. The Shorts batch page shows the same kinds (16 with the conversation / presenter / VOX
  Shorts) and a silent live preview of the chosen kind (`window.ShortsSample` + the Remotion player), but only after a
  kind is chosen and only for the 13 templates that have sample props (`renderer/src/sampleShort.ts`).
- The conversation, presenter and VOX videos have no sample props (they need character sprites, presenter packs or
  pictures from the libraries).

## Decisions (defaults; the owner may change them)

- **D134 — short muted MP4 loops, not GIF:** 5–6 s, 9:16 at 360×640 (16:9 at 640×360), H.264, no sound, about
  200–400 KB each (a GIF is 5–10× larger and blurs the text on the cards). Each has a poster image for reduced motion.
- **D135 — made by the app's own renderer from the sample props**, so a template's clip is made again when its look
  changes; Vietnamese and English versions, shown by the channel's audience (Việt Nam / Cả hai → Vietnamese text,
  Quốc tế → English).
- **D136 — the three 16:9 kinds use 6 s cut from the owner's own finished videos** (a list of source files and times in
  a manifest the owner can change); no new sample scenes are invented for them.
- **D137 — labelled "Ví dụ minh hoạ"** with a "Phù hợp cho…" line, so nobody expects their video to be this one.

## Tasks

1. **92.1 Clip maker** — `renderer/scripts/render-samples.mjs`: bundle once; for each sample template and language
   render the chosen 5–6 s window of `sampleProps(template, idea, level, audience)` (window per template in
   `renderer/samples.json`), 0.33 scale, muted, then a poster frame; the three 16:9 kinds are cut with ffmpeg from the
   manifest sources. Output `frontend/static/samples/{kind}-{vi|en}.mp4|jpg` and `index.json` (kind → files, seconds,
   bytes). A size check fails the run above 8 MB in total. Paths: `renderer/scripts/render-samples.mjs`,
   `renderer/samples.json`, `frontend/static/samples/*`, `renderer/package.json` (script `render:samples`).
2. **92.2 Cards with clips** — `frontend/static/js/template_samples.js` (new): adds a small clip to every kind card in
   Step 1 (video types and Short templates) and in the Shorts batch page; it loads lazily, plays on hover, focus or
   selection and pauses otherwise, shows the poster when the viewer prefers reduced motion; "Xem ví dụ" opens a larger
   clip in a dialog with "Ví dụ minh hoạ" and "Phù hợp cho…" (one line per kind, e.g. "dạy một điểm ngữ pháp cho
   người Việt, 1–3 phút"). Copy in `i18n_vi.js`. Paths: `frontend/static/js/template_samples.js`,
   `frontend/pages/step1_config.html`, `frontend/pages/shorts_batch.html`, `frontend/static/js/step1_config.js`,
   `frontend/static/js/shorts_batch.js`, `frontend/static/css/style.css`, `frontend/static/js/i18n_vi.js`.
3. **92.3 Packaging** — the samples ship in the desktop package (`frontend/static` is already bundled; checked in the
   spec and a package test), and `render:samples` is documented for when a template's look changes.
4. **92.4 Verify** — browser tests (every kind card has a clip and a "Phù hợp cho" line, hover plays, reduced motion
   shows the poster, the dialog opens and closes with Esc), size budget test, and the owner's look at Step 1 and the
   Shorts batch page.

Task cards are written when the phase starts.
