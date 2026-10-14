# PHASE-STATE — Phase 41: Project output folder (D120)

- **Status:** complete 2026-10-14; implementation, sandbox run and tests are recorded below. Phase 45 closes the later audit gaps in script/learning auto-export and copy concurrency. Opened 2026-10-14. Owner: "khi bắt đầu thực hiện video mới, người dùng có thể chọn thư mục lưu cho dự án
  video; video tạo ra sẽ lưu vào thư mục đó kèm nội dung đi kèm" + "người dùng có thể chọn các thành phần sẽ xuất ra thay vì
  nhận cả đống file không dùng đến". Choices: automatic on every new version; the owner ticks the components.

| Task | Description | Status |
|---|---|---|
| 41.1 | Migration 025: `project_exports` table; settings API and folder validation | done |
| 41.2 | `backend/content/export_service.py`: idempotent copy of selected components (Phase 45 fills script/learning edit hooks) | done |
| 41.3 | Step 1 and Step 7 folder UI, picker and component choices | done |
| 41.4 | Tests and real sandbox run | done |

## Implementation notes (before coding)

- Components (keys → files in the folder): `video` → `video.mp4` + `subtitles.srt`; `video_vertical` → `video_vertical.mp4`;
  `thumbnail` → `thumbnail.png` (+ `thumbnail_9x16.png` when present); `youtube` → `youtube/metadata.txt` (titles,
  description, tags, hashtags), `youtube/pinned_comment.txt`; `shorts` → `shorts/clip-N.mp4`, `clip-N-cover.jpg`,
  `clip-N.txt` (Shorts title/description + TikTok caption); `audio` → `audio.mp3`; `script` → `script.txt` (speaker: line);
  `learning` → `learning_pack.txt` (reuses the YouTube export's transcript+learning text). Default ticks: video, thumbnail,
  youtube.
- Copies only when the source is newer or a different size; files of unticked components are left alone (never deleted).
  An export error is logged and reported on the next status read; it never fails the render that triggered it.
- The folder picker runs `tkinter.filedialog.askdirectory` in a worker thread on the server (the app is local); if Tk is
  missing (packaged exe) the UI keeps the typed path.
- Existing projects have no folder (nothing exported) until one is set in Step 1 (edit) or Step 7.

## As built (2026-10-14)

- Migration 025 `project_exports`; `backend/content/export_service.py` (settings, plan, idempotent copy, text files,
  `sync_quietly` hook, native folder dialog); `backend/api/export.py` (GET/PUT/DELETE `/api/projects/{id}/export`,
  `POST …/export/sync`, `POST …/export/open`, `POST /api/system/choose-folder`).
- Automatic copy after: video render, vertical render, Shorts clip render, thumbnail favourite, YouTube package, audio mix.
- UI: shared `frontend/static/js/project_folder.js`; Step 1 "Save to folder (optional)"; Step 7 "Project folder" panel.
- Sandbox run: a real project exported 11 files (video, subtitles, vertical, thumbnails, YouTube texts, clip + cover +
  captions, script, learning pack) and nothing unticked. Tests: `tests/test_phase41_export.py` (4).
