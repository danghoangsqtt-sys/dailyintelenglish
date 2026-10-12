# PHASE-STATE — Phase 35: Remove old names and old features that overlap the current system (ENH-029, ENH-030, ENH-031)

- **Status:** in progress 2026-10-13 (planned the same day) (owner D89 after a detailed PM analysis of old names and overlapping features).
- **Approved groups:** A (conflicting flows), B + C (old name, obsolete code/docs), Standard ffmpeg renderer removed entirely.
  **Kept by the owner:** D (old data and test projects) and E (local GPU image generation).
- Runs while Phase 33 waits for owner Gate B-23.

| Task | Description | Request | Status |
|---|---|---|---|
| 35.1 | Old name in AI prompts and user-facing text | ENH-030 | done 2026-10-13 |
| 35.2 | Remove obsolete scripts, their tests, old prompt/hand-off docs, `models/activity-vision` | ENH-030 | done 2026-10-13 |
| 35.3 | Remove the "Generate locally" tab and the sprite inbox import; guard legacy routes | ENH-029 | planned |
| 35.4 | Step 5: remove the avatar section; cast through the shared selector | ENH-029 | planned |
| 35.5 | Remove the Standard ffmpeg renderer, its templates and the silent fallback | ENH-031 | planned |
| 35.6 | Full suite, docs (README/ARCHITECTURE), close requests | all | planned |

## Implementation notes (before coding)

- 35.1: the four prompts say "the English-learning YouTube channel Daily Beyond English" instead of "Daily Intel English
  Studio, an app that …"; `LICENSE`, `.gitignore`, `scripts/check_dependencies.py` text follow. Kept on purpose: the packaged
  data folder and exe name (`DailyIntelEnglishStudio`), migrations, CHANGELOG/history docs, recorded test fixtures.
- 35.2: delete the scripts/docs listed in ENH-030 and their tests; `grep` proves nothing imports them; `models/activity-vision`.
- 35.3: /characters loses the "Generate locally" tab (HTML, `characters.js` character part); Shot Library loses the sprite
  inbox import (UI, `/api/visuals/library/sprites/import`, `sprite_service.import_inbox`); legacy routes refuse to edit a
  profile's appearance or delete a seed. GPU library code used by story pictures/scene plates stays (group E kept).
- 35.4: Step 5 avatar section, its API calls and avatar routes removed; the cast uses `CharacterSelector`.
- 35.5: Standard renderer removed (`_render_video_sync`, `_render_vertical_sync`, templates, toggle, fallback); a Remotion
  failure fails the job with its reason.
