# Phase 20 — Task 20.2b spike report: character library feasibility

- **Run:** owner machine (RTX 3060 12 GB), runbook r3, 2026-09-30.
- **Pinned code:** `88b01d4`.
- **Evidence:** branch `owner-runs/20260930-r3` @ `1116597`, folder `owner-runs/20260930-r3/`
  (4 sheets, 21 full-size images, `L_r3.json`, worker logs).
- **Design:** `.viepilot/phases/20-ai-visuals/tasks/task-20.2b.md`.
- **Status:** **awaiting the owner's verdict** (the four questions at the end). The
  observations below are the Coder's reading of the images, not a decision.

## 1. Run facts

| Phase | Wall (s) | Model load (s) | Per image (s) | Peak VRAM allocated / reserved (MB) | Error |
|---|---|---|---|---|---|
| p1 style, Lightning | 50 | 13.6 | 2.2–6.1 | 9150 / 13134 | none |
| p1 style, base (30 steps) | 91 | 11.7 | 22.1–27.6 | 9170 / 13320 | none |
| p2 20 assets (Lightning + IP-Adapter) | 225 | 7.4 | 9.7–10.9 | 11164 / 13582 | none |
| p2 encode (4 action prompts + IP embeds) | — | — | 0.25 total | — | none |
| p3 4 actions (Lightning + ControlNet, no encoders) | 833 | **790** | 8.0–9.1 | 10790 / 12966 | none |
| p4 9 cut-outs (anime-seg, CPU) | 52 | — | 0.8–0.9 | — | none |
| p5 M1 composites (Pillow) | — | — | 0.17–0.20 | — | none |
| p6 M2 inpaint (base + IP-Adapter) | 80 | 13.1 | 26.5–27.2 | 11148 / 12476 | none |

- Every phase ran with no OOM and no error. Every file the runbook listed is present.
- **Lease:** qwen was already idle, so no evictions. Free VRAM went 11578 MB at the start
  → 11654 MB at the end: each worker exit returned its VRAM.
- **p3's 790 s load is the one-time first download** of the ControlNet OpenPose weights
  (2.5 GB). It is not a per-run cost.
- **The encode→render split works on the real card.**
  - ControlNet rendering with no text or image encoders peaked at 10.8 GB allocated.
  - Loading SDXL + IP-Adapter + ControlNet together would be about 13.6 GB and could
    not fit.

### Finding F1: the VRAM reserve exceeds the physical card (slowdown, not a failure)

- Lightning scenes at 1344×768 reserved 11338 MB and took 2.2–2.8 s each. That matches
  the 20.2 run.
- Switching the same worker to 1024×1024 portraits raised the allocator's reserve to
  13134 MB and the time to 5.3–6.1 s. Allocated memory barely moved (9112 → 9150 MB).
- 13.1 GB reserved on a 12 GB card means the Windows driver spilled into shared system
  memory (WDDM sysmem fallback). That also plausibly slows p2 (reserved 13.6 GB).
- **Fix for the production worker (Task 20.3+):**
  - release cached blocks (`torch.cuda.empty_cache()`) whenever the output size changes;
  - or keep one image size per worker lifetime.
- This is **no change to the spike code**; it is recorded for the real worker.

## 2. Observations (Coder's reading; the owner decides)

### Q1 Style (`sheet_style.png`)

- The descriptive preset gives a consistent soft, hand-painted anime look: watercolor
  backgrounds, warm window light, pastel palette.
- Scenes (classroom, kitchen) are clean and have no people or text.
- Lightning and base are close in quality. Base is slightly softer and more painterly,
  but 10× slower (22 s vs 2.2 s).
- Whether it is "Ghibli-like enough" is the owner's call.

### Q2 Identity (`sheet_character.png`, `sheet_actions.png`)

- **Strength:** the face, hair, glasses and green cardigan are clearly the same person in
  all 20 assets and all 4 actions.
- **Problem A, the IP-Adapter over-copies the reference.** Scale 0.7 with the
  plus-face model copies more than the face:
  - The same pose (hand to cheek) and the same library background appear in almost every
    head-and-shoulders asset, although the prompts asked for different views and
    expressions.
  - **The 5 expressions are barely distinguishable** (surprised and sad look close to
    neutral).
  - The two three-quarter views barely turn the head.
- **Problem B, outfit drift in the body shots.**
  - The full-body set wears jeans, not the specified brown skirt.
  - Across actions, the skirt changes colour (yellow), becomes shorts (pointing), and a
    handbag appears.
- **What works well: pose control.** All 4 OpenPose actions (waving, pointing, hand to
  chin, cheering) were followed accurately. This is the "not stiff, action fits the
  content" mechanism the owner asked for.
- **Fix ideas, to test in a follow-up run:**
  - IP scale about 0.4–0.5;
  - a clean reference: neutral pose, plain background, face crop;
  - stronger expression and view wording;
  - a full-body reference for outfit identity;
  - generating all actions with ControlNet so the body is always pose-driven.

### Q3 Cut-outs (`sheet_actions.png`, column 3)

- Waving, pointing and cheering are cleanly cut (soft-edge fraction 0.019–0.026).
- **Thinking left a ghosted lower body.** Its soft-edge fraction of 0.054 is 2× the
  others, so this metric works as an automatic quality flag for cut-outs.
- The 5 full-body assets are clean (0.019–0.020).

### Q4 Composition (`sheet_composites.png`)

- **M1 (naive and integrated): the placement is wrong.**
  - The fixed stage spot (floor line at 95% of the height) lands on foreground
    furniture, so the character stands **on** the desk or the kitchen table and reads as
    a small figurine.
  - Naive vs integrated differ only slightly. The shadow and colour match cannot rescue
    a wrong floor point.
  - **Implication for the Scene Library:** each saved scene needs an authored stage spot
    (floor point + character height, set once when the scene is saved), or scenes need
    to be generated with an explicit empty floor area.
- **M2 (inpaint + IP): the most natural lighting and integration.** The character sits at
  the desk or table and shares the scene's light. But:
  - the classroom render shows a **visible rectangular seam** at the mask box;
  - the face drifts from the reference (the kitchen hair is lighter brown);
  - the requested action is ignored, because this path has no ControlNet;
  - the scale follows the model, not the stage spot;
  - it costs about 27 s per image on base.

## 3. Coder recommendation for the next step (pending the owner's verdict)

1. **Keep:**
   - SDXL-Lightning;
   - the style preset;
   - OpenPose actions;
   - anime-seg with the soft-edge QC flag;
   - the encode→render split.
2. **Fix identity before building the library backend.** A short follow-up spike, **20.2c**:
   - lower IP scale;
   - a clean reference;
   - an outfit reference;
   - stronger expression prompts;
   - `empty_cache` on size change (F1).
3. **Composition candidate:**
   - **M1 with authored stage spots**, plus a light **img2img harmonisation pass** at low
     strength on Lightning (a few seconds);
   - M2 kept as the "hero image" option **only if** the seam is fixed (larger feathered
     mask, and ControlNet pose added so the action is honoured).

## Owner verdicts 2026-09-30 (verbatim, with translation)

1. **Style / model:** *"phong cách chưa giống ghibli lắm nhưng ảnh của base tạo đẹp hơn
   nhiều và có linh hồn hơn, của lightning tạo nhiều hơn nhưng nhiều ảnh lỗi quá"*.
   - The style is not very Ghibli-like yet.
   - **Base is much prettier and has more soul.** Lightning is faster but produces too
     many defective images.
   - This **reverses the 20.2 model choice: SDXL base (≈22–27 s/image), not Lightning.**
2. **Character:** *"biểu cảm trang phục quá phức tạp nên dễ lỗi tôi nghĩ cần đơn giản hóa
   nhiều hơn"*. The expressions and outfit are too complex and error-prone, so **simplify
   the character design.**
3. **Backgrounds vs on-screen text:** the video has dialogue captions at the bottom and
   the vocabulary card top-right.
   - A highly detailed background will hurt text legibility, compared with the current
     solid or black background.
   - The owner wants this **thought through further (open question).**
   - Layout options mocked up with the real r3 M2 image on the real 1280×720 layout:
     `docs/operations/phase20-layout-mockups.png`.
     - A: full-bleed as-is;
     - B: full-bleed, dimmed, softly blurred, with a dark gradient under the captions;
     - C: the scene in a rounded "window" frame, with the text zones kept on the dark
       background.
4. **Composition:** *"M2 tự nhiên hơn rất nhiều còn m1 chỉ tạo ra rác"*. **M2 (inpaint
   into the scene) is far more natural; M1 (cut-out collage) is rejected.**
   - Consequence: anime-seg cut-outs are no longer needed for scene composition.
- Cut-out quality was not separately judged; it is moot for scenes after verdict 4.
