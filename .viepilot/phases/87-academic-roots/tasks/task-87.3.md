# Task 87.3 — `RootsScene` renderer

See [PLAN.md](../PLAN.md), D127.

## Design (written before code)

- Props: for `shortStyle = "roots"` each line carries `roots` (its beat card from `language_notes.roots`) and, when a
  picture was drawn, `roots.pictureUrl` (87.4). `types.ts` gains the `roots` line field and the `"roots"` short style.
- `renderer/src/rootsMath.ts` (pure, vitest): word colouring from parts (root = brand green, prefix/suffix = ink),
  split progress (parts slide apart and a "+" appears over 0.5 s from the beat start), underline draw progress, wheel
  positions for the promise beat, which word stays on screen across whole → split → example.
- `renderer/src/RootsScene.tsx`: cream paper (shared `Paper`), the word in Bangers (bundled OFL, Vietnamese glyphs),
  slightly skewed like hand lettering; hand-drawn yellow underline that draws itself; meaning in Patrick Hand (bundled
  OFL, Vietnamese glyphs) in dark green; the breakdown line; the picture (Qwen line art, revealed by a left-to-right
  wipe) or, without one, the word's line icons drawn stroke by stroke (87.4); the example in Patrick Hand with the small
  Vietnamese gloss; beats: hook, twins (two words, the shared head green, the rest muted), wheel (head in the middle,
  words around), origin ("Gốc Latin", head, origin form = meaning), head / head_logic / head_example, whole, split,
  example, quiz ("Đoán từ cuối nhé!", "= ?"), follow. A centred one-phrase caption of the spoken line at the bottom of
  the safe zone, karaoke-highlighted word in green. Content stays inside `SAFE`.
- `Episode.tsx` routes `shortStyle === "roots"` to `RootsScene`; `sampleShort.ts` gets a roots sample for the batch
  page's silent preview.
- `backend/media/video_renderer_remotion.py` passes each line's card (like the slow podcast's translation).

## Paths

`renderer/src/types.ts`, `renderer/src/rootsMath.ts`, `renderer/src/RootsScene.tsx`, `renderer/src/Episode.tsx`,
`renderer/src/sampleShort.ts`, `renderer/public/fonts/` (PatrickHand-Regular.ttf, Bangers-Regular.ttf + OFL texts),
`backend/media/video_renderer_remotion.py`, `renderer/src/roots.test.ts`, a pytest for the props.

## Verification

`npx vitest run`, `npx tsc --noEmit`, pytest for the props; frames checked in 87.6.

## Result (2026-11-03)

Stills of every beat of the silent sample rendered with `remotion still` and checked (hook, twins, wheel, split
with "+", example with the gloss, quiz). `npx tsc --noEmit` clean; vitest 26 files / 198 tests passed; the props test
(`tests/test_roots_script.py`) checks the cards and picture URLs.
