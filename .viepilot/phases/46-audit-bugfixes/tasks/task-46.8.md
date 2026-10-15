# Task 46.8: owner trial EXE, GitHub update and render diagnosis

## Authorization and status

In progress, 2026-10-15. The owner explicitly requested replacing the old EXE and updating the project's GitHub for an extended usage trial. This authorizes build/install, commit/push and a prerelease artifact, superseding the previous no-build hold for this trial only. B-25/B-26/B-27/B-28 remain pending; no blanket acceptance of those gates.

## Plan / allowed_files

- backend/core/desktop_runtime.py (new), backend/desktop_launcher.py: load a local runtime locator before application imports, so double-clicking the new EXE uses the actual workspace data and external renderer/image environment independently of working directory. Explicit environment overrides take precedence.
- backend/core/paths.py, backend/media/video_renderer_remotion.py, backend/ai/image/engine.py: separate bundled UI/prompts/migrations from the linked renderer, models and image-worker runtime. Preserve source defaults and fail clearly for an invalid explicit workspace.
- daily_intel_english_studio.spec, scripts/build_exe.ps1: bundle the brand resource, fail on build errors, build to a reviewable staging directory, and write runtime/build metadata without credentials or user content.
- Owner steering: a one-click application with the existing logo as its icon. Add assets/app.ico (format conversion from the existing PNG), scripts/install_desktop.ps1 (verified local distribution installation and Desktop shortcut). Build without a console, retain startup logs and show a native error dialog on launch failure. Existing browser UI remains the app interface.
- tests/test_desktop_runtime.py, tests/test_runtime_paths.py (new): startup ordering/relative locator, explicit override, invalid configuration, frozen/source path selection and image runtime resolution.
- renderer/src/Sprites.tsx and backend/core/config.py only if controlled measurements isolate a compatible render optimization; otherwise report measured causes without an unsupported speed claim. Any additional candidate file must be added to this plan before implementation.
- Measured optimization amendment: CDP confirms default Chrome uses CPU SwiftShader with GPU compositing disabled; explicit ANGLE uses the RTX 3060/D3D11. Two identical 1,200-frame comparisons improve from 71.392/70.812 s to 46.627/47.975 s; removing sprite rotation does not help. Allow .env.example and tests/test_video_service_remotion.py to expose/test a validated REMOTION_GL setting (Windows default angle, auto elsewhere; opt-out auto). Keep encoder/quality, layout, motion and retry policy unchanged. Do not extrapolate short samples into a promised full-episode time.
- .gitignore: ignore the local .remotion download cache (retain it; do not delete).
- README.md, CHANGELOG.md, .viepilot/TRACKER.md, ROADMAP.md, HANDOFF.json, PROJECT-META.md, phase-46 PHASE-STATE.md and this card: record trial version v1.4.0-rc.1, authorization, evidence and pending owner gates.
- docs/operations/exe-trial-20261015.md and render-performance-20261015.md: launch/rollback instructions, build verification and controlled performance findings.
- Disposable measurements/build/smoke/ZIP artifacts under data/tmp/exe-trial-20261015/ and build/. Snapshot the old complete dist directory and workspace/AppData DBs under data/backups/ before replacing the verified dist target.
- Explicitly stage and commit the existing phase-46 source/docs/tests plus these changes; never stage runtime data, credentials, models or node_modules. Push the existing owner branch and publish a clearly marked GitHub prerelease with the packaged ZIP if authenticated access permits. Do not force-push or merge main implicitly.

## Risks and verification

- Old packaged app has a different AppData DB; retain both DBs and point this local trial to the 13-project workspace data. Stop only the identified old EXE and owned source server after the staged build passes smoke checks; no active jobs may be interrupted.
- Remotion and Qwen depend on the existing workspace/runtime, not only the EXE. Verify those paths from the frozen process, bundle UI resources and include extraction/launch instructions in the release.
- Compare identical short ranges with one variable changed at a time (rotation, compositing/GL, blur), sequentially with no competing render. Capture real frames/same props and distinguish capture from encoding. Preserve visual behavior for any adopted optimization.
- Full pytest required before commit; Ruff, modified frontend JS syntax, renderer TypeScript/Vitest, diff checks and staged secret/path-size review. Frozen smoke on an isolated SQLite backup, UI/static assets, renderer health, project status/media and external runtime availability; then install and confirm production data count and server readiness.
- Snapshot/verify absolute source/target paths before Windows copy/move. Keep the old complete distribution for rollback; no destructive cleanup of unrelated folders.

## Verification before GitHub publication

- Full pytest: 1636 passed / 891.13 s; 89 Vitest and TypeScript clean. Final frozen bootstrap/path tests rechecked: 11 passed. Ruff, modified frontend JS syntax and diff checks clean.
- Branded windowed EXE built and smoke-tested from System32 against an isolated DB: 13 projects, renderer/image runtime ready, UI/font/media ranges served and real bundled music analysis succeeded. PE subsystem 2 and embedded logo verified.
- Installed the complete verified distribution and created the logo Desktop shortcut. Installed EXE runs on port 8000 using the actual 13-project workspace data. Old distribution: data/backups/desktop-20261015-153630/. Both DB snapshots: data/backups/exe-trial-20261015/.
- Shortcut target/icon/working directory verified. Automatic approval review rejected launching the opaque .lnk with only "blocked by policy"; the explicit verified EXE path was subsequently approved and launched. Do not claim a shortcut-click execution test.
- CDP confirms CPU SwiftShader in automatic mode versus RTX 3060/D3D11 under ANGLE. Two 1200-frame pairs: 71.392→46.627 s and 70.812→47.975 s. Applied validated configurable Windows ANGLE default; encoder/quality/motion unchanged. Full-episode elapsed gain remains unmeasured.
- Secret/size scan of the 86-file pending update found no flagged credentials or unexpected large file. GitHub publication and clean-source build metadata remain in progress.
