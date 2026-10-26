# Phase 77 — Restore plain Edge speech

Owner instruction (2026-10-24): return the whole product to the old Edge voices and remove emotion insertion from scripts. This is authorization to implement the bounded restoration; prior OmniVoice/Chatterbox exploration is superseded. No commit/push/public release is requested.

## Tasks

1. Remove AI cue annotation from durable, compatibility and single-line generation. Sanitize only known retired editorial tags at script write/TTS boundaries. Keep actual dialogue and unrelated bracketed text.
2. Make Edge the only selectable/dispatchable engine and retain the Edge catalogue, voice picker, speed/pitch/volume and native word timestamps. Remove local engine/design and cue-insertion UI.
3. Add migration040: normalize old speaker/profile/config engines, remove stored tags, clear affected line caches and mark affected media stale without deleting existing exported media. Back up and apply to the idle local DB.
4. Record owner feedback and source/install state. Run syntax/static inspection only; no test suite or new tests, as the user has not requested testing. The installed Full EXE is running old code; rebuild Full/Lite 2.0.0 in a new folder, install Full through the guarded installer, then apply migration040 before restarting the app. Do not claim user acceptance.

## Paths / allowed_files

- `backend/core/constants.py`: Edge engine list and plain-speech cache recipe version.
- `backend/core/voice.py`: effective Edge voice fingerprints without cue recipe.
- `backend/ai/tts/vocal_cues.py`: retain only legacy tag recognition/stripping compatibility.
- `backend/ai/tts/tts_service.py`: single normal Edge request, no cue synthesis/local engine dispatch.
- `backend/ai/tts/voice_preview_service.py`, `backend/schemas/tts.py`, `backend/api/tts.py`: Edge-only auditions and discovery.
- `backend/content/script_service.py`, `backend/content/script_pipeline.py`, `backend/api/projects.py`, `backend/api/ai_jobs.py`: no annotation scheduling; clean saved dialogue.
- `backend/content/vocal_cue_annotation.py`, `backend/ai/llm/prompt_loader.py`, `backend/ai/prompts/script/vocal_cue_annotation.txt`: remove the retired annotation implementation/template and loader.
- `backend/ai/prompts/script/script_base.txt`, `backend/ai/prompts/script/regenerate_line.txt`, `backend/ai/prompts/script/section.txt`: add plain-dialogue instruction if applicable after reading exact files.
- `backend/db/database.py`, `backend/db/edge_only_restore.py`, `backend/db/migrations/040_edge_plain_speech.sql`: transactional compatibility migration with pinned helper functions.
- `frontend/static/js/step2_script.js`, `frontend/static/js/step4_tts.js`, `frontend/static/js/step1_config.js`: remove cue/engine UI and submit plain Edge settings.
- `frontend/static/css/style.css`, `frontend/pages/step4_tts.html`: remove retired feature styling.
- `.viepilot/phases/77-edge-plain-speech/PLAN.md`, `PHASE-STATE.md`, `tasks/task-77.1.md`: bounded contract and evidence.
- `.viepilot/SYSTEM-RULES.md`, `.viepilot/ARCHITECTURE.md`, `.viepilot/STACKS.md`, `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`, `CHANGELOG.md`, `README.md`: document restored policy and delivery limits.
- `docs/operations/edge-plain-speech.md`, `docs/brainstorm/session-2026-10-23-tts-emotion.md`, `.viepilot/debug/session-debug-20261024-chatterbox-karaoke.json`: operational guidance and owner decision.
- `.viepilot/debug/CURRENT.json`: close the superseded expressive-TTS investigation after the owner abandons that direction.
- `data/backups/edge-plain-speech-20261024/`, `data/app.db`: online SQLite backup and owner-authorized existing-data migration, only after idle preflight. Generated files stay out of git.
- `scripts/package_desktop.ps1`, `daily_intel_english_studio.spec`: remove retired worker payload/installation guidance; require the new migration in packages.
- `.viepilot/AI-GUIDE.md`, `docs/operations/omnivoice-local-tts.md`: state the new Edge-only policy and retire old setup instructions.
- `dist/2.0-edge-plain-20261024/`, `dist/DailyIntelEnglishStudio/`, installer-generated `data/backups/desktop-*` and Desktop shortcut: rebuild Full/Lite 2.0.0 and replace the idle installed Full app, using the existing guarded installer. Keep old 2.0 packages/backups.

## Risks and handling

- A cached audio/video may still contain old cues: invalidate affected DB references/status, keep last-good files, require regeneration.
- Old queued job snapshots contain cue flags: ignore those flags in every generation path; do not start workers during migration.
- Legacy scripts/configs may contain annotations: strip only the recognized Vietnamese/native tags, not arbitrary bracketed dialogue; reject new empty spoken lines and remove cue-only legacy rows during migration.
- Non-Edge voice IDs cannot be sent to Edge: retain valid saved English Edge IDs and otherwise use existing accent/gender defaults.
- DB writes while old code runs could reintroduce cues: do not claim the installed binary updated by a source edit; migrate on startup of the new build as well.
- Automated tests remain unrun by instruction. Existing historical feature tests may require contract updates in a separately requested verification pass.

## Inspection / evidence

- Python AST compilation and JavaScript syntax checks for touched files, no provider/GPU calls.
- Read-only search for reachable annotation/local-engine UI/dispatch.
- SQLite idle preflight, online backup and migration ledger; inspect counts after applying as part of the data change.
- No automatic commit/push or formal PASS declaration.
