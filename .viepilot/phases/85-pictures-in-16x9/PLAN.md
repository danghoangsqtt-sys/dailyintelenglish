# Phase 85 — Pictures in 16:9 videos, and the 16:9 test set (2026-10-28)

Owner (2026-10-28): test 16:9 presenter videos (different kinds), 16:9 VOX videos (different kinds) and a conversation
made from the owner's own script (check that it follows the script and invents nothing); "video 16:9 chưa có nhiều hình
ảnh minh họa phía sau" -- maybe the content illustration feature or the image model has a problem.
Owner choices (same day): library pictures first, then the local Qwen model draws any remaining picture slot (people
doing the action, never the presenter's face); a picture drawn during an automatic run is used right away and kept in
the library marked automatic.

## Findings

- The automatic 16:9 presenter and VOX plans had no picture at all (text cards, diagrams, quotes, a chart) although the
  planner was offered 133 approved library pictures and 56 scenes; the prompt only suggests pictures. A "photo" slot
  needs a picture someone imports, so automation turns it into a text card.
- The automatic 16:9 conversation proposed a storyboard (5 scenes, 6 picture inserts) but automation never approved it;
  the render uses only an approved storyboard, so the video played on the default background with no scene change and
  no insert (activity coverage: no beats).
- Qwen-Image-2.1 and Qwen-Image-Edit are installed (53 GB in `backend/ai/models/image`); the RTX 3060 drew pictures in
  about a minute each. The image model works; nothing asked it to draw for 16:9 narrated videos.

## Tasks

1. **85.1 Approve the conversation storyboard** — the Producer approves the beats it proposed (and a draft left by an
   earlier run). Committed as `202de88` before this plan was written (found while diagnosing; recorded here).
2. **85.2 The planner uses library pictures** — the presenter and VOX plan prompts ask for a picture behind the
   presenter (or full screen in VOX) in about every second or third segment: an offered library picture when one fits
   the idea, otherwise a photo slot with a face-free picture description. Paths: `backend/ai/prompts/storyboard/explainer.txt`,
   `explainer_vox.txt`, tests.
3. **85.3 Qwen draws the remaining photo slots** — image job `explainer_illustrations` and
   `POST /api/projects/{id}/explainer-plan/illustrate`: each photo slot with no picture gets a Qwen-Image-2.1 picture
   from its description (ordinary people or objects, no faces of the cast), imported as the project's illustration and
   set on the segment, and kept in the Activity Library as an approved generic picture tagged automatic. The Producer
   runs it before approving a plan; a picture that cannot be drawn falls back to the narrator's-words card. Paths:
   `backend/ai/image/pipelines.py`, `backend/ai/image/recipes.py`, `backend/library/explainer_service.py`,
   `backend/api/explainer.py`, `backend/main.py`, `backend/automation/runner.py`, tests.
4. **85.4 Conversation inserts get a picture** — before rendering, the Producer asks Qwen to draw every storyboard insert
   with no library picture (`activity_illustrations`, D102) and approves what it drew, so the insert shows a picture
   instead of the talking characters. Paths: `backend/automation/runner.py`, `backend/library/activity_library_service.py`
   (approve), tests.
5. **85.5 The 16:9 test set** — with the installed app: presenter 16:9 in each structure (why / how / list), VOX 16:9 in
   each structure plus one from the owner's material with numbers (chart), and a conversation from a test dialogue
   written here (verbatim): compare every saved line with the dialogue (nothing added, removed or reworded), count the
   pictures and scenes per video, frames. Full pytest; records; build and install with the owner's go-ahead.
