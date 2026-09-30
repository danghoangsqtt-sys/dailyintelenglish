# Phase 20 — Task 20.2c spike report: SDXL base, simple character, pose-controlled M2, video frames

- **Run:** owner machine (RTX 3060 12 GB), runbook r4, 2026-09-30.
- **Pinned code:** `81f6c67`.
- **Evidence:** branch `owner-runs/20260930-r4` @ `b53b5c2`, folder `owner-runs/20260930-r4/`
  (4 sheets, 24 full-size images, `L_r4.json`, worker logs).
- **Design:** `.viepilot/phases/20-ai-visuals/tasks/task-20.2c.md`.
- **Status:** **awaiting the owner's verdict.** The observations below are the Coder's
  reading, not a decision.

## 1. Run facts

| Phase | Wall (s) | Load (s) | Per image (s) | Peak VRAM allocated / reserved (MB) | Error |
|---|---|---|---|---|---|
| p1 base: 2 scenes 1344×768 + 3 candidates 1024² | 120 | 6.8 | 21.1–21.4 | 9170 / 11610 | none |
| p2 base + IP: 6 assets + full body, encode (CFG) | 222 | 5.0 | 26.8–29.3 | 11185 / 13746 | none |
| p3 base ControlNet-inpaint, no encoders: 8 renders | 280 | 8.1 | 31.5–33.1 | 10929 / 11972 | none |
| p4 frames (Pillow) | — | — | 0.14–0.16 | — | none |

- **The 20.2b F1 fix is confirmed.**
  - p1 switched from 1344×768 to 1024² in one worker. The reserve stayed at 11610 MB
    (r3: 13134 MB), and the time stayed flat at 21.1–21.4 s (r3: 2.2 s → 6.1 s on the
    switch).
- **p2 still reserves 13.7 GB** (IP-Adapter + CFG at 1024² / 832×1216). The time is
  steady, so spillover is at most mild. Note it for the production worker's budget.
- **p3 fits:** 11.97 GB reserved. The encode→render split works for base + ControlNet +
  IP with CFG.
- **Lease:** no evictions (qwen idle); the free VRAM baseline returned after each worker.
- **Cost per episode image on base:** a scene takes ≈ 21 s; a character-in-scene render
  takes ≈ 33 s.

## 2. Observations (Coder's reading; the owner decides)

1. **Style v2** (`sheet_style.png`): a clear move toward a hand-drawn, retro
   cel-animation look, with flat shading, muted earthy colours and painted backgrounds.
   Both scenes are clean, with a calm lower third.
2. **Character.**
   - **The design survives in every M2 render:** a dark bob with bangs and a mustard
     dress.
   - **Details drift:** the collar comes and goes, the shade of yellow changes, and a
     skirt appears in one render.
   - **The 6-asset identity set failed.**
     - All 6 are near-copies of candidate #1's composition (at a desk, the same window,
       the same pose).
     - Views and expressions barely change, even at IP scale 0.5.
     - The candidates also ignored "plain light background".
     - IP-Adapter plus-face copies the reference's layout, not just the face. A
       library reference must be a **tight face crop on a plain background**, likely at
       a lower scale. That needs its own fix.
3. **M2 with pose control** (`sheet_m2.png`).
   - **The rectangular seam is gone.**
   - **The action is followed in 3 of 4 cases:**
     - waving, pointing up (toward the vocab card) and explaining are followed;
     - **hand to chin (thinking) is not**: the hands stay on the table at both
       strengths.
   - Strict (1.0) follows the pose better; loose (0.7) is weaker and smearier.
     Recommendation: **strict**.
4. **New artifact: halo/smear at the silhouette edge.**
   - Examples: dark haze around the hair (kitchen explaining), a blurred torso edge
     (classroom pointing), a faint ghost patch beside the raised hand (classroom waving,
     loose).
   - **Cause:** inside the feathered border the model paints its own version of the
     background, which is then half-blended with the real scene.
   - **Fix candidate: "render then cut".**
     - Run `skytnt/anime-seg` (already in `venv-image` since 20.2b) on the M2 render.
     - Composite **only the character's own alpha** (lightly feathered) onto the
       untouched scene.
     - This keeps M2's natural lighting and pose, and drops the smear.
5. **Frames** (`sheet_frames.png`): full-bleed, with the outline captions, speaker chips
   and vocab card all readable. The layout reads like a finished animated lesson.

## 3. Coder recommendation (pending the owner's verdict)

- **Keep:**
  - SDXL base;
  - style v2;
  - the simple character design;
  - presenter framing;
  - strict pose;
  - the frame layout with outline captions.
- **Fix before the library backend (20.2e, a short follow-up run):**
  - **render-then-cut** compositing (anime-seg on the M2 render) against the edge smear;
  - **a face-crop reference** on a plain background, with a lower IP scale, against the
    near-identical assets;
  - a stronger "hand touching chin" pose/prompt pair, or drop that action.

## Owner verdicts (to be filled from the owner's answers)

- Style v2 on base: closer to the wanted look?:
- Simple character recognisable across views / expressions / actions?:
- M2 natural, no seam? Pose strict or loose?:
- Frames with captions look professional?:
