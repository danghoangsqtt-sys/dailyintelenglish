# Task 1.10: Music Library

## Meta
- **ID**: 1.10
- **Phase**: 1
- **Status**: planned
- **Priority**: low
- **Assignee**: AI

## Paths
- `app/api/music.py`
- `frontend/pages/music_library.html`
- `frontend/static/js/music_library.js`

## Acceptance Criteria
- [ ] User can upload royalty-free MP3/WAV tracks
- [ ] Audio wave preview and volume leveling
- [ ] Selection of background track for auto-ducking during speech in Step 4/5

## Forbidden Scope
- No saving audio files outside `data/music/`

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
