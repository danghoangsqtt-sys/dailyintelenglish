# Task 92.1 — Clip maker

See [PLAN.md](../PLAN.md), D134–D136.

## Design (written before code)

- `renderer/samples.json`: per kind `{idea: {title, brief}, from, seconds}` (the window that shows the kind best) for the
  13 sample templates; `sources` for `conversation`, `presenter`, `vox`: `{file, from, seconds}` — the owner's own
  finished videos (D136), skipped with a warning when the file is missing.
- `renderer/scripts/render-samples.mjs`: esbuild bundles `src/sampleShort.ts` to a temporary module to call
  `sampleProps(template, idea, "B1", audience)`; `@remotion/bundler` bundles the composition once;
  `@remotion/renderer` `renderMedia` (Episode, h264, muted, scale 1/3, the window's frames) for audience `vietnamese`
  (file `-vi`) and `international` (`-en`), then a poster with `renderStill`; roots / grammar samples are Vietnamese
  only (`-vi` is used for both). ffmpeg cuts the 16:9 sources (640×360, no audio, CRF 30) and their posters.
  Output `frontend/static/samples/{kind}-{vi|en}.mp4|jpg` and `index.json` (`{kind: {vi, en, poster_vi, poster_en,
  seconds, bytes}}`). The run fails when the total is above 8 MB.
- `npm run render:samples` in `renderer/package.json`.

## Paths

`renderer/samples.json`, `renderer/scripts/render-samples.mjs`, `renderer/package.json`, `frontend/static/samples/*`.

## Verification

Run it; check sizes, play a few clips, look at posters.
