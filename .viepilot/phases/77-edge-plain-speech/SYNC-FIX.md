# Edge karaoke repair — 2026-10-24

Owner explicitly requested implementation through vp-debug after the measured diagnosis. Continue Phase 77 with Edge only; preserve all existing work. No commit or push.

## Plan and bounded files

1. Measure native Edge boundaries against decoded audio for English male/female voices and several speech rates. Keep the provider capture immutable; apply one documented timing calibration at the mixing boundary if the matrix supports it.
2. Remove the measured AAC priming offset by rebuilding the final audio track from the exact composition timeline before atomic publication. Account for branding, no music and nonzero clip frame ranges. Preserve the last good output on failure.
3. Produce a short real render and compare the decoded result to its source; check the affected episode. Build and install Full/Lite 2.0.0 through the existing guarded scripts after the app is idle.

Allowed production files: `backend/core/constants.py`, `backend/media/audio_service.py`, `backend/media/video_renderer_remotion.py`, and a focused audio timeline helper `backend/media/render_audio.py` if needed. Raw TTS/cache fingerprints must stay compatible; any expansion must be recorded here first.

Allowed supporting paths: this file, the adjacent `PHASE-STATE.md` follow-up record, `.viepilot/debug/CURRENT.json`, `.viepilot/debug/session-debug-20261024-edge-karaoke.json`, `docs/operations/edge-karaoke-diagnosis-20261024.md`, `CHANGELOG.md`, `.viepilot/HANDOFF.json`; isolated diagnostic scripts/media in `data/tmp/edge-karaoke-diagnosis-20261024/`; fresh build `dist/2.0-edge-sync-20261024/`, installed `dist/DailyIntelEnglishStudio/`, guarded installer backups and desktop shortcut. Current project DB/media changes only with idle preflight, online backup and optimistic checks against the captured job revision.

## Risks and checks

- CTC is an approximate onset estimate, not perceptual ground truth: retain the raw evidence and report the calibration limit.
- Avoid applying compensation twice: raw `.words.json` stays unchanged and only the mixer converts to the decoded audio clock.
- Never trim the beginning of speech to hide a metadata error. Use lossless composition audio and normal AAC skip metadata.
- Verify rate/voice matrix, exact final sample alignment and clip trimming as debugging measurements. No unrelated test suite or restored local TTS/emotion support.
- Installation must not interrupt active jobs. Keep version 2.0.0 and old packages/backups.

Status: implemented_verified_installed_pending_owner_listening_review. Full/Lite2.0.0 packaging exit0; four production modules match source bytecode in both EXEs. Full installed/restarted (PID30980), live build identity/dashboard/current-video/corrected-word API checks succeeded. All40projects retained, SQLite integrity ok. Technical debug session resolved; owner listening acceptance remains pending. No formal PASS, commit, push or public release.
