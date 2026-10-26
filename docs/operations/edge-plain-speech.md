# Plain Edge speech — restoration 2026-10-24

Owner decision: the Chatterbox B video was preferable to A, but male sighs could sound like another voice/animal growling and female emotion was unclear. Restore the old Edge voices and remove emotion insertion entirely.

## Current behavior

- Edge is the only speech engine offered by schemas, discovery, previews and synthesis.
- Existing pinned English voices, catalogue/picker, speed, pitch and volume remain available.
- Script generation, durable jobs and regeneration produce spoken dialogue without the extra AI annotation pass. The editor has no emotion-insertion toolbar.
- Known retired Vietnamese/native tags are stripped at the save and speech boundaries; ordinary words and unrelated bracketed text remain.
- Karaoke uses Edge's native per-word timings. The experimental Chatterbox forced aligner and B's extra 120ms visual delay were not integrated.

## Existing projects

Migration `040_edge_plain_speech.sql` runs once in the existing transaction/tracking mechanism. Python adapters registered by `_apply_migration` recognize tags case-insensitively and normalize legacy config JSON.

The migration restores legacy speaker/profile engines to Edge, retaining valid pinned Edge IDs and otherwise choosing the existing accent/gender default. It removes stored tags and cue-only legacy rows, clears only affected line caches, and sets affected audio/video jobs stale/error with a regeneration message. The affected project returns to the script stage. Previous audio, video and exported files are retained.

After updating, open Step 4 and generate audio again for affected projects, then render the video in Step 5. A previous exported MP3/MP4 is not automatically rewritten by a database migration.

## Delivery and backups

Source changes are tracked in [Phase 77](../../.viepilot/phases/77-edge-plain-speech/PLAN.md). New Full/Lite 2.0.0 packages are built under `dist/2.0-edge-plain-20261024/`; older 2.0 packages are kept. Consult PHASE-STATE.md/HANDOFF.json for actual build/install completion rather than assuming a source edit changed the installed EXE.

Use SQLite's online backup/idle guard before installation or applying the migration. The existing Desktop installer backs up the old distribution, database and shortcut before replacing the installed Full edition. Migration must not race old running code.

No test suite or new tests were requested/run in this change. Static checks and build/data-operation results are recorded separately; audible acceptance of the installed app remains with the owner. Historical tests that assert the retired features need their contracts updated when a verification pass is requested.

## Local installation outcome

Full/Lite **2.0.0** packages were rebuilt in the new folder and Full was installed/restarted on 2026-10-24. The former installed app/database/shortcut are kept at `data/backups/desktop-20261024-115726-342/`; there is also an online pre-restoration snapshot at `data/backups/edge-plain-speech-20261024/app.before-restoration.db`.

Migration040 cleaned **3 lines in The Office Startup** (`5b1667a3-b47b-4c4b-b989-dddd3cb44b03`). All **40 projects**, **5 characters** and **80 Edge speaker settings** remain; 0 recognized cue lines remain. Audio/video for that project must be generated again. Integrity/FK results and counts are saved in `data/backups/edge-plain-speech-20261024/migration-report.json`.

Both ZIPs and checksums are in `dist/2.0-edge-plain-20261024/`. The running Desktop process is the updated Full build; no public release or GitHub push was made.
