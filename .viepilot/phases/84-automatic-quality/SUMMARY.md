# Phase 84 summary — Automatic videos, long and Short, at the best quality

Done 2026-10-28 on `owner-runs/20261001-r9` (not pushed).

## What changed

- **Plan boundaries repaired** (84.1): the AI's segment anchors are chained before the coverage check, so an off-by-a-word
  anchor no longer stops a visual plan.
- **Short script length** (84.2): Shorts are checked at ±20 % (`SCRIPT_SHORT_WORD_TOLERANCE`); long scripts keep ±10 %.
- **One more try** (84.3): audio, visual plan (proposed afresh), video and thumbnail run once more before an episode stops;
  a doubtful fact (`OwnerStop`) is never retried.
- **AI fact check** (84.4): `POST /api/projects/{id}/explainer-plan/fact-check`; News, VOX and long presenter plans are
  approved automatically only when every segment is ok; invented VOX chart / map data becomes a card of the narration.
- **Editor pass** (84.5): every automatic script (not flashcards / slow podcast) is scored on hook, one message,
  examples, natural English, level and ending; under 4 → one rewrite with the notes (plus one length-only retry), kept
  only when it passes every script check. It never adds facts and keeps every fact the script gives. Saved in
  `script_reviews` (migration 041), shown on Step 2 with a manual "Review the script" button.
- **1080p long videos** (84.6): Remotion `--scale=1.5`; the word card's IPA no longer shows double slashes.
- **After the automatic run** (84.7): a narrated episode needs no idiom and a Short 2-5 questions; repaired cards show
  the narrator's words, never the AI's planning note; the packaged app sets the Windows error mode and starts child
  programs with `CREATE_NO_WINDOW`, so an ffmpeg start failure (0xC0000142) fails at once instead of waiting behind a
  dialog (it held one Short for 55 minutes).

## Real checks

- Editor, real AI in a sandbox copy: first run invented a study in a news Short (fixed: no new facts), then dropped the
  news itself (fixed: keep every fact), then a long rewrite came back 10 % short (fixed: length retry); third run kept
  the facts and rewrote the long conversation at 619 words.
- 1080p render in the sandbox: 1920x1080, 258 s, 274 MB, 11 minutes.
- Installed app (from `9597292`), "Make videos now" for every kind into `D:\Videos\Tự động 2026-10-28`: 15 of 17 finished
  by themselves (News, Listen and Vox Shorts and the Solo presenter episode now finish); the editor rewrote all 15
  reviewed scripts; long videos 1920x1080; 2 clips cut. Stopped: slow podcast (2 questions) and VOX 16:9 (no idiom) —
  both fixed in `e3ff771`, not installed yet. The Phase 83 folders received their 5 held-back videos and 2 clips.
- Full pytest 2231 passed.

## Second install (2026-10-28)

- Built from `2f86226` into `dist/2.0-phase84b-20261028` (ZIP 138,734,224 bytes, SHA256
  `c4cdfe6030a2e51b68d2be0e71db3a16eb6698fca9a99bdcc3ad7c0cbf229552`); installed, backup
  `data/backups/desktop-20261028-161758-401`; data counts unchanged.
- The two stopped videos resumed and finished by themselves: slow podcast Short 47.8 s, VOX 16:9 156.6 s at 1920x1080
  (it passed the AI fact check after the editor's rewrite). 17 of 17 kinds now finish automatically.
- Found then: both slow podcast Shorts had no Vietnamese translations (the AI left them out); fixed after this install
  with a translation pass in the script job.
