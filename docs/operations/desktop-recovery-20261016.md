# Desktop runtime recovery — 2026-10-16

Status: implementation, local installation and full regression verified; Source and technical-tag persistence verified. Owner acceptance remains separate. BUG-045 and recurring BUG-044; [bounded Phase 51 plan](../../.viepilot/phases/51-desktop-runtime-recovery/PLAN.md).

## Cause and implementation

The Desktop shortcut ran the 2026-10-15 distribution (PID 30048, source`f8f7675`). Its actual `/characters` response lacked voice/front21 controls. The launcher treated any listener on 8000 as the same application and silently opened that old UI.

`backend/core/build_info.py` fingerprints packaged code and metadata, with a separate opaque data-instance identity. `/api/system/build` exposes that identity after startup; Settings displays version, local build time and short build ID. It returns no filesystem paths, API keys or project content. Same-version builds remain distinguishable. Source builds fingerprint source resources once per process.

The launcher opens an existing server only if product, code and data identity match; other/old/unknown listeners produce an explicit close/update instruction without opening that UI or stopping its process. Readiness checks HTTP identity after migrations, including the competing-port case. A real request to the old app before installation was safely rejected. A second launch of the actual installed EXE later exited 0 and reused the intended server.

The installer now checks SQLite integrity/FKs and unfinished jobs, makes an online SQLite backup including committed WAL, rechecks idle status, and stops only the exact installed executable. After exit it takes a final snapshot before swapping distributions. It retains the old folder and Desktop shortcut. The new preflight fails closed for unknown job states. All thirteen projects/five profiles were idle at installation.

## Rehearsal before owner upgrade

Command: `.venv/Scripts/python.exe scripts/verify_desktop_upgrade.py --stage data/tmp/phase51-exe-stage/DailyIntelEnglishStudio/DailyIntelEnglishStudio.exe`.

A consistent owner DB snapshot and copied character/sprite folders were used under `data/tmp/phase51-upgrade/`; explicit isolated DATA_DIR/cloud-off settings prevented owner writes or cloud generation. Actual frozen startup migrations and two process launches preserved all original columns/rows in projects, characters, assets, speakers, script lines, durable AI jobs/checkpoints. Integrity/FKs passed; all 289 existing character/sprite file hashes matched. Both launches reported the same code/data identities. This rehearsal was run twice, the second also waiting for the real catalog to load.

Browser evidence for each of the five old profiles: 47 English voice choices, 29 native slots, 21 front slots, 21 prompts with 1280×1536 instructions and 21 file inputs. Invalid image import on the disposable copy showed a readable error without altering rows/files. Profile switching, page reload, Settings build display, failed build-request fallback and recovery passed with zero page errors. No owner art was fabricated or approved.

Evidence: `data/tmp/phase51-upgrade/rehearsal-report.json`, `hoang-front21.png`, `settings-build.png`; reports/screenshots remain local because they concern owner profiles.

## Actual local installation

- Staging: `data/tmp/phase51-exe-stage/DailyIntelEnglishStudio/`; complete onedir distribution built successfully, including Player/typecheck/browser preparation. The outer PowerShell redirection reported a nonzero wrapper status from native stderr warnings; build completion/metadata and the actual frozen startup/UI were verified directly.
- Installed: `dist/DailyIntelEnglishStudio/DailyIntelEnglishStudio.exe`; Desktop shortcut **Daily Beyond English Studio** points here.
- Backup: `data/backups/desktop-20261016-220746-404/`: previous complete distribution, `Desktop-shortcut.lnk`, `app.before-upgrade.db`, `app.at-exit.db`.
- Installer exit 0; actual shortcut launch PID 20996 owns both 127.0.0.1:8000 and[::1]:8000.
- Serving build ID: `468f9f7ce4b472aa6c26b26469f41d979a02d16ad5822786ef6f3f2c6041e04a`, metadata built 2026-10-16T15:04:57.6566661Z. Parent source`b659fb1`, `source_dirty=true`: an explicitly identified local worktree trial, not a clean release artifact.
- EXE SHA256: `08fdad32d35140dc3d59c71165cb5c5ddc7963e3c346a03d02027193a0a53087`. Live `/characters` and static Player hashes match installed bundled resources; schema migration tracker advanced 27→30. Both rollback DB snapshots independently passed integrity/FK/count checks.
- Read-only browser verification on the real installed app repeated 47 voices +29/21 slots for all five profiles and reload/Settings checks. Original owner table hashes and 289 native file hashes matched the pre-install manifest; integrity/FKs passed. Existing counts: 13 projects, 5 characters, 190 asset rows, 17 AI jobs, 91 image jobs, 8 audio jobs, 7 video jobs.
- Evidence: `data/tmp/phase51-upgrade/installed-report.json`, `owner-before.json` (hashes/schema only), `install.log`. An initial inspection started before the app was ready and hit connection refused; the harness now waits for the HTTP readiness identity and the check passed.

An optional combined command to compare data and stop/restart the new installed app was rejected by automatic approval review (`blocked by policy`; no more specific reason returned). It made no changes. The installed app was left running; read-only integrity/UI checks and a same-build second launch passed separately. Two frozen restarts were verified on the faithful data copy. No repeated attempt to force a real-app restart was made.

## Quality and boundaries

Focused tests: 25 passed in 4.05s (desktop boot, build identity/privacy/API, wrong-build/database/unknown listener, readiness race/timeout, committed WAL snapshot and unfinished-job/FK guards). Ruff, modified JS syntax and PowerShell installer AST checks passed. OpenAPI reference regenerated: 184 routes. Runtime voice catalog is ignored by Git.

Full regression: **1884 passed in 787.66s (13:07)**; evidence `data/tmp/phase51-pytest-full.log`. One existing Starlette/httpx deprecation warning, no failures. Ruff/JS syntax/PowerShell AST/diff checks clean. Source checkpoint`cefb3e2` was committed/pushed to`origin/owner-runs/20261001-r9`; all 3 annotated technical task tags`die-vp-p51-t51.1-done` through`51.3-done` resolve remotely to that commit. Clean worktree and ahead 0/behind0 verified before this documentation checkpoint; final check follows its push. No phase-complete/release/V49 acceptance tag created.

BUG-044 architecture/project metadata/renderer README now describe implemented shared SoloScene, Player, production and integration behavior; distinguish verified implementation, installed local trial and the published ZIP. Historical Phase 50 evidence remains historical. Phase 49 has 9/10 technically verified tasks and 49.10 implementation/package checks; the real owner front21 demo and V49 acceptance remain pending because the owner has no pictures yet. Published GitHub 1.4.0-rc.1 and stable 1.3.0 remain unchanged; target 1.5.0 is unreleased. No old owner gate was closed.
