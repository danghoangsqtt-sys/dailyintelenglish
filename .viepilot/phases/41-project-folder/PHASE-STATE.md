# PHASE-STATE — Phase 41: Project output folder (D120)

- **Status:** in progress 2026-10-14. Owner: "khi bắt đầu thực hiện video mới, người dùng có thể chọn thư mục lưu cho dự án
  video; video tạo ra sẽ lưu vào thư mục đó kèm nội dung đi kèm" + "người dùng có thể chọn các thành phần sẽ xuất ra thay vì
  nhận cả đống file không dùng đến". Choices: automatic on every new version; the owner ticks the components.

| Task | Description | Status |
|---|---|---|
| 41.1 | Migration 025: `projects.output_dir`, `projects.export_items` (JSON); schema + API fields; validation (absolute, creatable, writable) | in_progress |
| 41.2 | `backend/content/export_service.py`: `sync(project_id)` copies the ticked components that exist into the folder (idempotent); hooks after video/vertical/clip render, thumbnail favourite, YouTube package, audio, learning | in_progress |
| 41.3 | Step 1 "Save to folder": path + "Choose folder…" (native Windows dialog from the local server, typed path as fallback) + component checkboxes; Step 7 panel: folder, components, "Open folder", "Save now" | in_progress |
| 41.4 | Tests and a real run | in_progress |

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
