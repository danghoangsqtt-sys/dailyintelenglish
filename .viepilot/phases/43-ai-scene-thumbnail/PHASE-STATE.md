# PHASE-STATE — Phase 43: "AI scene" thumbnail drawn locally by Qwen-Image-Edit (D122)

- **Status:** planned 2026-10-14 (owner "okey" to the proposal). Not started.
- **Why:** the owner made a thumbnail in ChatGPT from the app's outside-AI prompt with the two character pictures
  attached: the people stand *in* the scene (light, depth, big smiles), far better than the composed "sticker" kind.
  A trial on this computer (2026-10-14, `D:\Example-videos\walkthrough-2026-10-14\32-*.png`) showed
  Qwen-Image-Edit-2511 (Q4 GGUF + 4-step Lightning, both sprites as references, 1280x720) reaches a similar look:
  model load 79 s, then ~84 s per picture. Faces close to the approved sprites, but redrawn (not pixel-exact).
  Weak points seen: the pair started at ~37 % of the width (the app's headline covers the left 45 %), and a fake logo
  (top-left) and fake text (bottom-right, "Daiiai") appeared although the prompt forbids them.
- **Keeps the old kinds (owner rule: do not replace modes):** "Characters + illustration" (fast, seconds) and "Your
  outside-AI picture" stay; this is a third kind.

## D122 (owner, 2026-10-14)

A third Step 6 thumbnail kind, **"AI scene (local Qwen)"**: Qwen-Image-Edit-2511 draws the episode's two characters
(their approved sprites as references) in a scene of the topic; the app adds the headline, the supporting line, the
level/episode badges and the logo on the side where the faces are not. Slower (~1.5 min per variant, a background job
with progress); the composed kind stays the quick default.

## Tasks

| Task | Description | Status |
|---|---|---|
| 43.1 | **Worker: multi-reference Qwen edit.** `qwen_runner.generate_qwen_edit` accepts `references` (1–3 pictures; sprites flattened on white) besides the single `reference` used by inserts; one load per batch. A prompt recipe `recipes.qwen_thumbnail_scene_prompt` built from the same rules as the outside-AI prompt (pair in the right 55 %, head-and-shoulders, heads apart, plain left side, corners free, no text/logo). Draw **1536x720** (wider than the frame) so the app can choose the 1280 window. Tests with the fake engine | planned |
| 43.2 | **Find the people, choose the frame.** Run the worker's existing `isnetis.onnx` background removal on the drawn picture to get the people mask (no new dependency); from it the people's left/right extent and head band. Crop the 1280x720 window that leaves the widest free side for the headline (≥ 45 % of the width) and keeps heads ≥ 60 px from the edges; pick the layout (text left or right) from the free side. If no window gives 40 %, mark the variant "crowded" so the UI offers "Draw again". Unit tests on synthetic masks | planned |
| 43.3 | **Compose and clean the corners.** Render with the outside-AI layout on the chosen side: headline + supporting pill + B1/EP badges + logo. Over the top corners the real badges and logo cover what Qwen may have drawn; a soft local blur-and-darken behind the badges/logo and the headline side so any fake logo or letters do not show; the bottom-right corner is left to YouTube's duration badge. The 9:16 version is drawn only for the variant chosen as favorite (720x1280, pair in the lower half), so 3 variants cost ~4–5 min, not 9 | planned |
| 43.4 | **Step 6 UI.** A third kind card "AI scene (local Qwen)" with the honest time ("about 1–2 minutes per variant"), a background job with progress and ETA, per-variant "Draw again", GPU-busy and model-missing messages (fallback: suggest the composed kind). The project folder (Phase 41) gets the favorite as usual | planned |
| 43.5 | **Real run and Gate B-27.** Ep. 2 "Shopping at the Market" (Hoang, Kim): 3 variants on the real app, timing recorded, frames checked against the thumbnail rules (headline never on a face, faces ≥ 150-px-readable, corners); owner review **Gate B-27** | planned |

## Thumbnail rules applied (research 2026-10-14)

Faces readable at 150 px wide (~40–50 % of the frame in single-face guides); rule of thirds with 2–3 elements; headline
3–5 words, bold, outlined; nothing key in the bottom-right duration badge (~20 % x 15 %); ~60 px margins; top corners
hold our badge and logo. Sources: thumbnailtest.com, vidIQ, TubeCore, Search Engine Journal, socialk.it (see the
2026-10-14 conversation summary in `docs/operations/` when written).

## Risks

- Identity drift (Qwen redraws faces): the owner judges at Gate B-27; the composed kind remains for exact faces.
- Time: ~80 s model load + ~85 s per picture on the 12 GB GPU; the job must not block the video render (one GPU lease).
- Prompt adherence of the 4-step model: handled by the wider draw + window choice (43.2) and corner treatment (43.3),
  not by trusting the prompt.
