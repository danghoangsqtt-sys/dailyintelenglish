# Phase 77 state

Status: implemented_packaged_installed_pending_owner_review. Owner authorized restoration on 2026-10-24. No formal PASS/git-persistence claim.

- 77.1 implemented — Edge-only discovery/schemas/preview/dispatch; annotation implementation/prompt and UI removed; only legacy tag stripping remains.
- Static inspection: touched Python files passed Ruff/AST; changed JS syntax passed; HANDOFF JSON and diff whitespace passed. Build scripts also ran renderer typecheck/build. No tests were requested, added or run.
- Full/Lite 2.0.0 built at `dist/2.0-edge-plain-20261024/`; ZIP creation completed with built-in integrity checks and SHA256SUMS. The outer PowerShell redirection reported NativeCommandError for npm warning stderr although the inner script completed both builds/packages; package logs and outputs record completion.
- Full installed with the guarded installer; old EXE/database/shortcut kept at `data/backups/desktop-20261024-115726-342/`.
- Online pre-restoration DB backup: `data/backups/edge-plain-speech-20261024/app.before-restoration.db`.
- Migration040 applied locally: 3 tagged lines cleaned in project `5b1667a3-b47b-4c4b-b989-dddd3cb44b03`; 0 tagged lines remain; 40/40 projects and 80 Edge speakers retained. SQLite integrity ok, no FK issues. No output media files deleted; affected media marked for regeneration.
- Installed Full 2.0.0 restarted normally (PID32372); startup/dashboard requests are visible as 200 responses in the normal app log. No synthesis/render test was run.
- Owner should regenerate Step 4 audio and Step 5 video for the affected Office Startup project. Historical feature tests asserting OmniVoice/cues were not updated or run; audible/regression acceptance remains pending.
- No commit, push, tag or public release performed.

## Follow-up: owner-requested Edge karaoke repair

The earlier regenerate recommendation above was followed by the owner, but sync remained wrong. The subsequent explicit fix request is implemented under [SYNC-FIX.md](SYNC-FIX.md).

- Source repair: idempotent rate-aware word onset calibration, original-source AAC mux, lossless composition soundtrack, matching frame rounding and clip trimming.
- The25-line Office Startup episode has been rendered and published; old outputs and the pre-fix SQLite backup are retained. Owner does not need to synthesize its voices again.
- Full/Lite2.0.0 packages: `dist/2.0-edge-sync-20261024/`. Both builds passed bytecode/source comparison for the four modified production modules. Full installed/restarted, PID30980; rollback backup `data/backups/desktop-20261024-163016-755/`.
- Live installed build identity matches the new EXE/metadata; dashboard200, current video path, calibrated words, database integrity and40projects retained were checked. Debugging measurements cover16 voice/rate captures, landscape/portrait/branding and six full-episode windows; no unrelated test suite was run.
- Technical debug session resolved. Owner listening review remains pending; no formal PASS/git-persistence claim or public release.
