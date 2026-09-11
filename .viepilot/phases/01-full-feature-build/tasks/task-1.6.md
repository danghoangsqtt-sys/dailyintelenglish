# Task 1.6: Step 4 — TTS Audio Studio

## Meta
- **ID**: 1.6
- **Phase**: 1
- **Status**: planned
- **Priority**: high
- **Assignee**: AI

## Paths
- `app/services/tts_service.py`
- `app/services/audio_service.py`
- `app/api/tts.py`
- `frontend/pages/step4_tts.html`
- `frontend/static/js/step4_tts.js`

## Acceptance Criteria
- [ ] TTSService supports OmniVoice local GPU with concurrency semaphore(2)
- [ ] Automatic fallback to Edge TTS on OOM / error
- [ ] AudioService mixes tracks with speaker pauses and volume normalization
- [ ] TTS UI supports audio preview, regeneration, and export

## Forbidden Scope
- No blocking the event loop with ffmpeg or audio model synthesis
- No VRAM exhaustion without fallback

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
- `venv\Scripts\ruff check app/`
