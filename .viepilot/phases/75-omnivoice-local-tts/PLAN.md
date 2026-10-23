# PLAN — Phase 75: OmniVoice Voice Design, local TTS

**Status:** in_progress (2026-10-23). Owner approved integrating the OmniVoice Voice Design sample. Edge stays default; local model execution is optional and explicit. Source: [SPEC](SPEC.md), [TTS emotion brainstorm](../../../docs/brainstorm/session-2026-10-23-tts-emotion.md).

## Architecture and order

Keep OmniVoice in a dedicated Python environment and subprocess, following the repository's existing isolated GPU-worker pattern. The FastAPI app sends one line at a time to a one-shot child process; each process loads the local model, synthesizes the whole line, and exits after returning audio through a temporary WAV file. Acquire the process-wide GPU lease around model work. Never load Torch/OmniVoice into the app venv or package model weights into the app.

Dispatch from the stored `tts_engine`; never infer or silently change the engine. Edge's current path stays intact. OmniVoice gets a deterministic voice-design instruction from the stored gender/accent/pitch and optional `voice_description`; speed and volume are applied within documented capability. Convert only the three supported laugh cues and sigh cue to model-native tags. Reject ahem on OmniVoice with an actionable message. Keep cue-free transcript stripping unchanged.

The existing model produces audio but no per-word timings. Preserve current honest no-word-sidecar behavior for those lines (line-level audio/SRT remains available; karaoke has no word highlight for that line). Do not fabricate word timing.

## Tasks and dependencies

| Task | Outcome | Depends on | Card |
|---|---|---|---|
| 75.1 | Isolated local runner, engine dispatch, native cue mapping, readiness and GPU lease | Phase 74 cue parser and existing GPU manager | [75.1](tasks/75.1.md) |
| 75.2 | Persisted engine/design controls and honest voice preview/status in Step 4 | 75.1 | [75.2](tasks/75.2.md) |
| 75.3 | Dedicated setup, operating/listening docs, state and handoff synchronization | 75.1–75.2 | [75.3](tasks/75.3.md) |
| 75.4 | Version 2.0.0 Full/Lite desktop setup packages and local Full installation | 75.1–75.3 | [75.4](tasks/75.4.md) |

## Bounded paths

- Task 75.1: `backend/ai/tts/omnivoice_service.py`, `backend/ai/tts/omnivoice_worker.py`, `backend/ai/tts/tts_service.py`, `backend/ai/tts/vocal_cues.py`, `backend/ai/image/gpu_model_manager.py`, `backend/core/config.py`, `backend/core/constants.py`, `backend/core/voice.py`, `backend/main.py`; tests: `tests/test_omnivoice_service.py`, `tests/test_tts_service.py`, `tests/test_vocal_cues.py`, `tests/test_gpu_model_manager.py`.
- Task 75.2: `backend/schemas/project.py`, `backend/schemas/tts.py`, `backend/api/projects.py`, `backend/api/tts.py`, `backend/ai/tts/voice_preview_service.py`, `frontend/pages/step4_tts.html`, `frontend/static/js/step4_tts.js`, `frontend/static/js/i18n_vi.js`; tests: `tests/test_projects_api.py`, `tests/test_tts_api.py`, `tests/test_tts_audio_browser.py`, `tests/test_voice_preview.py`.
- Task 75.3: `backend/ai/tts/omnivoice-requirements.txt`, `scripts/setup_omnivoice.ps1`, `docs/operations/omnivoice-local-tts.md`, `.viepilot/SYSTEM-RULES.md`, `.viepilot/ARCHITECTURE.md`, `.viepilot/STACKS.md`, `.viepilot/AI-GUIDE.md`, `.viepilot/PROJECT-CONTEXT.md`, `.viepilot/ROADMAP.md`, `.viepilot/TRACKER.md`, `.viepilot/HANDOFF.json`, `.viepilot/phases/74-ai-vocal-cues/PHASE-STATE.md`, `.viepilot/phases/74-ai-vocal-cues/tasks/74.4.md`, `.viepilot/phases/75-omnivoice-local-tts/PHASE-STATE.md`, `.viepilot/phases/75-omnivoice-local-tts/tasks/75.3.md`, `docs/brainstorm/session-2026-10-23-tts-emotion.md`, `CHANGELOG.md`.
- Task 75.4: see [task card](tasks/75.4.md); package orchestration, frozen OmniVoice worker support, version metadata/docs, and generated `dist/2.0/` artifacts.

The task cards narrow these paths. Preserve all existing uncommitted Phase 73/74 and owner changes. No commit, push, or public release is authorized. Owner authorized Task 75.4 to build local Full/Lite ZIPs and install Full on this computer.

## Risks and verification

- **GPU memory and concurrency:** use the shared lease; refuse with a clear message if the measured free-memory threshold is not met. Keep worker/model out of GPU outside synthesis.
- **Optional dependency drift:** pin the separate Python 3.11/CUDA 12.8 environment; do not modify `.venv` or `.venv-image` during setup.
- **Cue semantics:** model-native laughter/sigh are supported; ahem is not. Reject unsupported tags rather than silently losing emotion or mixing voices.
- **Voice consistency:** OmniVoice generates full dialogue lines. It does not overlay cue-only audio on Edge output.
- **Timing:** no fabricated word alignment; existing renderer behavior without a word sidecar is retained and called out.
- **Model/network:** first download is several GB and requires Hugging Face access; setup/readiness errors must remain actionable.
- **Verification:** focused service/API/browser/GPU-manager tests, Python/JS syntax, Ruff, and diff checks; local CUDA inference/latency/VRAM and owner audio review are separately reported.
