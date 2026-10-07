# Owner runbook, 2026-10-07 (Phases 27 to 31)

What is new and what only you can decide.

## Start the app

- From the source folder: `venv\Scripts\python -m uvicorn app.main:app --port 8000`, or run the rebuilt package
  `dist\DailyIntelEnglishStudio\DailyIntelEnglishStudio.exe` (rebuilt 2026-10-07 and smoke-tested on a fresh data folder; rebuild it
  again with `powershell -File scripts\build_exe.ps1` after the later changes of Phase 31).
- The image worker needs the GPU: close any other program that uses it while pictures are being drawn.

## 1. The characters: Alex and Lina

- The characters are **Alex** (navy suit, white shirt, black bow tie) and **Lina** (white mini dress), both Russian, made from your own
  sheets (`docs/operations/phase31-characters/`). Lan and Minh, and the 27 library pictures made of them, were removed (database backups
  in `data/backups/`, old character folders in `data/tmp/characters-old-backup-31/`).
- Projects that used Lan and Minh now use Lina and Alex, but their already drawn shots still show the old characters: draw them again
  in Step 5.
- The scene plates are still the old places (some have a Vietnamese look). Say if you want them redrawn.

## 2. The Shot Library (`/shots`)

Ready-made pictures of Alex and Lina by scene, framing, action and mood. A new episode reuses **approved** pictures that match its
scene, framing, action and mood (Step 5 shows "Shot Library: X of Y pictures are ready to reuse") and draws only what is missing. A
picture of a character you changed later shows as **stale** and is never reused.

**Your own pictures:** put them in `data\library\shots_inbox`, named like `cafe__duo-wide.png`
(the full rules and the 55 scenes are in `docs/operations/scene-list-55.md`), open the page, "Add your own pictures", **Import pictures**.
They wait for your review: **Approve** the good ones, **Reject** the others, or **Approve all in view** after filtering.
Pictures should be 16:9 (a 4:3 picture is cropped and loses its bottom quarter).

To fill scenes with drawn pictures instead (the app must be running; it skips scenes that already have a full set):

```bash
venv\Scripts\python scripts\build_shot_library.py --characters Lina,Alex --scenes builtin-restaurant,builtin-airport --max-minutes 90
```

## 3. Step 5 "Video pictures"

- **Podcast: with characters**: Alex and Lina in their scenes with scene changes and inserts (the earlier test video).
- **Podcast: black screen** and **Podcast: one still scene**: need no drawn shots, ready in about two minutes.

## 4. Switches (environment variables, all optional)

| Variable | Default | Meaning |
|---|---|---|
| `DIE_VISUALS_GAZE` | `turned` | `off` brings back the old stare into the lens, `words` uses only the prompt words |
| `DIE_VISUALS_USE_LIBRARY` | `true` | `false` draws every shot even when the library has a match |
| `DIE_VISUALS_LIBRARY_AUTO_ADD` | `false` | `true` adds every shot that passed its checks to the library as "needs review" |

## 5. Gates and decisions waiting for you

- **Gate B-19** (Phase 27): look at the pages (Dashboard, Characters, Music, Shot Library, the seven steps) and one rendered episode.
- **Gate B-20** (Phase 28): the photo-look episode (`data/tmp/gate-b20/daily_beyond_english_episode.mp4`, already sent; it shows the old
  characters).
- **Gate B-21** (Phase 29): after your pictures are approved, make an episode and time it against drawing everything.
- **Library questions** (`docs/implementation/phase-29-shot-library.md`, section 4): GPU hours for more scenes, which scenes first,
  the gesture list, and whether a picture may repeat across episodes.
- **Expression variants by face repaint**: recommended not to build yet (`docs/operations/phase29-vocabulary.md`).
