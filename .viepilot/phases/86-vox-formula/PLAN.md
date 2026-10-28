# Phase 86 — VOX videos on the viral explainer formula (2026-10-28)

Owner (2026-10-28): research the Vox video formula and viral examples, then "Plan Phase 86 to rebuild the VOX format on
the researched formula (cold open, evidence blocks, a visual every 5-8 s, evidence cards, collage object pictures,
recap ending), then build it and make test VOX videos."

## Research (sources in the session report)

- Story: open on a concrete example and ONE question (no greeting); context only after curiosity; a recurring visual
  comes back; end by answering the question, then widen. "Visual evidence, then context" (Johnny Harris).
- Pace: one idea and one visual anchor per scene, narration lines of 20 words or fewer, a key visual held ~5-6 s with
  small motion (highlighter sweeps, arrows, zoom); stepped ~12 fps motion for the hand-made collage feel.
- Language channels that travel (RobWords): a strange question about English; the evidence is the English itself.

## What our VOX does today (test video "VOX list", 2026-10-28)

Good: paper board, highlighter quotes timed to the words, transitions, push-in camera, data only from the narration.
Weak: opens on the brand title slide ("VOX list · Ep. 1"); text cards with only a title; abstract AI pictures (a crowd of
faces with letters); 10-15 s segments with one still visual; ends on a "Thanks for watching! Subscribe" card.

## Tasks

1. **86.1 VOX script formula** — long and Short VOX scripts: line 1 is a cold open (a concrete English example and one
   question, no greeting or welcome), a one-line promise, three evidence blocks (each says an English word or sentence
   aloud, then explains it), a callback to the opening example, the answer in plain words, one memory tip, and one short
   follow line (no long goodbye). Sections of a long VOX follow it (the first section opens cold). Paths:
   `backend/ai/prompts/script/solo_explainer.txt`, `backend/ai/prompts/script/section.txt`, tests.
2. **86.2 VOX plan: evidence, pace, recap** — the plan prompt asks for one segment per one or two sentences (about 5-8 s),
   evidence first (the English example as a highlighted quote), text cards that always carry an example, the opening
   example returning in the recap, a last segment that recaps the answer (no "thanks for watching" card), and picture
   prompts for cut-out objects on paper (no crowds of faces). A VOX segment still longer than 24 spoken words is split
   at a sentence boundary into a quote of its later sentences, so the picture changes at least every ~8 s. Paths:
   `backend/ai/prompts/storyboard/explainer_vox.txt`, `backend/library/explainer_timing.py` or `explainer_service.py`
   (`densify_vox`), tests.
3. **86.3 VOX pictures** — Qwen draws a VOX photo slot as an editorial paper cut-out collage of objects (warm muted
   colours, no faces, no text), not a photograph. Paths: `backend/ai/image/recipes.py`, `backend/ai/image/pipelines.py`,
   tests.
4. **86.4 Cold open and collage motion** — a long VOX video has no intro slide (it opens on its first line; the branded
   ending stays); collage pictures move in stepped 12 fps steps with a slight paper jitter. Paths:
   `backend/media/video_renderer_remotion.py` (`_add_brand`), `renderer/src/VoxVisual.tsx`, `renderer/src/voxMotion.ts`,
   tests (pytest, vitest).
5. **86.5 Verify** — full pytest and vitest; build and install (owner's go-ahead given in the request); three automatic
   VOX 16:9 videos (why / how / list) and one VOX Short into `D:\Videos\Kiểm tra VOX 2026-10-28`, each checked: first
   line, segment lengths, evidence cards, pictures, ending, frames. Records.
