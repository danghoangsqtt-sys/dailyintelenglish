# Gate B-20: one full real episode in the new style (2026-10-07)

**Video:** `data/tmp/gate-b20/daily_beyond_english_episode.mp4` (outside git, 72 MB). **Sheets:**
`docs/operations/phase28-gate-b20-shots.png` (the 12 shots), `docs/operations/phase28-gate-b20-frames.png` (10 frames of the
video). Run on a throw-away copy of the data (the real library, project and music), through the app's own API.

## What was made

- The "Demo Episode" (B1, "The best way to start your morning"): 176 s of speech, 12 shots (2 singles, 1 close duo, 6 wide
  duos, 3 inserts) of **Lan and Minh** in the 55-plate cafe, the new brand intro (7.6 s) and outro (8.5 s) with Jenny's
  new greeting, the auto-selected Pixabay music ("corporate background"), subtitles and vocabulary cards.
- Rendered by Remotion (Enhanced), no fallback: **192.26 s**, 1280 x 720, 30 fps, h264 + aac, **-16.5 LUFS**, peak -2.6 dB.

## Times

| Step | Time |
|---|---|
| All 12 shots, first pass (photographic, 2 hand repairs per person, duo refine, colour and face checks) | 19 min |
| Regenerating the 7 shots the user would press "Regenerate" on (4 + 2 + 1) | about 14 min |
| The video (Remotion + soundtrack with the brand voices) | 1 min 37 s |

## What the checks did on the real run

- 4 of the 9 duo and single shots with people came out flagged "may not be black" and three really were wrong (Minh in a
  white shirt in 2 of them, a dark-navy shirt in the third). After regenerating those, shot 10 was still flagged: it is a
  **false alarm** (the black shirt is lit, value just over the 0.16 line).
- The extra-person check (faces) found no third person in this run; the earlier three-person shot is a test fixture.
- The note and the primary Regenerate button worked as designed.

## What the owner should look at (honest list)

1. **Speaker names:** the project's speakers are "Alex" and "Maya" (the labels in the video), while the characters are Minh
   and Lan. Rename the speakers in Step 1 if the owner wants the labels to match.
2. **Shot 10** (a duo): an acceptable picture, flagged by a false alarm.
3. **Outfit swaps in duos remain the weak spot:** Minh in a white shirt appeared in about a third of the first-pass duos.
   The colour check finds most, not all (a white shirt open over a black tee passes). A stronger fix (per-person outfit
   inpainting before the refine, or the Phase 29 library of checked shots) is the real answer.
4. **Inserts** that name a person (a person stretching, shot 7) draw a stranger: by design (no characters), but the
   storyboard could avoid people in inserts.
