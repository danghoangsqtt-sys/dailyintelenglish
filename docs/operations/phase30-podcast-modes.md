# Phase 30, Task 30.4: real renders of the podcast picture options (ENH-021)

Date: 2026-10-07. Project: the Gate B-20 demo episode (data copy `data/tmp/smoke28-4b`), 192.26 s of audio, Enhanced (Remotion) renderer, caption style "outline", 16:9.

## The three options in Step 5 "Video pictures"

| Option | `visual_mode` | What is on screen | Render time |
|---|---|---|---|
| Podcast: with characters | none (default, `illustrated`) | the previous feature, unchanged: Lan and Minh in their scenes, shots changing with the story, inserts, speaker chips, vocabulary card | 1 min 37 s after the shots exist |
| Podcast: black screen | `podcast_black` | black, captions, speaker chips, vocabulary card | 84 s |
| Podcast: one still scene | `podcast_still` | one scene plate with a very slow zoom (at most 5%), captions, speaker chips | 119 s |

Black and still need no drawn shots at all (the story pictures need about 19 min of image generation first).
Frames: `docs/operations/phase30-podcast-modes.png` (black screen and one still) and `docs/operations/phase30-podcast-modes-characters.png` (with characters, a fresh render with the new code, seconds 12 to 150).

## What went wrong, and the correction

The owner asked for "3 extra options": a black screen, with the characters, one still scene. The first reading made "with characters" a **fourth**, new mode beside the old one: first two portrait cards on black, then one held duo shot. Both were rejected by the owner: the characters must be in their scene like the earlier test videos, with scene changes and illustrations, and the old feature must not be lost. The "extra" options were only the black screen and the still. The cards and the held-shot mode were removed (model, props builder, composition, tests); "with characters" is now the old drawn-story mode, relabelled, still the default, and its request body is unchanged.

Regression check: the default mode was rendered again with the new code (complete, no fallback); the frames show scene changes, the phone insert and the close-ups.

Also fixed in this task: the inactive speaker chip on the bright still (soft dark gradient at the top of the still).
