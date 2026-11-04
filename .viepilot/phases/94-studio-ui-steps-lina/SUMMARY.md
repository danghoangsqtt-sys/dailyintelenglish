# Phase 94 summary — the seven steps and Lina (2026-11-04)

Owner: "làm đi" after Phase 93. Built in the sandbox; not built, installed or pushed.

## What changed

- **Step frame (94.1, D143):** the step list in the left pane is grouped in three stages — Content (1–3), Production
  (4–5), Publishing (6–7); the current step's dot is the brand yellow. The sticky next-step bar every step already had
  (Phase 56) gains a Back link to the previous step; on Step 7 it goes back to Today. The rail starts collapsed on every
  step, so the steps have the room.
- **Steps 1–7 (94.2/94.3):** they take direction E through the shared tokens (panels, buttons, pills, type, focus) and
  larger stage titles; their layouts, IDs and flows are unchanged (the beat editor, storyboard, Shorts, thumbnails and
  YouTube package work as before).
- **Lina (94.4, D144/D145):** on the step pages Lina speaks the next-step bar — her face beside its line, which comes from
  the project's own progress (what is missing, what is done, an earlier step not done). There is no second note, so
  nothing is said twice. On Home she is the band (Phase 93).

## Not done from the plan (honest list)

- The step pages were not rebuilt into the drawn layouts of `e/step-1.html` … `step-7.html`; they keep their own layouts
  in the new look. Rebuilding them is a larger change best done one step at a time with the owner.
- D146 reading aloud: the voice preview route only has English Edge voices, and VieNeu runs in its own worker for
  projects, so a speaker button for Lina needs a small VieNeu preview route first.
- The three-quarter view of Lina's frames (`?view=side`) and a separate `/api/assistant/line` endpoint: not needed for
  the bar; left for when Lina gets more places to speak.

## Verification

- `tests/test_step_guide_browser.py` extended (Back link, the three stages, Step 7 back to Today); sidebar, studio pages
  and brand tests pass; full pytest 2355 passed, then 8 step-nav tests pointed at the progress label (the stage labels are
  spans too) and pass.
- Sandbox: Steps 2, 4, 5, 7 of a real project in Vietnamese at 1440 px.
