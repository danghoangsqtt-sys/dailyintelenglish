# PLAN — Phase 51: Desktop runtime recovery

Status: **implemented_verified_pending_owner_review**, authorized by owner `vp-auto xử lý bug`,2026-10-16. This authorizes bug implementation and the local Desktop correction requested by the owner; no extra PM confirmation is needed. No publication or V49 acceptance implied.

## Objective
Fix BUG-045: existing profiles must expose voice selection and all 21 front presenter cards in the actual installed app. Fix recurring BUG-044 documentation after 49.6–49.10 implementation.

## Tasks / per-file plan
1. **51.1 implemented_verified:** build identity module; lightweight readiness/build endpoint in main; launcher reuses only the same build/data instance, rejects old/unknown occupied ports with a clear safe update instruction. Settings displays running build. Regression tests cover old/same/unknown identity, startup race and metadata privacy.
2. **51.2 implemented_verified:** offline/online consistent SQLite backup and idle-job preflight helper; installer safeguards before stopping only the exact installed EXE, preserves old distribution/shortcut. Disposable legacy-owner-copy migration + frozen old-profile browser rehearsal, then locally install and restart/verify actual Desktop build. Tests cover active jobs, WAL snapshot and upgrade integrity. No owner data edits beyond normal startup migrations.
3. **51.3 implemented_verified:** reconcile architecture/project/renderer docs and state; retain historical evidence, published 1.4.0-rc.1, feature 49.10 real-art/owner gates. Record quality, install/rollback and persistence proof.

## Paths / allowed_files
- `backend/core/build_info.py`
- `backend/desktop_launcher.py`
- `backend/main.py`
- `scripts/desktop_upgrade.py`
- `scripts/install_desktop.ps1`
- `frontend/pages/settings.html`
- `frontend/static/js/settings.js`
- `frontend/static/js/api.js` — centralized build identity request (CR-05).
- `tests/test_desktop_runtime.py`
- `tests/test_desktop_upgrade.py`
- `tests/test_build_info.py`
- `scripts/verify_desktop_upgrade.py`
- `.viepilot/ARCHITECTURE.md`
- `.viepilot/PROJECT-META.md`
- `renderer/README.md`
- `docs/api.md` — regenerate after build identity route addition.
- `.gitignore` — exclude the runtime voice catalog created by installed profile inspection.
- `docs/user/windows-installation.md`
- `docs/user/solo-explainer.md`
- `docs/operations/desktop-recovery-20261016.md`
- `.viepilot/requests/BUG-044.md`
- `.viepilot/requests/BUG-045.md`
- `.viepilot/audit/profile-ui-runtime-20261016.md`
- `.viepilot/TRACKER.md`
- `.viepilot/ROADMAP.md`
- `.viepilot/HANDOFF.json`
- `.viepilot/phases/49-solo-explainer/PHASE-STATE.md` — local installation checkpoint; keep V49 pending.
- `CHANGELOG.md`
- `.viepilot/phases/51-desktop-runtime-recovery/PLAN.md`
- `.viepilot/phases/51-desktop-runtime-recovery/PHASE-STATE.md`

## Risks and mitigation
- Owner SQLite may have WAL or active work: online SQLite backup, integrity/FK verification, inspect pending/running jobs; fail before process stop if busy. Rehearse migrations on a copy first; retain rollback DB + full previous distribution and shortcut.
- Same version does not mean same code: packaged identity hashes immutable build metadata plus EXE; separate data-instance identity prevents opening a different profile store. Expose no paths/secrets.
- Port races/unknown services: HTTP identity readiness, do not open a different app or terminate it.
- Startup migrations may add columns: compare original stable row identities and existing native asset hashes before/after/restart.
- Build is a local development trial; published release/real-art acceptance remain separate.

## Verification
Targeted pytest desktop/build/backup/health; node --check settings.js; PowerShell AST parsing; full ruff and pytest tests/ -x; actual frozen startup twice on copied old DB, browser voice/native29/front21/prompt/reload and Settings build/error path; installed EXE port owner + HTTP identity + existing profiles + integrity/native hash comparison. Explicit staging, commit/push and clean/upstream checks before formal technical PASS. Renderer unchanged; build script already runs typecheck/Player build/browser preparation.

## Result

Full pytest 1884 passed in 787.66s; 25 focused; local installed build 468f9f7ce4b4 verified on 5/5 existing profiles (47 voices, 29/21 slots), original owner rows and 289 native files preserved. Consistent rollback DBs/old EXE/shortcut retained. [Report](../../../docs/operations/desktop-recovery-20261016.md). Technical verification and owner/release gates remain separate.
