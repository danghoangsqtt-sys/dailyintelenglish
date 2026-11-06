# Task 98.8 - Verify Doodle duration and picture corrections

## Objective

Carry the owner's positive Apollo 11 review forward. Resolve BUG-056 in the normal audio mix. Check BUG-057 against the actual narration before changing an accepted sample. Leave the original projects and exports as review baselines.

## Paths

- `backend/core/constants.py` - document the maximum Doodle tempo correction.
- `backend/media/audio_service.py` - fit short Doodle narration to its target when a modest pitch-preserving correction is enough. Calibrate Edge word timing before scaling it onto the decoded output. Fit music to the resulting speech timeline.
- `backend/tests/test_audio_service.py` - regression for measured media duration, scaled line and word timestamps, and the existing behavior for other modes and large shortfalls.
- `backend/ai/image/recipes.py`, `backend/ai/image/pipelines.py`, `backend/tests/test_doodle_story.py` - enforce label policy when redrawing stored myth or fiction plans. Match the explicit label directive and strip it for those subjects. Cover legitimate historical labels and quoted narration.
- `backend/library/explainer_service.py`, `backend/ai/prompts/storyboard/explainer_doodle.txt`, `backend/tests/test_doodle_story.py` - picture accuracy follow-up only if representative verification shows an implementation gap.
- `CHANGELOG.md`, `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`, `.viepilot/phases/98-doodle-story/PHASE-STATE.md`, `.viepilot/requests/BUG-056.md`, `.viepilot/requests/BUG-057.md` - record evidence and open checks.

## File-Level Plan

- Apply the correction only to Doodle and only when actual decoded narration is short by an amount that can be corrected at a tempo of 0.82 or higher. Larger shortfalls need a longer script. Keep the selected TTS voice, its settings and cached speech. Use the existing FFmpeg tempo filter and retain pitch.
- Use actual output milliseconds to transform line and word timing together. Keep legacy timing reads idempotent. Reuse the music bed after speech timing has been fitted.
- Run focused audio and Doodle tests. Re-mix the real cached B1 narration for Lantern and Apollo using the normal service with isolated output paths. Check source anchors, audio durations and timing alignment. Verify image corrections on the affected scenes where the local runtime is available.

## Risks and gates

- Tempo changes can sound artificial and old storyboards may exceed their 12-second span after the mix changes. Keep the correction bounded and verify a fresh timing-based storyboard.
- Record narration and MP4 durations separately because Studio adds its branded tail. Existing published or reviewed files remain independent review baselines.
- Owner review of Apollo's overall quality has been recorded. Keep the task open for any visual correction or persistence gate still pending.

## Verification checkpoint

Both fitted mixes and isolated storyboard approvals passed. Three selected Qwen replacements passed visual review. Remotion browser startup failed in this execution environment. See [measured results and remaining gates](PHASE-STATE.md#task-988-verification-2026-11-06).

## Offline review exports

The Remotion Chrome connection is still unavailable in this execution environment. Build isolated MP4 review copies in `data/tmp/phase98-review/` from the approved assets, fitted audio, renderer caption/card timing helpers, and the original branded endings. Check FFprobe, black frames and the changed scenes. This is a media verification path. The Studio export and Git persistence remain independent gates.

The isolated Apollo review needs its seven selected script terms in the learning pack. Add validated bilingual vocabulary to that test database, then re-pin the unchanged scene and audio inputs. The original project remains the comparison baseline.

- `backend/content/learning_pipeline.py` and `backend/tests/test_learning_pipeline.py`: require exact dictionary entries for the Doodle script's selected terms in the initial, repaired and reduced learning pack. Reuse the existing repair attempt and failure state. Other styles continue to use their existing validation. Run the focused learning pipeline tests.
