# PHASE-STATE — Phase 32: Talking characters as sprites, visual-novel style (ENH-023)

- **Status:** in progress 2026-10-08: both sprite packs complete (Alex and Lina, 22 pictures each, check 0 failed). **Plan:** `docs/implementation/phase-32-talking-sprites.md`; implementation decisions D32-a to D32-i in `tasks/task-32.1-32.4.md`.

| Task | Description | Status |
|---|---|---|
| 32.1 | Sprite library: model, inbox import by file name, alignment, Sprites page | done 2026-10-08 (`sprite_service.py`, Shot Library card; real import: Alex 20, Lina 22, Alex's gesture-open and gesture-point refused: cut by the canvas edge) |
| 32.2 | Speech to mouth states and the expression plan per line | done 2026-10-08 (`sprite_plan.py`) |
| 32.3 | Remotion composition (layers, turns, enter and leave, blink, mouth) | done 2026-10-08 (`spriteTimeline.ts`, `Sprites.tsx`; owner: pose changes are a paper-doll flip, the listener is not resized) |
| 32.4 | API and Step 5 mode `podcast_sprites` | done 2026-10-08 (mode `podcast_sprites`, Step 5 chip) |
| 32.5 | Real render with the owner's first sprite set | in_progress (Demo Episode preview) |
| 32.6 | Gate B-22 (owner) | planned |
