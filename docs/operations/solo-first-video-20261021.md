# First real Solo Explainer video — Lina (2026-10-21)

Owner request: "create a test video with one presenter". Driven through the installed app's API (same calls as the UI).

| Step | Result |
|---|---|
| Project | `5644734e-92a8-4ee0-8b32-d6dfab71bab6` "Solo test — Why do we build habits?", B1, Why structure, 1.5 min target, Lina (21/21 front approved), voice en-US-JennyNeural |
| Script | AI job complete: 4 lines, 174 words |
| Audio | 4 lines synthesized (9.2 s), mix complete |
| Proposal | first attempt failed (BUG-050) → fixed in Phase 54 → complete on first call: 4 segments (text card, photo, diagram, text card); gestures think, emphasize, talk, point-right, count-1, calm, wave |
| Demo edits (PM, not owner) | `example-1` photo had no illustration → text card "Driving becomes automatic"; diagram labels shortened after the layout engine refused 9:16 ("text cannot fit readably"); every segment marked reviewed with the note "content not yet checked by the owner" |
| Layout / approval | arrange OK for 16:9 and 9:16; approved revision 5 |
| Render | 48.3 s; `data/video/5644734e-92a8-4ee0-8b32-d6dfab71bab6/8829c93b28f34251abc09bd0855387e8/video_remotion.mp4` — H.264 1280×720 30 fps + AAC, 92.95 s, 8.2 MB, with `subtitles.srt` |

Observations for the owner:
- The presenter is small: the layout engine chose height 0.22 of the frame in 16:9 (editor allows 0.12–0.38). Raise it in Step 5 → presenter placement if a larger presenter is wanted.
- Gestures are brief and sparse (about two per segment); most of the time she stands in the neutral pose. The `think` pose (hand at the chin, previously blocked by BUG-049) renders correctly.
- Cards leave much empty space; the driving segment has no picture.
- Content review was ticked by the PM for this demo only; the owner still has to check the claims before any publication. No release, upload or V49 acceptance is implied.
