# Phase 20 — Task 20.2f spike report: character-first, Vietnamese students, r3 look, one-pass scenes

- **Run:** owner machine (RTX 3060 12 GB), runbook r6, 2026-09-30.
- **Pinned code:** `a11b755`.
- **Evidence:** branch `owner-runs/20260930-r6` @ `9ded477`.
- **Design:** `.viepilot/phases/20-ai-visuals/tasks/task-20.2f.md`.
- **Status:** **awaiting the owner's verdict.** The observations below are the Coder's
  reading.

## 1. Run facts

| Phase | Wall (s) | Load (s) | Per image (s) | Peak allocated / reserved (MB) | Prompt tokens (max) | Truncated |
|---|---|---|---|---|---|---|
| p1: 8 candidates | 196 | 12.2 | 21.9–22.3 | 9170 / 11610 | 66 | 0 |
| p2 (IP): 16 sheet images + 8 one-pass scenes | 731 | 5.1 | 26.9–30.8 | 11185 / 13746 | 67 | 0 |
| p3: 8 frames | — | — | — | — | — | — |

- **Finding F3 is fixed:** 0 truncated prompts (max 67 of 77).
- **No downloads; no errors.** The VRAM baseline returned after each worker.

## 2. Observations (Coder's reading; the owner decides)

1. **Look.**
   - Both variants give a soft watercolor anime illustration in the r3 family.
   - `r3_bright` is cleaner and more saturated; `r3_watercolor` is softer and warmer.
2. **The characters read as young Vietnamese students** and are clearly drawn:
   - female: long straight black hair, yellow sweater;
   - male: short black hair, teal hoodie.
3. **Presence in the scenes is good.**
   - The character is the subject in every one-pass scene: natural scale and light, no
     seam, no halo, no sinking (verdicts 2 and 4 of 20.2e).
4. **Weak points.**
   - **Actions only partly followed:**
     - the library "waving" shows no wave;
     - the classroom "pointing at a whiteboard" became writing;
     - the café actions are roughly right.
   - **Placement ignored:** "on the left side" is not honoured. In the classroom frame
     (watercolor), the vocab card covers the male student's hair.
   - **Outfit extras drift:** a backpack, an orange jacket and a cap appear on some
     images.
   - **"plain light background" is ignored.** The style preset itself asks for "soft
     watercolor background".
   - **The IP reference's pose leaks:** a hand to the cheek recurs in the female sheet.
   - One café scene adds two background people who resemble the male student.

## 3. Coder recommendation (pending the owner's verdict)

The look and presence problems look solved. The remaining issues are control issues,
which the already-proven pieces address:
- **One-pass + ControlNet OpenPose** (text2img ControlNet, encode→render split as in
  20.2b P3) for the **action and the left-side placement**. The pose skeleton fixes where
  and how the character stands, while the scene is still painted in the same pass, so it
  cannot sink.
- **Outfit lock:** "no backpack, no hat, no jacket" in the negative prompt.
- **A reference** generated without the hand-to-face pose.

## Owner verdicts (to be filled from the owner's answers)

- r3_watercolor or r3_bright?:
- Each student clearly drawn / Vietnamese? Candidate 1 or 2 per character?:
- Same person across sheet and scenes?:
- Scale and presence natural (not sinking)?:
