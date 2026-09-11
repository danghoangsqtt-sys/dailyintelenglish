# Task 1.7: Step 5 — Video Studio

## Meta
- **ID**: 1.7
- **Phase**: 1
- **Status**: planned
- **Priority**: medium
- **Assignee**: AI

## Paths
- `app/services/video_service.py`
- `app/api/video.py`
- `frontend/pages/step5_video.html`
- `frontend/static/js/step5_video.js`

## Acceptance Criteria
- [ ] Level 2 video: Background video loop + burned-in subtitles + SRT export
- [ ] Level 3 video: LivePortrait lips-sync on portrait avatar
- [ ] Safe fallback from Level 3 to Level 2 on error/VRAM limit
- [ ] Video Studio UI with preview player and export options

## Forbidden Scope
- No synchronous ffmpeg calls on event loop
- No failure to generate fallback when lips-sync fails

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
