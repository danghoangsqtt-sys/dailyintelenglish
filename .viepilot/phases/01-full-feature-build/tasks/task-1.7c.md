# Task 1.7c: Speaker Avatar Upload (Video Studio groundwork)

## Meta
- **ID**: 1.7c (sub-task of Task 1.7 — Step 5 Video Studio)
- **Phase**: 1
- **Status**: done (2026-09-13)
- **Priority**: low
- **Assignee**: PM (Claude, autonomous continuation — "tiếp tục")

## Context / Decision

Task 1.7's Acceptance Criteria item 2 (Level 3 LivePortrait lip-sync) was blocked on a real
user decision: where do per-speaker avatar images come from? On 2026-09-13 the user was
presented the tradeoffs via `AskUserQuestion` (upload vs. AI-generated likeness, and the
consent/rights implications of the latter) and chose: **"Chỉ build tính năng upload ảnh
avatar"** — build only the avatar-upload feature now; actual LivePortrait model integration
(the lip-sync inference pipeline) stays deferred as a separate, larger research+build effort,
same as the OmniVoice `ref_audio` decision recorded in TRACKER.md Known Issues.

This task is deliberately narrow: give each speaker a place to store/preview/remove an
uploaded portrait image, safely served. It does **not** attempt lip-sync, video generation
using the avatar, or any AI image generation — those remain out of scope until a future task
picks up real LivePortrait integration.

## Paths
- `app/core/constants.py`
- `app/core/exceptions.py`
- `app/services/avatar_service.py` (new)
- `app/services/project_service.py`
- `app/api/projects.py`
- `frontend/pages/step5_video.html`
- `frontend/static/js/step5_video.js`
- `frontend/static/js/api.js`
- `tests/test_avatar_service.py` (new)
- `tests/test_avatar_api.py` (new)
- `tests/test_video_studio_browser.py`

## Acceptance Criteria
- [x] `POST /api/projects/{project_id}/speakers/{speaker_id}/avatar` accepts a PNG/JPEG
  multipart upload, validated by magic bytes (not just extension) and size-limited, streamed
  to a temp file first (same chunked-write pattern as `app/api/music.py`'s `upload_music`).
  Storage is one mutable file per speaker (re-upload overwrites, unlike the music library's
  no-clobber collision naming) at `settings.DATA_DIR / "avatars" / {project_id} /
  {speaker_id}.{ext}`; a prior file with a different extension for the same speaker is
  removed so at most one avatar file exists per speaker at a time.
- [x] `GET /api/projects/{project_id}/speakers/{speaker_id}/avatar` streams the stored image
  with the correct `media_type`, resolving the path server-side and validating it stays
  under that project's avatar directory (mirrors `thumbnail_service.resolve_content_path`'s
  containment check) — 404 if the speaker has no avatar.
- [x] `DELETE /api/projects/{project_id}/speakers/{speaker_id}/avatar` removes the file (if
  any) and clears `speakers.avatar_image_path`.
- [x] `project_service.get_project` must never leak a raw filesystem path to API clients:
  each speaker's `avatar_image_path` in the response is either `null` or a served URL
  (`/api/projects/{id}/speakers/{id}/avatar`), never the on-disk path — the DB column itself
  keeps storing the real path.
- [x] Step 5 Video Studio UI (`/step5`) gets a small per-speaker avatar section: current
  avatar preview (or a placeholder), an upload control, and a remove button. This is
  additive to the existing background-template selector — no lip-sync/"Level 3" controls,
  no wiring into `POST .../video/generate` (that endpoint doesn't consume avatars yet and
  must not be changed by this task).
- [x] New tests: service-level (valid upload, magic-byte rejection, size-limit rejection,
  overwrite-replaces-old-file, resolve/404, delete) + API-level (multipart upload through
  the real route, GET serves correct bytes/media type, DELETE clears the DB column, 404s
  for unknown project/speaker) + a Playwright addition to
  `tests/test_video_studio_browser.py` covering upload → preview appears → remove → preview
  reverts to placeholder (network-mocked, same pattern as the rest of that file).

## Forbidden Scope
- No LivePortrait / lip-sync inference pipeline work of any kind.
- No AI-generated avatar images ("generate via external AI" convenience prompt-copy is a
  ROADMAP idea for a *later* task, not this one).
- No change to `POST .../video/generate` or `VideoService` — this task only stores/serves
  images, it does not make the video pipeline consume them yet.
- No raw filesystem path ever returned in an API response body.

## Verification Commands
- `venv\Scripts\python -m pytest tests/`
- `venv\Scripts\python -m ruff check app/ tests/`
- `node --check frontend/static/js/step5_video.js`
- `node --check frontend/static/js/api.js`

## Implementation Notes (2026-09-13)

Storage/serving pattern mirrors two existing precedents rather than inventing a third:
chunked upload with magic-byte validation before trusting the rest of the stream, first
chunk checked, size capped mid-stream (`app/api/music.py`'s `upload_music`); safe
server-side path resolution that never trusts a client-supplied path and stays contained
under a per-project directory before returning a `FileResponse`
(`thumbnail_service.resolve_content_path` / `app/api/thumbnail.py`'s `get_thumbnail_content`).

New constants (`app/core/constants.py`): `MAX_AVATAR_UPLOAD_MB = 8`,
`MAX_AVATAR_UPLOAD_BYTES`, `AVATAR_UPLOAD_CHUNK_BYTES = 1024 * 1024`,
`AVATAR_UPLOAD_EXTENSIONS = (".png", ".jpg", ".jpeg")`. New exception
`AvatarUploadTooLargeError(AppError)` with `status_code = 413`, same shape as
`MusicUploadTooLargeError`.

New `app/services/avatar_service.py`: `_avatar_dir(project_id)`, magic-byte validation for
PNG (`\x89PNG\r\n\x1a\n`) and JPEG (`\xff\xd8\xff`), `upload_avatar(db, project_id,
speaker_id, file) -> dict` (validates speaker exists via `project_service.get_project`,
streams+validates, replaces any existing file for that speaker id regardless of its old
extension, writes the new absolute path into `speakers.avatar_image_path` via a small
direct `UPDATE`, returns the refreshed project), `resolve_avatar_path(db, project_id,
speaker_id) -> Path` (reads the column, resolves+contains+`is_file()`-checks, raises
`NotFoundError` otherwise), `delete_avatar(db, project_id, speaker_id) -> dict` (unlinks if
present, clears the column, returns the refreshed project).

`project_service.get_project` change: after building `project["speakers"]`, replace each
speaker's `avatar_image_path` with `f"/api/projects/{project_id}/speakers/{speaker['id']}/avatar"`
when non-null, else leave it `None` — the only place a raw path could otherwise leak to a
client.

Routes added to `app/api/projects.py` right after the existing `update_speaker` PATCH route
(keeps all speaker-scoped mutations together): `POST`/`GET`/`DELETE` on
`/{project_id}/speakers/{speaker_id}/avatar`. `POST`/`DELETE` go through the existing
`_write_transaction` lock (same as `update_speaker`); `GET` is read-only, no lock needed.

Frontend: `step5_video.js` renders one small card per speaker (name + current avatar image
or a neutral placeholder + file input + remove button), calling three new `api.js` methods
(`uploadSpeakerAvatar`, `speakerAvatarUrl`, `deleteSpeakerAvatar`). Upload is `FormData`
+ `fetch` (not JSON), same as how `step4_tts.js`'s music upload — wait, Step 4 doesn't
upload music from the UI; this is a new "browser posts multipart" code path for this
codebase's frontend, so it's written plainly (no shared helper yet, nothing to reuse).

This card intentionally leaves `## Sub-task Result` unwritten until implementation is
verified — matching this project's doc-first + git-persistence gate discipline.

## Result (2026-09-13) — DONE

Delivered exactly the plan above. New `app/services/avatar_service.py` (magic-byte-checked
PNG/JPEG upload streamed through a temp file, single-mutable-file-per-speaker storage,
containment-checked serving, delete), new constants/exception, 3 new routes on
`app/api/projects.py` (`POST`/`GET`/`DELETE .../speakers/{id}/avatar`, the write routes going
through the same `_write_transaction` lock as `update_speaker`). `project_service.get_project`
now maps a non-null `avatar_image_path` to a served URL instead of ever returning the raw
on-disk path. `/step5` gained a "1. Speaker avatars (optional)" section (per-speaker preview
circle, Upload/Replace label, conditional Remove button); sections 2 and 3 renumbered.
`api.js` gained `uploadSpeakerAvatar`/`deleteSpeakerAvatar` (reusing the existing FormData
`request()` path — no changes needed to the shared client). 20 new backend tests
(`tests/test_avatar_service.py` — pure/validation helpers; `tests/test_avatar_api.py` —
real multipart upload through the FastAPI route, replace-overwrites-old-extension, path-leak
guard, 404s, size-limit) + 1 new Playwright test appended to
`tests/test_video_studio_browser.py` (upload → preview appears → remove → placeholder
returns).

Live-verified with real data end to end, not just mocked routes: a manual smoke script
created a real project via the real API, uploaded a real (magic-byte-valid) PNG through the
real multipart route, confirmed `GET` streamed back the exact same bytes with
`image/png`, confirmed the project's own `GET` never exposed the on-disk path (only the
served URL), then deleted it and confirmed a subsequent `GET` correctly 404s.

**Caught and fixed a real bug via a live Playwright screenshot**, not just the automated
suite: the first implementation set `.hidden` on the Remove `<button>` for speakers with no
avatar, but this codebase's `style.css` has no `[hidden]` rule anywhere, and `.btn {
display: inline-flex }` is an author-stylesheet rule — which the CSS cascade always
prioritizes over a same/lower-specificity user-agent rule like `[hidden] { display: none }`,
regardless of selector specificity or source order. The Remove button stayed visibly shown
for a speaker with no avatar. Confirmed visually via screenshot, fixed by not appending the
button to the DOM at all when there's nothing to remove (sidesteps the CSS conflict
entirely, rather than trying to out-specificity it), and re-verified with a second
screenshot. Worth noting for a future cleanup: `frontend/static/js/step6_thumbnail.js`'s
`retry-save-btn` has this exact same `.hidden`-on-a-`.btn` pattern and is very likely
affected too — not fixed here since it's outside this task's `## Paths`, but flagged in
TRACKER.md Known Issues.

### Verification output

`venv\Scripts\python -m pytest tests/test_avatar_service.py tests/test_avatar_api.py tests/test_video_studio_browser.py -q` (exit 0):
```
28 passed
```

`venv\Scripts\python -m pytest tests/ -q` (exit 0, full suite), run twice for confidence:
first run `2 failed, 472 passed` (both in `tests/test_learning_service.py`), second run
`1 failed, 473 passed` (a different test, `tests/test_script_service.py`) — 474 total both
times, and every failure passed instantly in isolation. This is the documented Gemini
retry/backoff full-suite timing flake (TRACKER.md Known Issues), not a real regression, and
none of the failing tests touch this task's files.

`venv\Scripts\python -m ruff check app/ tests/` (exit 0): `All checks passed!`

`node --check` on `step5_video.js`, `api.js`: both exit 0.

Real end-to-end smoke test (see above) and two live Playwright screenshots (before/after the
Remove-button fix) visually confirmed correct behavior.
