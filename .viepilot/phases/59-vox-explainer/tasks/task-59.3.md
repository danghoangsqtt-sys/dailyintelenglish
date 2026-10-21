# Task 59.3 — Renderer VoxScene

Status: planned 2026-10-22.

## Paths
- renderer/package.json (`world-atlas` dependency, owner-approved), renderer/src/VoxScene.tsx, VoxVisual.tsx, voxMap.ts (new), soloTypes.ts, Episode.tsx
- renderer/src/vox.test.ts (new)

## File-Level Plan
`Episode` picks `VoxScene` when `solo.style === "vox"`. `soloPayloadSchema` keeps 21 pictures for Solo and accepts 0 for VOX. VoxScene: warm paper board (CSS layers, subtle grain), the segment's scene plate as a faded, slowly zooming backdrop, the brand line and the captions as in Solo. Per visual, driven by the segment's speech progress:
- text_card / quote: words appear one by one; a highlighter bar sweeps behind the emphasis/highlight phrase; quotes look cut out (paper strip, slight tilt).
- photo / activity: a collage card (white border, small tilt, shadow) with Ken Burns zoom/pan, a drawn circle on the first important region (or the centre) and an arrow.
- diagram: nodes pop in in order with connecting arrows.
- chart: bars grow / the line draws (stroke-dash) with value labels; axis from 0.
- timeline: a line drawn left to right, dots and labels appear in order.
- map: countries from `world-atlas` countries-110m decoded by our own small TopoJSON decoder (`voxMap.ts`), equirectangular projection cropped to the places, highlighted countries, pins with labels, an animated route arrow.
Pure helpers (word reveal, highlight span, chart scale, timeline positions, TopoJSON decode, projection bounds) are unit-tested.

## Tests
vitest for the helpers and the schema switch; existing Solo renderer tests unchanged.
