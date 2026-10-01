# Phase 20 — Task 20.2h spike report: two-person conversation shots, close-ups, solid outfits

- **Run:** owner machine, runbook r8, 2026-10-01.
- **Pinned code:** `887ea85`.
- **Evidence:** branch `owner-runs/20261001-r8` @ `b8365f6`.
- **Design:** `.viepilot/phases/20-ai-visuals/tasks/task-20.2h.md`.
- **Status:** **awaiting the owner's verdict.** The observations below are the Coder's
  reading.

## 1. Run facts

| Phase | Wall (s) | Per image (s) | Peak allocated / reserved (MB) | Notes |
|---|---|---|---|---|
| p1: 4 cards + 10 encodes | 135 | 28.5–30.1 | 11185 / 13746 | all 4 r7 faces found; duo encodes `ip_faces` 2 |
| p2 ControlNet, masked multi-face IP: 20 renders | 927 | 38.3–48.6 | 10930 / 13216 | slower than r7 (36.6–37.6); spill |
| p3 hand repair: 44 hands | 337 | 7.0–7.5 | 8106 / 8910 | |
| p4: 20 frames | — | — | — | |

No errors and no truncated prompts (max 72).

## 2. Observations (Coder's reading; the owner decides)

1. **Single close-ups: good in both styles.** The chest-up framing the owner asked for;
   one hand gesturing.
2. **Reference cards.**
   - Female cards and the `r3_watercolor` male card are right: the male is neat, in a
     light-blue slim shirt.
   - **The `r3_bright` male card copied the orange jacket** from the r7 pick it was
     IP-guided from. That drift then appears in the bright single (a beige jacket over
     the shirt).
   - **Fix:** IP-guide the cards from a **head crop** of the r7 pick, so the face
     transfers and the clothes do not.
3. **Duo shots: they work, but not reliably.**
   - **`r3_watercolor`: 4 of 6 right.** Both close-ups and both café wides show the
     woman left, the man right, as distinct people.
   - The school wides drift: a black skirt; then a yellow shirt on the man, as the
     woman's colour bleeds across.
   - **`r3_bright`: mostly wrong.**
     - The close-ups show two long-haired figures; the man's identity is lost.
     - A school wide has the man on the left in the woman's yellow.
     - The café wides swap outfit colours between the two.
   - **Cause:** the classic multi-subject bleed. One text prompt describes both people;
     the IP masks steer the faces, but the colours and gender words leak across.
   - **Fix candidate: a regional refine pass.** After the duo render, inpaint each
     person's half again (strength ≈ 0.6). Each pass uses **only that person's own
     prompt and own single face** at their own pose, so attributes cannot cross over.
     It reuses the proven inpaint + IP + hand-repair machinery.
4. **Speed:** the duo renders take 38–49 s (VRAM spill at 13.2 GB reserved).
   Production should trim this, e.g. with VAE tiling.

## Owner verdicts (to be filled from the owner's answers)

- Conversation shots natural, two distinct people keeping identity?:
- Close-up framing right?:
- Male neat, slim-fit, short hair?:
- Outfits solid, 1 top + 1 bottom, no colour confusion?:
