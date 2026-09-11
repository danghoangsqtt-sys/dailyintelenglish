# Task 1.9: Step 7 — YouTube Package

## Meta
- **ID**: 1.9
- **Phase**: 1
- **Status**: planned
- **Priority**: medium
- **Assignee**: AI

## Paths
- `app/services/youtube_service.py`
- `app/api/youtube.py`
- `frontend/pages/step7_youtube.html`
- `frontend/static/js/step7_youtube.js`

## Acceptance Criteria
- [ ] Title options (3 variants: click-worthy, educational, SEO)
- [ ] Description with auto-generated timestamps/chapters
- [ ] Tag generator (comma-separated, max 500 chars)
- [ ] Full package download (.zip containing video, thumbnail, SRT, metadata.txt)

## Forbidden Scope
- No auto-publishing to YouTube without explicit user export/consent

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
