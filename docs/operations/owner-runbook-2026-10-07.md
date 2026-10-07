# Owner runbook, 2026-10-07 (Phases 27 to 30)

What is new and what only you can decide.

## Start the app

- From the source folder: `venv\Scripts\python -m uvicorn app.main:app --port 8000`, or run the rebuilt package
  `dist\DailyIntelEnglishStudio\DailyIntelEnglishStudio.exe` (rebuilt 2026-10-07 and smoke-tested on a fresh data folder).
- The image worker needs the GPU: close any other program that uses it while pictures are being drawn.

## 1. Review the library pictures (needed before they are ever reused)

1. Open **Shot Library** in the left menu (`/shots`). 27 pictures wait for review (sheets: `docs/operations/phase29-library-batch-1.png`,
   `-2.png`).
2. Press **Reject** on a wrong one: suggested rejects are the Park single of Minh (green shirt), the Park duo wide (Minh turns his
   back) and the City street single of Lan (blazer with a black top).
3. Press **Approve** on the good ones, or **Approve all in view** after filtering to the good ones (filter Review = Needs review).
4. A new episode now reuses approved pictures that match its scene, framing, action and mood (the Step 5 line "Shot Library: X of Y
   pictures are ready to reuse") and draws only what is missing. A picture of a character you changed later shows as **stale**
   and is never reused.

To grow the library: in Step 5 press **+ Add to library** under a good finished shot, or fill more scenes (the app must be running):

```bash
venv\Scripts\python scripts\build_shot_library.py --scenes builtin-restaurant,builtin-airport --max-minutes 90
```

It skips scenes that already have a full set and can be stopped and started again.

## 2. Step 5 "Video pictures"

- **Podcast: with characters**: Lan and Minh in their scenes with scene changes and inserts (the earlier test video).
- **Podcast: black screen** and **Podcast: one still scene**: need no drawn shots, ready in about two minutes.

## 3. Switches (environment variables, all optional)

| Variable | Default | Meaning |
|---|---|---|
| `DIE_VISUALS_GAZE` | `turned` | `off` brings back the old stare into the lens, `words` uses only the prompt words |
| `DIE_VISUALS_USE_LIBRARY` | `true` | `false` draws every shot even when the library has a match |
| `DIE_VISUALS_LIBRARY_AUTO_ADD` | `false` | `true` adds every shot that passed its checks to the library as "needs review" |

## 4. Gates and decisions waiting for you

- **Gate B-19** (Phase 27): look at the pages (Dashboard, Characters, Music, Shot Library, the seven steps) and one rendered episode.
- **Gate B-20** (Phase 28): the photo-look episode (`data/tmp/gate-b20/daily_beyond_english_episode.mp4`, already sent).
- **Gate B-21** (Phase 29): after approving the library, make an episode and time it against drawing everything.
- **Library questions** (`docs/implementation/phase-29-shot-library.md`, section 4): GPU hours for more scenes, which scenes first,
  the gesture list, and whether a picture may repeat across episodes.
- **Expression variants by face repaint**: recommended not to build yet (`docs/operations/phase29-vocabulary.md`).
