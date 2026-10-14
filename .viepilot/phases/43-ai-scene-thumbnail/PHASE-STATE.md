# PHASE-STATE — Phase 43: "AI scene" thumbnail drawn locally by Qwen-Image-Edit (D122)

- **Status:** planned 2026-10-14 (owner "okey" to the proposal); 43.1-43.4 done 2026-10-14; 43.5 real draw done, **waiting for owner Gate B-27**.
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
| 43.1 | **Worker: multi-reference Qwen edit.** `qwen_runner.generate_qwen_edit` accepts `references` (1–3 pictures; sprites flattened on white) besides the single `reference` used by inserts; one load per batch. A prompt recipe `recipes.qwen_thumbnail_scene_prompt` built from the same rules as the outside-AI prompt (pair in the right 55 %, head-and-shoulders, heads apart, plain left side, corners free, no text/logo). Draw **1536x720** (wider than the frame) so the app can choose the 1280 window. Tests with the fake engine | done |
| 43.2 | **Find the people, choose the frame.** Run the worker's existing ONNX face detector (`count_faces`, Task 28.5) on the drawn picture -- face boxes, widened to the head (hair) as the keep-out zone; the `isnetis.onnx` people mask only if faces are not found (no new dependency). Crop the 1280x720 window that leaves the widest free side for the headline (≥ 45 % of the width) and keeps heads ≥ 60 px from the edges; pick the layout (text left or right) from the free side. If no window gives 40 %, mark the variant "crowded" so the UI offers "Draw again". Unit tests on synthetic masks | done |
| 43.3 | **Compose.** `thumbnail_compose.ai_scene_picture` + template `ai_scene`: 16:9 = the chosen 1280x720 window, headline/pill/badges/logo in the computed text box, the shade reaching just past the title strip (faces keep their light); the supporting pill shrinks to the title box (all kinds). **Changed from the plan:** 9:16 needs no second GPU draw -- the band around the faces fills the lower part, the same scene enlarged, blurred and darkened carries the headline above it. Corner cleaning: not needed after 43.1 (the new prompt drew no fake logo or lettering in 3/3); the real badges/logo still cover the top corners | done |
| 43.4 | **Step 6 UI.** A third kind card "AI scene (local Qwen)" with the honest time ("about 1–2 minutes per variant"), a background job with progress and ETA, per-variant "Draw again", GPU-busy and model-missing messages (fallback: suggest the composed kind). The project folder (Phase 41) gets the favorite as usual | done |
| 43.5 | **Real run and Gate B-27.** Ep. 2 "Shopping at the Market" (Hoang, Kim): 3 variants on the real app, timing recorded, frames checked against the thumbnail rules (headline never on a face, faces ≥ 150-px-readable, corners); owner review **Gate B-27** | waiting for owner (Gate B-27) |

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

## As built

- **43.1 (2026-10-14):** `qwen_runner.references_of` / `_flat_reference` (sprites laid on white), `validate` accepts
  `references` (1-3 paths); `recipes.qwen_thumbnail_scene_prompt(names, topic, scene)`. Tests:
  `tests/test_phase43_ai_scene_thumbnail.py`. Real GPU check with the production runner, Hoang + Kim sprites,
  1536x720, 3 seeds: load 76 s, 90-94 s per picture; all three put the pair right of centre with a clean blurred left
  side and **no fake logo or lettering** (the earlier 1280x720 trial with the outside-AI prompt had both)
  (`D:\Example-videos\walkthrough-2026-10-14-ai-scene-raw-*.png`).
- **43.2 (2026-10-14):** `backend/media/ai_scene.py` -- `head_zones` (face box widened 25 % each side, raised 45 % for
  the hair) and `choose_frame` (slides the 1280 window over the 1536 draw, picks the side with the widest free strip,
  sizes the headline box to that strip minus margin and gap, flags "crowded" below 33 % or with a head in the
  duration-stamp corner). On the three real draws: text left, window x 0, free 38.7-39.2 %, headline box ~32 % wide.
  Face boxes from the worker's existing ONNX detector (no new dependency).
- **43.3 (2026-10-14):** previews of 3 variants at 16:9 and 9:16 from the real draws
  (`D:\Example-videos\walkthrough-2026-10-14\35-ai-scene-*.jpg`): titles never touch a head, faces big and unshaded.
- **43.4 (2026-10-14):** kind id **`qwen_scene`** (not `ai_scene`: that id was the old kind D92 removed). Worker
  `qwen_generate` returns the faces of each drawn picture when asked (`detect_faces`); `ai_scene.draw_scenes` /
  `load_scenes` / `clear_scenes` store `data/thumbnails/<project>/ai_scenes/scenes.json`; API `POST/GET
  /thumbnails/ai-scenes`, `GET /thumbnails/ai-scenes/{i}`, `POST /thumbnails/ai-scenes/{i}/redraw`; the composition
  carries `ai_scenes` so an edit re-renders the same picture. Step 6: an "AI scene" panel (1-3 pictures, elapsed/ETA,
  pictures with "title on the left/right" or a red "Crowded / No faces" note and "Draw again"); after drawing, the kind
  is available and selected. A request is synchronous like the topic picture and the video render (minutes).
- **43.5 (2026-10-14):** real app, Ep. 2, Step 6 "Draw AI scenes" x3: 201 in ~6 min (load + 86.7-92.2 s per
  picture), 2 faces found on each, none crowded (free 33-38 %), title on the left. The owner had already generated
  outside-AI thumbnails from their ChatGPT picture, so the "Generate" click (which replaces the variant set) is left to
  the owner; offline renders of the three real scenes: `39-real-ai-scene-thumbnails.jpg`, `39-real-ai-scene-9x16.jpg`.
- **Owner review (2026-10-14):** "not as bright and fresh as ChatGPT". Try 1 (high-key close-up + strong grade) blew
  out the highlights, changed Kim's hair colour and left only 26-30 % for the title (all three "crowded"). Try 2
  (natural daylight, medium shot from the waist up with open gestures, the place visible on the left, hair colour named,
  a gentle grade: levels 0.2 %, brightness 1.03, colour 1.1, sharpness 1.15; lighter title shade) on Ep. 2: 3/3 fine,
  free side 43-48 %, 87-105 s per picture (`42-natural-daylight-thumbnails.jpg`).
