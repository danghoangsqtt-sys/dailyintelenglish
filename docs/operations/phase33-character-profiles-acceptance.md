# Phase 33 Character Profiles v2 — Gate B-23 acceptance

Date: 2026-10-10
Status: automated evidence ready; owner acceptance pending

## Safety boundary

- The live database and live asset folders were read only.
- Migration and acceptance ran in `data/backups/phase33-acceptance-20261010/copied-data-final`, which contains the required `.phase33-acceptance-copy` marker.
- The acceptance runner refuses an unmarked data directory or one without `app.db`.
- Phase 32 Gate B-22 remains pending and is independent of this gate.

## Migration rehearsal

Command:

```powershell
$env:DIE_DATA_DIR = 'D:\DataAdmin\Daily_Intel_English\data'
D:\DataAdmin\Daily_Intel_English\venv\Scripts\python.exe scripts/migrate_character_profiles_v2.py `
  --db data/backups/phase33-acceptance-20261010/app-copy-final.db `
  --data-dir data/backups/phase33-acceptance-20261010/copied-data-final `
  --copy-from-live
```

Result:

| Check | Before | After | Result |
|---|---:|---:|---|
| Characters | 2 | 2 | Preserved |
| Character assets | 14 | 72 | 58 legacy sprites registered |
| Project cast rows | 2 | 2 | Preserved byte for byte at row level |
| Projects | 9 | 9 | Preserved |
| Speakers | 16 | 16 | Names and voice settings preserved |
| Character and sprite files | Full SHA-256 snapshot | Same snapshot | Preserved |
| SQLite foreign keys | — | 0 errors | Pass |

The applied migration was `018_character_profiles_v2.sql`. The complete report, including every SHA-256 value, is in `data/backups/phase33-acceptance-20261010/migration-report-final.json`.

## Owner workflow rehearsal

The real app was started against the isolated copy and driven through Chromium with `scripts/run_phase33_acceptance.py`.

1. Created Rowan from the ten-step Character Library wizard.
2. Closed the first browser context and resumed Rowan from a new context.
3. Uploaded five core pictures and seven Talking Starter sprites through the UI.
4. Approved all twelve assets through the UI and locked the profile.
5. Created a three-speaker project and assigned Alex, Lina and Rowan with the game-style selector.
6. Preserved the project-specific `Custom Alex` name and `1.1` speed because copy-on-assign was off.
7. Copied Lina and Rowan profile voice defaults because copy-on-assign was on.
8. Approved storyboard pairs `[Alex, Lina]`, `[Rowan]`, and `[Alex, Rowan]`.
9. Matched the insert action `cooking` to approved Generic activity `0dfa3a8c-b112-42f8-9ee8-cc1648e6680c` with score 80.
10. Rendered still, talking-character and old Alex/Lina videos with Remotion and no fallback.

Rowan finished with Profile, Voice, Core visual (5/5), and Talking Starter (7/7) readiness. The optional 15-expression and 29-sprite tiers correctly remain partial.

## Defect found during acceptance

The first talking render loaded only sprite slots 0 and 1. A final beat whose storyboard pair was `[Alex, Rowan]` therefore displayed Alex and Lina even though Rowan was the active speaker.

The fix now:

- packages sprite sets for every assigned cast member, up to the six-speaker project limit;
- records up to two `visibleSlots` per line from the approved storyboard beat;
- keeps the active speaker visible if a malformed pair omits that speaker;
- positions a one-person beat in the center and a two-person beat on the left and right;
- hides cast members outside the current pair;
- accepts slots 0–5 at the Remotion schema boundary.

Regression tests cover the three-character props, `[0, 2]` pair selection, hidden Lina, visible speaking Rowan, schema parsing and canvas placement. Visual inspection of `frame-talking-31.png` confirms Alex on the left and Rowan on the right.

## Owner-review remediation

The first owner review found two additional composition defects in the Talking Starter video:

1. An activity illustration was drawn after the sprites and covered the active speaker.
2. Storyboard pairs could be stored in either order, allowing the same two characters to exchange left/right positions between beats even though their source pictures have fixed gaze directions.

The renderer now draws the activity illustration above the scene plate but below all sprites. It also sorts every visible pair by cast slot before assigning stage positions. The active speaker therefore remains visible during a cutaway, and Alex stays left of Lina when their speaking turn changes. Focused layer-order and reversed-pair regression tests pass.

The replacement talking video rendered through the real Remotion API in 32.27 seconds with no fallback. Visual inspection confirms:

- `frame-fixed-18.png`: Rowan remains visible and speaking over the cooking illustration.
- `frame-pair-10.png` and `frame-pair-14.png`: Alex remains left and Lina remains right before and after the active speaker changes.
- `frame-fixed-31.png`: Alex and Rowan retain the intended pair after the cutaway.

## Render evidence

Evidence directory: `data/backups/phase33-acceptance-20261010/evidence-final`

| Artifact | Duration | Media | Size | Result |
|---|---:|---|---:|---|
| `phase33-three-cast-still.mp4` | 42.411 s | 1280×720, H.264/AAC, 30 fps | 13,460,532 bytes | Remotion, no fallback |
| `phase33-three-cast-talking-fixed.mp4` | 42.411 s | 1280×720, H.264/AAC, 30 fps | 14,119,270 bytes | Replacement Remotion render, no fallback |
| `phase33-old-alex-lina.mp4` | 192.256 s | 1280×720, H.264/AAC, 30 fps | 28,129,470 bytes | Remotion, no fallback |

Supporting files:

- `01-rowan-core-approved.png`
- `02-rowan-talking-starter-approved.png`
- `03-rowan-locked-profile.png`
- `04-three-character-selector.png`
- `frame-talking-18.png` — approved Generic cooking cutaway
- `frame-talking-31.png` — corrected Alex and Rowan pair
- `frame-fixed-18.png` — active Rowan remains above the cooking illustration
- `frame-pair-10.png` and `frame-pair-14.png` — Alex/Lina keep stable sides across a speaker change
- `frame-fixed-31.png` — corrected Alex/Rowan pair in the replacement render
- `acceptance-result.json` — IDs, readiness, cast, speakers, beats, activity coverage and render jobs
- `server.log` — no error, traceback or fallback message

## Verification

Environment:

- Python 3.14.7
- Node.js 24.20.0
- npm 11.19.0
- Remotion 4.0.529
- FFmpeg 9.0.1
- Chromium 151.0.7922.34

| Verification | Result |
|---|---|
| Migration unit tests | 4 passed |
| Sprite plan, props and tier regression | 34 passed |
| Phase 33 and affected browser regression group | 97 passed |
| Vitest | 67 passed across 10 files after owner-review remediation |
| TypeScript `tsc --noEmit` | Pass |
| Ruff on every changed Python file | Pass |
| Real isolated workflow | Pass in 161.43 s |
| Full Python/browser suite | 1,674 passed, 7 skipped, 0 failed in 1,143.77 s |

Repository-wide Ruff still reports two pre-existing unused imports in `scripts/run_gate_b12.py` and `tests/test_shot_faces.py`. Neither file is part of Phase 33, and both remain untouched.

## Gate B-23 owner review

Please review the four UI screenshots and three MP4 files in the evidence directory. Phase 33 remains open until the owner explicitly accepts Gate B-23. Acceptance must not imply acceptance of Phase 32 Gate B-22.
