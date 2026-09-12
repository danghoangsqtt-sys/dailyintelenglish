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
- No saving audio files outside `data/music_library/` (corrected 2026-09-12 — the task
  card originally said `data/music/`, which was stale; `settings.DATA_DIR / "music_library"`
  is the actual project-wide convention already used by `app/api/music.py::_list_music_files`
  and `.gitignore`)

## Verification Commands
- `venv\Scripts\python -m pytest tests/`

## Implementation Notes (2026-09-12, proposed Sub-task 1.10a: ffmpeg-independent Music Library UI)

### Environment preflight and routing decision

- `ffmpeg -version` exited 1: `ffmpeg` is not present in this Codex sandbox's PATH.
- `python -c "import pydub"` exited 1 with `ModuleNotFoundError: No module named 'pydub'`.
- Per PM instruction, stop Sub-task 1.6b without implementing or simulating AudioService and
  propose this ffmpeg-independent Task 1.10 slice instead.
- Storage will follow the PM assignment and existing application convention:
  `settings.DATA_DIR / "music_library"`. This conflicts with the stale Forbidden Scope text
  above (`data/music/`); no files will be written outside `data/music_library/`.

### Proposed scope and expected result

Deliver an accessible Music Library page that lists the current library, previews tracks in
native browser audio players, uploads new MP3/WAV files, and deletes a selected track after
confirmation. All async UI actions use in-flight locks/disabled controls, and user-visible
errors remain friendly while raw details are logged only to the console.

The requested upload and preview behavior cannot work with only the existing collection GET
and proposed DELETE route. The plan therefore asks PM to approve two necessary API additions:
`POST /api/music` for multipart upload and `GET /api/music/{filename}` for safe audio streaming.

### Proposed `allowed_files`

- `.viepilot/phases/01-full-feature-build/tasks/task-1.10.md` — this plan/evidence area only;
  do not change task status or acceptance checkboxes.
- `app/api/music.py` — retain `GET /api/music`; add multipart `POST /api/music`, safe
  `GET /api/music/{filename}` preview/download, and requested
  `DELETE /api/music/{filename}`. Accept uploads only for non-empty `.mp3`/`.wav` files,
  reject unsafe filenames/path traversal, stream writes asynchronously into
  `data/music_library/`, clean partial files on failure, and keep responses in the standard
  envelope (except the audio `FileResponse`).
- `app/main.py` — serve `frontend/pages/music_library.html` at `/music`.
- `frontend/static/js/api.js` — centralize list/upload/delete calls and support `FormData`
  without forcing a JSON `Content-Type` header.
- `frontend/pages/music_library.html` — themed page with drag/drop plus file picker,
  upload state, track list, native audio preview, delete controls, empty state, and friendly
  error/status regions; reuse the shared stylesheet and theme script.
- `frontend/static/js/music_library.js` — render escaped filenames and sizes; serialize
  uploads with a double-submit lock; lock each delete action, require confirmation, refresh
  state after mutations, encode filenames in URLs, and never expose raw API errors in the UI.
- `tests/test_music_api.py` — API coverage for list, MP3/WAV upload, unsupported/empty/unsafe
  input, preview bytes/media type, delete, missing files, and confinement to the configured
  temporary music-library directory.
- `tests/test_music_library_browser.py` — real-browser coverage for happy path, friendly
  error path, reload persistence, upload/delete confirmation, audio-player URL, and rapid
  repeated-action locking.

No AudioService, pydub/ffmpeg logic, loudness normalization, background-music selection,
Step 4 integration, shared CSS changes, dependency installation, or documentation/status
updates are included in this slice.

### Risks and limits

- The task card's broader acceptance criteria mention volume leveling and Step 4/5 track
  selection; both depend on later audio workflow work and are outside this PM-directed
  ffmpeg-independent slice.
- The architecture currently documents collection GET and item DELETE only. POST upload and
  item GET are minimal additions required by the ROADMAP's upload/preview acceptance behavior.
- Extension validation cannot prove a file is genuinely royalty-free or fully decode audio;
  without ffmpeg/pydub this slice can enforce filename, extension, non-empty content, and safe
  storage only.
- Browser E2E requires the repository's installed Playwright Chromium; if unavailable, report
  the exact command failure rather than claiming browser verification.

### Verification commands to run after implementation

- `venv\Scripts\python -m pytest tests/test_music_api.py -q`
- `venv\Scripts\python -m pytest tests/test_music_library_browser.py -q`
- `venv\Scripts\python -m pytest tests/ -q`
- `venv\Scripts\python -m ruff check app/ tests/`
- `node --check frontend/static/js/api.js`
- `node --check frontend/static/js/music_library.js`
- `git diff --check`

Implementation remains paused pending explicit PM confirmation of this plan and expanded
`allowed_files` list.
