# Task 55.3 — Renderer stage

Status: planned 2026-10-21.

## Paths
- renderer/src/SoloScene.tsx, Presenter.tsx, ExplainerVisual.tsx, soloTypes.ts (+ tests)

## File-Level Plan
- Background: the segment's scene plate, cover, conversation `sceneMotion` zoom, crossfade on scene change; vertical uses the picture area and ambient fade like `SpriteStage`.
- Activity visual: full-frame insert over the plate with the conversation `insertMotion` reveal.
- Cards/diagrams: same text metrics, semi-transparent dark panel.
- Presenter: v2 canvas from `presenterBoxes`; bottom shade under captions; mouth/blink/gesture timeline unchanged.
- `soloPayloadSchema` accepts rules v2 and `scenes`/`activities` maps.

## Verification
Vitest for layout math and payload schema; TypeScript; `npm run build:preview`.
