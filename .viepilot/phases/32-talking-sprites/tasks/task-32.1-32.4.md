# Tasks 32.1 to 32.4: talking sprites (import, mouth and expression plan, composition, API and Step 5)

## Owner request (2026-10-08)

"Run the tests, no need to rebuild the exe; build the sprite import and the video for the talking sprites mode (Phase 32), because Alex
and Lina have their full sets of pictures." Both packs are complete (22 pictures each, `check_sprites.py`: 0 failed for both) in
`data/library/sprites_inbox`. Self-implemented (PM session), plan committed before the code.

## Decisions (changes to the phase plan of 2026-10-07, now that the real packs exist)

- **D32-a, storage without a new table:** an imported sprite set is a folder per character,
  `data/library/sprites/<character_id>/<name>.png` (`calm__closed.png`, `smile__open.png`, `blink.png`, `gesture-wave.png`, ...) plus a
  `sprite_set.json` (the canvas, the face ellipse, the import date, the check result). The folder is the source of truth: no migration,
  and deleting a character deletes its folder. The phase plan's `character_sprites` table is not needed.
- **D32-b, import by file name:** the inbox file `<character name lower>__<name>.png` belongs to the library character of that name
  (`alex__smile__open.png` -> Alex). The import refuses a set without `calm__closed`, a picture of the wrong size (1280 x 1536) or without
  transparency, and an expression or gesture that fails the alignment check (the rules of `scripts/check_sprites.py`, moved into an app
  module the script now calls). Refused pictures are reported with the reason; the accepted ones are copied (the inbox keeps its files).
- **D32-c, the face ellipse:** measured once at import with the app's face detector on `calm__closed` (the same ellipse as
  `sprite_face_tools.face_ellipse`). The composition uses it to put the face of the current expression and mouth onto a gesture picture
  (CSS mask, feathered), so any gesture can wear any face.
- **D32-d, mouth from loudness:** the episode voice mix is decoded once (ffmpeg, mono 16 kHz) and its loudness measured per video frame
  (RMS in a 1/30 s window). Inside a line, a frame is "open" when its loudness is above 35% of that line's 90th percentile; open runs
  shorter than 2 frames are dropped and gaps shorter than 2 frames are closed (no flicker). The result is a list of open intervals in
  seconds per line. Without the audio file (a test), the word timestamps are used (open during each word, closed in 60 ms at its end).
- **D32-e, expression per line:** the beat's expression when the storyboard is approved and the beat says something else than calm;
  otherwise rules on the text: "oh no / sorry / worried / afraid / problem" -> worried, "!" with "haha / funny / great / wow / amazing"
  -> laugh or surprised, "?" -> thinking, "!" -> smile, else calm. The listener smiles when the speaker laughs or smiles, else calm.
- **D32-f, gestures:** per line, by rules on the text: greetings and goodbyes -> wave, "thank" -> heart, "look / over there / this one"
  -> point, "maybe / I don't know / who knows" -> open, a thinking line -> think, a line of 4 s or more (every second such line of a
  speaker) -> talk; the listener of a line of 6 s or more -> listen. A gesture needs its picture; without it the base body is used.
- **D32-g, framing:** the 1280 x 1536 sprite is drawn 1.2 x the video height tall, the first speaker of the cast (speaker index 0) at
  27% of the width, the second at 73%, both on the bottom edge (legs below the knees off screen, as in a visual novel). The speaker is
  full colour; the listener is dimmed (brightness 0.78) and 3% smaller. Turn start: a 10 px hop over 8 frames. Both slide in from their
  sides over 12 frames at the start of the speech and slide out over the last 12 frames. Breathing: a 2.5 px bob with a 4 s period
  (phase per character). Blink: 4 frames every 3 to 5 s (a fixed pseudo-random pattern per character), never while the mouth is open.
- **D32-h, backgrounds:** the scene plate of each line's beat when the storyboard is approved (an insert beat keeps the previous place);
  otherwise one plate for the whole video (the still-scene choice of Step 5, same rule as `podcast_still`). Cross-fade 12 frames when the
  place changes; the slow still zoom stays.
- **D32-i, refusal:** `podcast_sprites` needs both speakers' cast characters to have an imported sprite set; otherwise a 422 that names
  the character and says to import its sprites (Shot Library page). Enhanced (Remotion) only, like the other podcast modes.

## Plan

- 32.1 `app/services/visuals/sprite_service.py` (new): `check_set` (the alignment rules, pure numpy), `parse_name`, `import_inbox`,
  `list_sets`, `sprite_dir`, face ellipse; `scripts/check_sprites.py` calls `check_set`; `app/api/visuals.py`: `GET /api/library/sprites`,
  `POST /api/library/sprites/import`; `library_service.delete_character` deletes the folder; Shot Library page: a "Talking sprites" card
  (per character: pictures, gestures, check result; an Import button).
- 32.2 `app/services/visuals/sprite_plan.py` (new, pure): `loudness_per_frame` (ffmpeg decode + numpy), `mouth_intervals`,
  `mouth_from_words`, `line_expression`, `listener_expression`, `line_gesture`, `build_plan`.
- 32.3 `video-renderer/src/spriteTimeline.ts` (pure: picture choice per frame, positions, hop, blink, enter and leave, background
  cross-fade) + `spriteTimeline.test.ts`; `video-renderer/src/Sprites.tsx` (draws it); `types.ts` (`visualMode` gains
  `podcast_sprites`, `sprites` props); `podcastLayout.ts` (`VISUAL_MODES`, layer "sprites"); `Episode.tsx` mounts the stage.
- 32.4 `app/models/video.py` (`podcast_sprites`); `app/services/video_renderer_remotion.py` (`_build_sprite_props`: copies the pictures
  and the plates into `public/remotion-render/sprites/<project>/`, the plan); `frontend/pages/step5_video.html` +
  `frontend/static/js/step5_video.js` (the chip "Podcast: talking characters", the scene row shown for it too).

## Paths

- `app/services/visuals/sprite_service.py`, `app/services/visuals/sprite_plan.py`, `app/api/visuals.py`,
  `app/services/visuals/library_service.py`, `app/models/video.py`, `app/services/video_renderer_remotion.py`
- `scripts/check_sprites.py`
- `frontend/pages/shot_library.html`, `frontend/static/js/shot_library.js`, `frontend/static/js/api.js`,
  `frontend/pages/step5_video.html`, `frontend/static/js/step5_video.js`
- `video-renderer/src/spriteTimeline.ts`, `video-renderer/src/spriteTimeline.test.ts`, `video-renderer/src/Sprites.tsx`,
  `video-renderer/src/types.ts`, `video-renderer/src/podcastLayout.ts`, `video-renderer/src/Episode.tsx`
- `tests/test_sprite_service.py`, `tests/test_sprite_plan.py`, `tests/test_sprite_video_props.py`, browser test for the chip and the card

## Verification

pytest for the new modules and the touched ones; `npx vitest run` and `npx tsc --noEmit` in `video-renderer/`; a browser test for the
Step 5 chip and the library card; then 32.5: the real import of the two packs (backup of `data/app.db` first, though no table is
written) and a real Enhanced render of an Alex and Lina episode in `podcast_sprites`, looked at frame by frame before the owner sees it.
