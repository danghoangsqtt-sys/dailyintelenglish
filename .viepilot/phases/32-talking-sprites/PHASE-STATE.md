# PHASE-STATE — Phase 32: Talking characters as sprites, visual-novel style (ENH-023)

- **Status:** in progress 2026-10-08: both sprite packs complete (Alex and Lina, 22 pictures each, check 0 failed). **Plan:** `docs/implementation/phase-32-talking-sprites.md`; implementation decisions D32-a to D32-i in `tasks/task-32.1-32.4.md`.

| Task | Description | Status |
|---|---|---|
| 32.1 | Sprite library: model, inbox import by file name, alignment, Sprites page | done 2026-10-08 (`sprite_service.py`, Shot Library card; real import: Alex 20, Lina 22, Alex's gesture-open and gesture-point refused: cut by the canvas edge) |
| 32.2 | Speech to mouth states and the expression plan per line | done 2026-10-08 (`sprite_plan.py`) |
| 32.3 | Remotion composition (layers, turns, enter and leave, blink, mouth) | done 2026-10-08 (`spriteTimeline.ts`, `Sprites.tsx`; owner: pose changes are a paper-doll flip, the listener is not resized) |
| 32.4 | API and Step 5 mode `podcast_sprites` | done 2026-10-08 (mode `podcast_sprites`, Step 5 chip) |
| 32.5 | Real render with the owner's first sprite set | done 2026-10-08: Demo Episode preview `data/video/b330d37f-.../video_sprites_preview.mp4` (Enhanced, 129 s render). Alex's Codex `__open` pictures had closed mouths: replaced by 7 head-crop edits from ChatGPT web composed on his calm body (old ones kept in `data/assets_sprites/old/alex_open_codex_closed_mouth`) |
| 32.6a | Activity Library backend: migration, inbox import, metadata, review and usage history | in progress 2026-10-08 |
| 32.6b | Activity Library UI inside Shot Library | done 2026-10-09 (one-click multi-image upload; Alex/Lina/Generic picture selectors use character head references; local Qwen3-VL 4B Q4 metadata analysis with review gate, cloud opt-in only; real `go straight` smoke 0.98; full suite 1,633 passed) |
| 32.6c | Deterministic activity matching and Step 5 coverage | in progress 2026-10-08 |
| 32.6d | Full-screen activity cutaways in the Remotion sprite composition | planned |
| 32.6e | Storyboard insert guidance and the 20-image generic prompt pack | planned |
| 32.6f | Automated verification and Demo Episode render with three cutaways | planned |
| 32.7 | Gate B-22: owner comparison of illustrated talking sprites and talking-sprites baseline | planned |

## Owner review of the preview (2026-10-08)

"Too many pictures with a shifted or distorted body; with a flip to change gestures there is no need to skew the body." Changed: no
squash flip (a pose is swapped on one frame), nothing pasted on a gesture picture (shown exactly as made; the speaker holds it for
the first 1.6 s of the line, then talks on the plain body), and the import refuses a gesture whose torso edges moved more than 20 px.
Moved out of the inbox to `data/assets_sprites/old/refused_body_moved_20261008/`: all 7 of Alex's gestures (body moved 55 to 144 px,
two hands cut by the canvas edge) and Lina's gesture-open (35 px). Sets now: Alex 15 pictures (no gestures), Lina 21.

## Both packs remade by region edits (2026-10-08)

Owner: the face of Alex jumped on every mouth flap and Lina's face slid when her head was raised. Cause: the open-mouth pictures
came from other image runs (other head angle, other eyes). Fix: the owner remade both packs on ChatGPT web, every picture a region
edit of one base picture (`docs/operations/Prompt_ChatGPT_Web_Alex.txt`, `..._Lina.txt`): faces, blink, open mouths, 7 gestures
and their open-mouth twins `gesture-X__open`. The video shows whole pictures only (no pasted faces, no squash); the mouth flaps
between a picture and its twin. `sprite_web_import.py` resizes same-shape pictures (Alex) and registers rescaled or cropped ones by
phase correlation (Lina), an open twin on its own closed picture (twins within 1 px). Gestures are checked by the share of the body
that kept its colour (at least 60%). Old pictures of both characters deleted at the owner's request. Sets: Alex 29, Lina 29.
