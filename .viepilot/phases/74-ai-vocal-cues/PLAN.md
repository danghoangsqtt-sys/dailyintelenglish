# PLAN — Phase 74: AI vocal cues and expressive Edge TTS

**Status:** code implemented for 74.1–74.3; 74.4 listening and verification pending. Owner invoked vp-auto on 2026-10-23; owner acceptance and release decisions remain separate. Source: [brainstorm](../../../docs/brainstorm/session-2026-10-23-tts-emotion.md), [specification](SPEC.md).

## Architecture and order

The production script path is `script_pipeline._run_script_job`; it validates/repairs section text, then publishes `server_lines`. First extend the parser/TTS so newly generated tags are safe to play. Then add a single optional AI annotation stage after global/vocabulary repair and before final publication. Legacy generate and one-line regenerate receive compatible behavior. Finally expose variant editing and conduct listening review.

AI output is a JSON cue plan with `line_index` (zero-based), `after_word_index` (zero means before the first word), `cue_type` and optional `variant`. Server code validates its schema and indices, at most one cue per line, a hard episode quota of `ceil(duration_minutes * 2)`, and contextual spacing; it inserts tags by whitespace-token spans. The model cannot submit replacement dialogue. Zero cues is valid. Invalid entries are skipped with diagnostics; provider failure keeps the clean, validated script. Script generation does not call Edge TTS.

During the additional AI call, hold no DB write lock. Heartbeat the durable job and check cancellation/config hash again after the call, before the existing short publish transaction. A worker restart may redo the optional annotation on clean section checkpoints; it must not publish a partially tagged script. Regeneration of one line checks the remaining episode cue budget and leaves other edited lines untouched.

## Tasks and dependencies

| Task | Outcome | Depends on | Card |
|---|---|---|---|
| 74.1 | Backward-compatible cue grammar, Edge vocal variants/temporary low pitch, timings/cache | Existing three-tag implementation | [74.1](tasks/74.1.md) |
| 74.2 | AI annotation after validated dialogue, fallback and regeneration coverage | 74.1 | [74.2](tasks/74.2.md) |
| 74.3 | Step 2 variant editing, guidance and export checks | 74.1, 74.2 | [74.3](tasks/74.3.md) |
| 74.4 | Real listening matrix, integration review and owner handoff | 74.1–74.3 | [74.4](tasks/74.4.md) |

## Bounded source paths

- TTS: `backend/ai/tts/vocal_cues.py`, `backend/ai/tts/tts_service.py`, `backend/core/voice.py`, `backend/core/constants.py`.
- Script AI: `backend/ai/prompts/script/vocal_cue_annotation.txt`, `backend/ai/llm/prompt_loader.py`, `backend/content/vocal_cue_annotation.py`, `backend/content/script_pipeline.py`, `backend/content/script_service.py`, `backend/api/projects.py`, `backend/api/ai_jobs.py`.
- Presentation/export: `frontend/static/js/step2_script.js`, `frontend/static/js/i18n_vi.js`, `frontend/static/css/style.css`, `backend/media/audio_service.py`, `backend/content/learning_service.py`, `backend/content/youtube_service.py` only if new variants require changes beyond the shared stripper.
- Targeted verification files: `tests/test_vocal_cues.py`, `tests/test_tts_service.py`, `tests/test_tts_word_boundary.py`, `tests/test_script_pipeline.py`, `tests/test_script_service.py`, `tests/test_script_api.py`, `tests/test_script_jobs_browser.py`, `tests/test_audio_service.py` as needed by the assigned task.
- Delivery artifacts: this phase's `SPEC.md`, `PLAN.md`, `PHASE-STATE.md`, task cards, `docs/brainstorm/session-2026-10-23-tts-emotion.md`, `docs/operations/phase74-listening.md`, `.viepilot/AI-GUIDE.md`, `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`, `.viepilot/PROJECT-CONTEXT.md`, `.viepilot/ARCHITECTURE.md`, `.viepilot/STACKS.md`, and `CHANGELOG.md` upon implementation. Stack guidance is cached at `C:/Users/Admin/.viepilot/stacks/edge-tts-vocal-cues/`.

Each task card narrows this union; implementation changes outside its card require a plan amendment first. Preserve all existing uncommitted Phase 73 and user changes. No migration, release or installed EXE update is in scope.

## Research and stack guidance

- [Edge TTS maintainer README](https://github.com/rany2/edge-tts#custom-ssml): voice/prosody options, no custom SSML. Do not promise native emotional speech.
- [Maintainer emotion answer](https://github.com/rany2/edge-tts/discussions/176): no custom-SSML emotion support.
- [Azure Speech SSML documentation](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice): style/audio are a separate service, outside this phase.
- Stack cache: `C:/Users/Admin/.viepilot/stacks/edge-tts-vocal-cues/` (summary, practices, anti-patterns, sources; accessed 2026-10-23). Indexed in `.viepilot/STACKS.md`.

## Risks and verification plan

- **Voice quality:** “hi hi”/“haiz” may be read as ordinary words. Prepare a small real Edge sample matrix before choosing phonetics per voice. Report inadequacy instead of declaring natural laughter/sigh.
- **Latency:** each cue and low-pitch span adds Edge calls and MP3 processing. Bound event count; untagged lines retain one call.
- **Timing:** measure decoded segments, update sidecar offsets, and inspect SRT/karaoke; avoid raw MP3 byte concatenation.
- **Cache/staleness:** recipe version affects cue-bearing line fingerprints and stale network completion checks, while ordinary lines remain reusable.
- **Script safety:** only the annotation plan is AI-generated; prose is immutable. Provider timeout/invalid plan cannot fail a clean script. Recheck project revision after annotation.
- **Verification after implementation:** targeted Python service/API/worker/browser checks for parser, quota, fallback, race and timing; Python/JS syntax and Ruff; real listening and sample mix inspection. Planning makes no test-result claim.
