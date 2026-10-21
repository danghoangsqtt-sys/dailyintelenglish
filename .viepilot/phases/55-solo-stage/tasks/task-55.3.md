# Task 55.3 — Renderer stage

Status: implemented_verified 2026-10-21 (visual check in 55.5).

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

## Verification result 2026-10-21

- New `renderer/src/SoloStage.tsx`: segment plate (cover) with the conversation `sceneMotion` drift, 0.6 s crossfade when the scene changes (`stagePlates`, pure), activity picture full-frame with the conversation `insertMotion` reveal, top shade for the brand line; `StageShade` over the legs under captions. `SoloScene` draws stage → card → presenter → shade → captions. Cards are translucent with a shadow; activity visuals draw no card.
- `soloTypes`: `activity` visual, `scene`, payload `scenes`/`activities`; payload schema accepts rules 1 and 2.
- Vitest 127 passed (new `soloStage.test.ts`: steady plate, crossfade + deterministic seek, no-scene fallback); `tsc --noEmit` clean; `npm run build:preview` built `frontend/static/solo-preview/player.js`.
