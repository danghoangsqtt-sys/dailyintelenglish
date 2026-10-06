# Task 26.3: Dashboard polish (doc-first card)

## Paths

- `app/services/project_service.py` (`list_projects` + `preview_url`)
- `frontend/static/js/dashboard.js`
- `frontend/pages/dashboard.html`
- `frontend/static/css/style.css`
- `tests/test_dashboard_preview.py` (new)

## File-Level Plan

1. **`list_projects` adds `preview_url`** (additive). It is the first available of:
   - the selected thumbnail (16x9, by its stored file extension);
   - the first complete shot (final image);
   - null.
2. **Project cards:**
   - the real preview image (`object-fit: cover`); without one, a brand-gradient tile with the DI
     mark and the topic;
   - a "Step x of 7" progress bar from the status;
   - hover elevation.
3. **Hero:**
   - English, like every other page: "Create English listening episodes with AI" plus a one-line
     subtitle and a "New project" CTA (same `#new-project-btn` id);
   - a soft brand-gradient panel.
4. Filter chips and search keep their ids.

## Verification

- An API test for `preview_url` (none / shot / selected thumbnail wins).
- The dashboard browser tests pass.
- Before/after screenshots.
- The full suite is green.
