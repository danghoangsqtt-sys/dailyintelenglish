# Phase 29, Task 29.3: library vocabulary spike (ENH-020)

Question: can expression variants of a library shot be made by repainting only the faces (about 35 s) instead of drawing the
whole shot again?

## What was tried (`scripts/spike_expression_repaint.py`)

One approved-quality Cafe duo close shot; for each face (left to right) an elliptical feathered mask, the inpaint session, the
character's face reference and the expression words; the result is composited back, so body, outfit and scene stay as they are.

| Run | References | Strength | Seconds per variant (both faces) | Sheet |
|---|---|---|---|---|
| 1 (my mistake: the faces were assigned to the wrong people) | front | 0.55 | 28 | `phase29-expression-spike-swapped.png` |
| 2 | front | 0.55 | 28 | `phase29-expression-spike-front.png` |
| 3 | turned toward the partner (mirrored on the right) | 0.68 | 34 | `phase29-expression-spike-turned.png` |

## Result

- **Body, outfit and scene are untouched** (the repaint is local), and identity holds: Lan and Minh stay themselves. The faces come
  out clean.
- **Front references lose the gaze:** Minh turns to the camera in every variant. The **turned references keep the gaze toward the
  other person**, so the gaze fix of Task 29.1 survives the repaint.
- **Expression range is narrow:** `laugh` gives a clear smile for both; `surprised`, `worried` and `serious` change little (Lan
  keeps smiling). So the repaint is good for **calm / smile / laugh** and not for strong negative moods.
- **Speed:** 34 s per variant against about 1.5 min per picture in the batch (6 min for a set of four): roughly 3 times faster, not
  the 10 times hoped for.

## Decision (recommendation to the owner)

- **Vocabulary for the library:** scene x framing (single, duo close, duo wide) x action (empty, plus a few per scene when the
  stories need them) x expression. The matcher already treats calm and smile as the same, so the main saving is already there.
- **Do not build the repaint variant job yet.** It would save about a minute per extra expression, only for smile / laugh, and it needs
  its own review pass. The batch builder with one framing set per scene (27 pictures in 55 minutes) covers the common talking
  beats; strong moods and special actions are drawn when a storyboard asks for them and added to the library afterwards ("Add to
  library"), so the library grows from real use.
- Camera angles (over the shoulder, side view) and a gesture list stay out until the owner's review of the first 27 pictures and
  Gate B-21 show what the episodes really miss.

The four open questions (GPU hours, scenes first, gesture list, repetition) are still the owner's: the plan keeps the proposal
(8 scenes, one framing set each) until they are answered.
