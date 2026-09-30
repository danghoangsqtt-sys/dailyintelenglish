# Phase 20 — Task 20.2e spike report: Animagine XL 4.0, two anime styles, render-then-cut

- **Run:** owner machine (RTX 3060 12 GB), runbook r5, 2026-09-30.
- **Pinned code:** `c8bac2d`.
- **Evidence:** branch `owner-runs/20260930-r5` @ `beafe53`, folder `owner-runs/20260930-r5/`.
- **Design:** `.viepilot/phases/20-ai-visuals/tasks/task-20.2e.md`.
- **Status:** **awaiting the owner's verdict.** The observations below are the Coder's
  reading.

## 1. Run facts

| Phase | Wall (s) | Download (s) | Load (s) | Per image (s) | Peak allocated / reserved (MB) | Error |
|---|---|---|---|---|---|---|
| p1 text2img: 4 scenes + 4 candidates | 1444 | **1256** (first fetch, 6.8 GB) | 5.2 | 19.8–20.2 | 9170 / 11610 | none |
| p2 + IP: 8 assets, 2 encodes (CFG) | 240 | 0.8 | 4.8 | 25.5–28.3 | 11185 / 13746 | none |
| p3 ControlNet-inpaint + anime-seg: 8 renders | 269 | 0.8 | 8.2 | 29.3–30.1 (+0.15–0.18 s cut) | 10929 / 11972 | none |
| p4 frames | — | — | — | — | — | none |

- **The anime fine-tune is a drop-in replacement.** Speed and VRAM are identical to SDXL
  base (r4). The lease, the encode→render split, ControlNet, IP-Adapter and anime-seg all
  worked unchanged.
- **Finding F2 (production note):** the one-time 21-minute download happened **inside
  the GPU lease** (the GPU sat idle but reserved). Production must pre-fetch weights
  outside any lease.
- p2 still reserves 13.7 GB (IP + CFG); its time is steady. This is the same as r4.

## 2. Observations (Coder's reading; the owner decides)

1. **Style: now genuinely anime** (`sheet_style.png`).
   - **A `action_webtoon`:** dark blue night palette, purple neon rim light, dramatic
     shadows.
   - **B `bright_anime`:** sunny TV-anime look.
   - Scenes are clean in both.
   - In A, skin sometimes turns grey or blue under the cool lighting (kitchen thinking).
2. **Character** (`sheet_character.png`).
   - **The same design in all assets and renders:** black bob, blunt bangs, blue eyes,
     white shirt, black jacket.
   - **Expressions now change** (neutral, open smile, surprised), unlike 20.2c.
   - The side view is still only a slight turn.
   - **Outfit drift, mostly in B:** a yellow cardigan (classroom waving), a light-blue
     shirt with a black pinafore (kitchen). Style A kept the black jacket every time.
3. **Actions: 4 of 4 followed in both styles**, including hand-to-chin (the tag worked;
   20.2c failed at it).
4. **Render-then-cut** (`sheet_m2.png`, blend vs cut).
   - **The halo is gone in 7 of 8.**
   - **One failure: B classroom waving.** anime-seg kept only the head (foreground 0.044,
     against 0.19–0.24 elsewhere), so the frame shows a floating head.
   - **Fix, a QC gate:** if the segmented foreground inside the silhouette is below ~40%
     of the silhouette area, reject the cut and fall back to blend, or re-render with the
     next seed. The number is already in the worker response.
   - A small leftover: a soft edge where an arm leaves the silhouette mask (A classroom
     pointing, right sleeve).
5. **Frames** (`sheet_frames.png`): polished anime-lesson look in both styles; captions,
   chips and the vocab card are readable.

## 3. Coder recommendation (pending the owner's verdict)

- **Adopt Animagine XL 4.0 + render-then-cut with the QC gate**, in the owner's chosen
  style (A or B).
- **Next, before the library backend:**
  - lock the outfit (stronger outfit tags plus an outfit reference);
  - pre-fetch weights outside the lease (F2);
  - widen the silhouette around raised arms.

## Owner verdicts (to be filled from the owner's answers)

- Style A (action_webtoon) or B (bright_anime)?:
- Character OK now?:
- Halo gone?:
- Frames OK?:
