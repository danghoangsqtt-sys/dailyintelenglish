# Task 1.8: Step 6 — Thumbnail Generator

## Meta
- **ID**: 1.8
- **Phase**: 1
- **Status**: planned
- **Priority**: medium
- **Assignee**: AI

## Paths
- `app/services/thumbnail_service.py`
- `app/api/thumbnail.py`
- `frontend/pages/step6_thumbnail.html`
- `frontend/static/js/step6_thumbnail.js`

## Acceptance Criteria
- [ ] 5 Pillow thumbnail templates (minimal, bold, split, dark, educational)
- [ ] AI prompt generation for headline & color palette via Gemini
- [ ] Interactive manual text editor and layout tweaks
- [ ] Export 1280x720 PNG/JPG

## Forbidden Scope
- No blocking filesystem operations
- No hardcoded font paths that fail cross-platform

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
