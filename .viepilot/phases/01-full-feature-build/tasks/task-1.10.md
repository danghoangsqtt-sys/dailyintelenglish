# Task 1.10: Music Library

## Meta
- **ID**: 1.10
- **Phase**: 1
- **Status**: in_progress (Sub-task 1.10a done)
- **Priority**: low
- **Assignee**: AI (Codex)

## Paths
- `app/api/music.py`
- `frontend/pages/music_library.html`
- `frontend/static/js/music_library.js`

## Acceptance Criteria
- [x] User can upload royalty-free MP3/WAV tracks — upload/list/preview/delete UI at `/music`, magic-byte + size validated (royalty-free-ness itself is a content/licensing judgment, not a code check)
- [ ] Audio wave preview and volume leveling — native browser `<audio>` preview done; waveform visualization and loudness leveling need ffmpeg/pydub, deferred to Sub-task 1.10b
- [ ] Selection of background track for auto-ducking during speech in Step 4/5 — deferred to Sub-task 1.10b alongside AudioService

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
  `settings.DATA_DIR / "music_library"`; no files will be written outside that directory.

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
  reject unsafe filenames/path traversal, enforce the configured 50 MB limit while streaming,
  verify lightweight format signatures (WAV `RIFF`/`WAVE`; MP3 `ID3` or an approved frame-sync
  prefix), stream writes asynchronously into `data/music_library/`, clean partial files on
  failure, and keep responses in the standard envelope (except the audio `FileResponse`).
- `app/core/constants.py` — add `MAX_MUSIC_UPLOAD_MB = 50` per CR-02; no unrelated constants
  changes.
- `app/main.py` — serve `frontend/pages/music_library.html` at `/music`.
- `.viepilot/ARCHITECTURE.md` — update only the Music Library endpoint list with
  `POST /api/music` and `GET /api/music/{filename}` so documentation matches the API.
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

Duplicate uploads will use the UX-friendly option (a): preserve the existing file and assign
the new upload the first available `name (1).ext`, `name (2).ext`, and so on. Final placement
will be atomic/no-clobber so concurrent same-name uploads cannot overwrite existing data.

No AudioService, pydub/ffmpeg logic, loudness normalization, background-music selection,
Step 4 integration, shared CSS changes, dependency installation, status updates, or
documentation changes beyond the approved ARCHITECTURE endpoint sync are included.

### Risks and limits

- The task card's broader acceptance criteria mention volume leveling and Step 4/5 track
  selection; both depend on later audio workflow work and are outside this PM-directed
  ffmpeg-independent slice.
- The architecture currently documents collection GET and item DELETE only. POST upload and
  item GET are minimal additions required by the ROADMAP's upload/preview acceptance behavior.
- Lightweight magic-byte validation detects obvious extension spoofing but cannot prove a file
  is royalty-free or fully decodable; full media decoding remains unavailable without
  ffmpeg/pydub.
- Uploads larger than `MAX_MUSIC_UPLOAD_MB = 50` are rejected with a friendly 413 response,
  and their partial temporary files are removed.
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

PM approved this plan and the expanded `allowed_files` list on 2026-09-12. Implementation
evidence follows; PM acceptance remains pending.

## Implementer Evidence (Awaiting PM Acceptance)

### Delivered behavior

- Added multipart MP3/WAV upload, safe browser streaming, collection listing, and deletion.
- Enforced a 50 MB streamed-upload limit with 413 response and partial-file cleanup.
- Enforced WAV (`RIFF`/`WAVE`) and MP3 (`ID3` or approved frame sync) magic-byte checks.
- Preserved existing files on duplicate names via atomic `name (1).ext` allocation; a
  concurrent-placement regression test verifies that both uploads survive.
- Added `/music` UI with drag/drop/file picker, native audio preview, empty/loading/status
  states, confirm-gated delete, friendly errors, upload serialization, and per-delete locks.
- Synchronized the Music Library endpoint list in `ARCHITECTURE.md`.

### Files changed

- `.viepilot/ARCHITECTURE.md`
- `.viepilot/phases/01-full-feature-build/tasks/task-1.10.md`
- `app/api/music.py`
- `app/core/constants.py`
- `app/main.py`
- `frontend/static/js/api.js`
- `frontend/pages/music_library.html`
- `frontend/static/js/music_library.js`
- `tests/test_music_api.py`
- `tests/test_music_library_browser.py`

No task status, acceptance checkbox, TRACKER, PHASE-STATE, commit, tag, or remote state was
changed by the implementer.

### Verification output

`venv\Scripts\python -m pytest tests/test_music_api.py -q` (exit 0):

```text
...............                                                          [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
15 passed, 2 warnings in 2.95s
```

`venv\Scripts\python -m pytest tests/test_music_library_browser.py -q` (exit 0):

```text
....                                                                     [100%]
4 passed in 15.80s
```

`venv\Scripts\python -m pytest tests/ -q` (exit 0):

```text
........................................................................ [ 26%]
........................................................................ [ 53%]
........................................................................ [ 79%]
.......................................................                  [100%]
============================== warnings summary ===============================
venv\Lib\site-packages\fastapi\testclient.py:1
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\fastapi\testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

venv\Lib\site-packages\starlette\testclient.py:53
  D:\DataAdmin\Daily_Intel_English\venv\Lib\site-packages\starlette\testclient.py:53: DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.
    _PortalFactoryType = Callable[[], AbstractContextManager[anyio.abc.BlockingPortal]]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
271 passed, 2 warnings in 51.15s
```

`venv\Scripts\python -m ruff check app/ tests/` (exit 0):

```text
All checks passed!
```

`node --check frontend/static/js/api.js` (exit 0):

```text
EXIT_CODE=0
```

`node --check frontend/static/js/music_library.js` (exit 0):

```text
EXIT_CODE=0
```

`git diff --check` (exit 0):

```text
warning: in the working copy of '.viepilot/ARCHITECTURE.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of '.viepilot/phases/01-full-feature-build/tasks/task-1.10.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/api/music.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/core/constants.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'app/main.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'frontend/static/js/api.js', LF will be replaced by CRLF the next time Git touches it
EXIT_CODE=0
```

### Remaining limits and risks

- This ffmpeg-independent slice does not implement loudness leveling, background-track
  selection, Step 4/5 integration, or full audio decoding.
- Magic-byte checks reject obvious spoofing but do not prove media decodability or licensing.
- The two warnings are existing third-party FastAPI/Starlette deprecations; no project test
  warning or failure was suppressed.

## PM Acceptance (2026-09-12)

Independently re-verified, not just trusted — re-ran every claimed command myself:
- `pytest tests/test_music_api.py tests/test_music_library_browser.py -q`: 19 passed (matches).
- `pytest tests/ -q`: 270 passed + 1 unrelated failure (`test_script_service.py::test_generate_script_backoff_sequence_is_1s_2s_4s`, a pre-existing retry/backoff test, confirmed passes in isolation — same flaky-under-full-suite pattern as `test_generate_script_exhausts_retries_raises` seen earlier this session; tracked separately, not caused by this change and not in this task's `allowed_files`).
- `ruff check app/ tests/`: clean (matches).
- `node --check` on both JS files: clean (matches).
- `grep "Music Library" .viepilot/ARCHITECTURE.md`: confirms `POST /api/music` and `GET /api/music/{filename}` are now documented alongside the existing routes (matches).

Read the actual diff, not just the report:
- `app/api/music.py`: path traversal blocked on all three mutating/reading routes via a shared `_validate_filename` (rejects `..`, `/`, `\`, and any filename whose `Path(...).name` doesn't round-trip); 50 MB limit enforced while streaming (not after buffering the whole file); magic-byte check runs on the first chunk before any bytes are trusted; `_place_without_overwrite` uses `os.link` + `FileExistsError` retry, which is atomic at the OS level (no check-then-write race) — verified by `test_atomic_placement_preserves_concurrent_same_name_uploads`, a real `ThreadPoolExecutor`/`Barrier` concurrency test, not just a sequential-call test.
- `frontend/static/js/music_library.js`: filenames rendered via `textContent` (no innerHTML/XSS risk); double-submit lock on upload and per-file lock on delete; friendly error text confirmed by `test_invalid_magic_bytes_show_friendly_error_only` to never leak the backend's raw validation message.
- `frontend/static/js/api.js`: `FormData` bodies correctly skip the forced `Content-Type: application/json` header without touching any existing JSON call.

All 4 PM-requested additions from the plan-review round are present and correctly implemented: upload size limit, no-clobber duplicate naming (with real concurrency proof), magic-byte validation, and `ARCHITECTURE.md` sync.

**Accepted.** This closes Sub-task 1.10a (ffmpeg-independent slice) of Task 1.10. Full Task 1.10 stays `in_progress` — waveform visualization/volume leveling and Step 4/5 background-track selection remain blocked on `ffmpeg` + the `audioop-lts` fix (see TRACKER.md Known Issues) and are deferred to a future Sub-task 1.10b alongside AudioService.
