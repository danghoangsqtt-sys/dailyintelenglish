# Task 46.4: Verify the owner's episode title and folder report

Owner follow-up 2026-10-15: the supplied Ep. 2 intro wraps between Ep. and 2; episode exports overlap in the topic folder. Continue the authorized repair with concrete output verification.

## Plan and allowed_files
- This task card and docs/operations/episode-output-verification.md.
- scripts/start_studio.ps1: run the current source against the workspace data on a separate localhost port; never silently redirect to the old executable.
- frontend/static/js/project_folder.js: clarify that a series folder is selected and episode subfolders are automatic.
- Disposable evidence under data/tmp/episode-output-verification/.
- Additive exports under the already configured D:/Example-videos/Local Market/Ep 02 - Shopping at the Market/; retain existing root files.
- Normal source-app startup and video generation for the reported Ep. 2: first snapshot the workspace SQLite DB and existing MP4/SRT files under data/backups, then run on port 8001 and use the existing video APIs. This applies the authorized video repair to the actual project and records exports through the usual transaction path.

## Evidence and risk
BUG-036 and ENH-035 implementations already exist at HEAD. The running October 7 exe serves a separate AppData database with one old draft; the source database contains the three real Dinner Party episodes. Do not claim the exe generated the reported video. No exe build/release or existing application shutdown. Startup and normal video API writes are covered by the owner's repair request; preserve rollback snapshots first. Source launcher checks dependencies/port and backs up the DB before startup. Source media is replaced only by successful render staging; the previous versions remain in the snapshot.

## Verification
Run existing title/export tests; render actual wide and vertical intro stills and inspect; resolve actual series episode paths using a read-only database; copy the configured Ep. 2 export plan additively; verify file hashes. Syntax-check the launcher and modified JS. Formal acceptance remains pending owner review.

## Result: implemented_verified_pending_pm

- Reproduced the supplied defect from the old production MP4 at 4.5 seconds.
- Normal source APIs regenerated both real Ep. 2 outputs: 1280x720 and 1080x1920, H.264/AAC, each 249.514667 seconds. Cached narration/music/brand voice retained. New output frames visually inspected; `Ep. 2` stays together in both layouts.
- The normal export hook created and populated the episode folder; both exported video hashes match the new production sources. Root video/vertical/SRT hashes match the original snapshots.
- Tests: 11 export + 7 brand passed. Actual Step 7 browser destination and both sibling root suggestions verified. JS/PowerShell syntax and git diff --check passed. Launcher SQLite backup integrity and occupied-port guard verified.
- Source server remains available at http://127.0.0.1:8001 with workspace data. Existing EXE and its separate AppData database were preserved. Rollback snapshot: data/backups/episode-output-20261015/.
- Report: docs/operations/episode-output-verification.md. No commit, release, or owner gate acceptance declared.
