# Task 88.2 — `GrammarScene` renderer

See [PLAN.md](../PLAN.md), task 88.1 for the card data.

## Objective

Draw a `grammar` Short (9:16) from its lines: paper background, coloured scene pill ("PHÂN CẢNH 2 • BẢN CHẤT CỐT
LÕI"), bold capital title and a subtitle, rounded cards with a soft shadow that stack down as the narration reaches
them, the fixed colour code, the red "forget it" stamp, the summary table filling row by row, a karaoke caption.

## Design (written before code)

- `renderer/src/grammarMath.ts`: `CHIP_COLOURS` (s brand green, v red, o brown, be blue, ing orange, v3 yellow sticker
  with dark text, modal purple, have teal, adj pink, plain ink), `chipColour(role)`, `shownBefore(lines, index)` (how
  many cards of the current scene the previous line already showed, so only new ones animate in), `rowsBefore` (the
  same for table rows), `stackScale(count)` (so up to four cards fit between title and caption), `pillText`.
- `renderer/src/GrammarScene.tsx`: `Paper` from SlowPodScene, Bangers for the title, Patrick Hand / Montserrat for the
  cards (fonts bundled in 87.3), one component per card kind (formula chips, compare columns EN + VI, table, rule pink,
  example EN with coloured marks + VI gloss, sticker yellow tag, stamp red rotated, lego "BE + -ING = BEING"); new cards
  slide in from below, older ones stay; the quiz card has a 3-2-1 countdown ring; karaoke caption like RootsScene.
- `types.ts`: `grammarCardSchema` (line `grammar`), `shortStyle` gets `"grammar"`; `Episode.tsx` routes it;
  `sampleShort.ts` gets a silent passive-voice sample (hook, two scenes, summary, follow).
- Backend: `video_renderer_remotion.py` copies each line's `grammar` card into the props (no pictures).

## Paths

`renderer/src/GrammarScene.tsx` (new), `renderer/src/grammarMath.ts` (new), `renderer/src/grammar.test.ts` (new),
`renderer/src/types.ts`, `renderer/src/Episode.tsx`, `renderer/src/sampleShort.ts`,
`backend/media/video_renderer_remotion.py`.

## Verification

`npx vitest run`, `npx tsc --noEmit`; stills of the sample at a few frames.
