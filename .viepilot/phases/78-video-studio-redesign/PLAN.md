# Phase 78 — Step 5 Video studio redesign (storyboard previews, 9:16 repairs)

Owner request (2026-10-26, Vietnamese original): "chỉnh sửa thiết kế lại trang VIDEO trong quá trình sản xuất; và hệ thống hiện tại chỉ tạo ra video khổ 16:9 là chính còn nội dung 9:16 lỗi còn rất nhiều, tính năng duyệt storyboard cũng khá lỗi và khó tương tác, không có ảnh preview để đánh giá".

Delivered through `/vp-auto` from a side session. Doc-first: this plan and the task files are committed before any shipping file changes. Keep every existing feature and mode (no new modes); the Vietnamese UI copy goes through `frontend/static/js/i18n_vi.js` (pages stay English source text). Both 16:9 and 9:16 are first-class.

## What was reproduced (2026-10-26, sandbox copy of the owner DB, project "The Office Startup · Ep. 1")

Storyboard review (Step 5, "Storyboard"):
- S1 Labels and controls are siblings in one auto-fit grid (`.storyboard-fields`), so a label and its control land in different cells and rows ("Loại" over one column, its select in the next). Nothing lines up at any width.
- S2 The beat's script lines are hidden behind a collapsed `<details>`; the owner cannot judge a beat without opening each one.
- S3 No picture: the owner cannot see which scene plate, which characters or which illustration a beat will show.
- S4 Several labels are not translated ("Place", "Action", "Split at", "Merge with next", "On screen:", "Shows", "New place", "Search scenes" placeholder).
- S5 The sticky "Bước 5 — Video đã xong" bar (`.step-guide`, `position: sticky; bottom: 0` inside the scrolling stage) floats over beats and clip cards.

9:16 output (section "4. Shorts & TikTok (dọc)") — renderer stills rendered from the real props at 1080×1920, plus UI:
- V1 Renderer: a highlight clip's hook banner (y 330–630) covers the speaker chips (y 300–356); the vocabulary card already fades out under the hook, the chips do not.
- V2 Clip card: the reason text uses `.section-hint` (margin-top −8px) and is pulled up over the line-range inputs.
- V3 Clip card: "Not rendered yet" with no picture at all; nothing to judge before spending a render.
- V4 Clip card: `"aria-label"` is assigned as a DOM property (no attribute), so the inputs and text boxes have no accessible name and the i18n layer cannot translate them.
- V5 Clip card: Approve sends only `status` + `hook`; edited first/last line numbers are silently dropped unless Save was pressed first.
- V6 Clip card: the duration ("62.1 s") never follows edited line numbers; a 30–90 s violation only shows as a server error after Save.
- V7 Full vertical episode: only a download link, no player to watch the 9:16 result.
- V8 A conversation Short (chat / would-you-rather: the main video itself is 9:16 and ≤1 min) plays in the 16:9-sized result player at full width (a 1920 px tall frame), and still offers "Full episode, vertical" and 30–90 s highlight clips that cannot exist in a ≤60 s Short.

## Tasks

1. **78.1 Beat preview API** — `POST /api/projects/{id}/storyboard/preview`: for a list of (draft) beats returns per beat exactly what the talking-characters render will use: the scene plate shown during the beat (same carry-over rule as `_beat_scene_per_line`), the pair of characters on screen (same `sprite_segments` / `sprite_placement` / `sprite_mirrored`), each with its sprite picture for the beat's expression, and for an insert the matched library illustration (same `match_activity`) or the pending picture / missing state. Read-only; no files copied, no rendering. Tests.
2. **78.2 Storyboard review redesign** — beat cards with a preview frame (16:9 / 9:16 switch, composed from 78.1 with the renderer's geometry), the script lines visible, a labelled two-column form (label above control), clear Split / Merge row, toolbar with Propose / Save / Approve and a summary; preview refresh debounced on edits. Keep every id, name and behaviour the existing tests and owner use (`#beat-N-place`, `#beat-N-action`, `Merge with next`, summary texts). Vietnamese copy. Fix S5 for Step 5.
3. **78.3 9:16 repairs** — V1 renderer fix (+ Vitest), V2–V7 clip-card / vertical-section rebuild with a 9:16 sketch preview of the clip's opening beat (78.1 data, hook banner drawn on it), live duration check, Approve keeps edited lines, inline vertical player; V8: 9:16 result player for a vertical main video and the Shorts section explained instead of offering impossible clips.
4. **78.4 Page layout, verification, records** — Step 5 section headers/ordering polish, narrow-width layout, browser verification at desktop and 390 px, related pytest + full suite, renderer tests/typecheck, TRACKER / ROADMAP / HANDOFF / CHANGELOG / PHASE-STATE.

## Paths / allowed_files

- `backend/api/storyboard.py`, `backend/library/storyboard_preview.py` (new), `backend/schemas/storyboard.py`: preview endpoint and its read-only computation.
- `backend/media/video_renderer_remotion.py`: only if a pure helper must be shared with the preview (no behaviour change to renders).
- `frontend/pages/step5_video.html`, `frontend/static/js/storyboard.js`, `frontend/static/js/step5_shorts.js`, `frontend/static/js/step5_video.js`, `frontend/static/js/api.js`, `frontend/static/js/i18n_vi.js`, `frontend/static/css/style.css`: Step 5 UI.
- `frontend/static/js/beat_preview.js` (new): shared preview-frame drawing for beats and clips.
- `renderer/src/Episode.tsx`, `renderer/src/hook.test.ts`: V1.
- `tests/test_storyboard_preview.py` (new), `tests/test_storyboard_browser.py`, `tests/test_step5_shorts_after_render.py`, `tests/test_shorts.py`: coverage for the new endpoint and the changed UI.
- `.viepilot/phases/78-video-studio-redesign/**`, `.viepilot/TRACKER.md`, `.viepilot/ROADMAP.md`, `.viepilot/HANDOFF.json`, `CHANGELOG.md`: records.

## Risks and handling

- The preview must not drift from the render: it calls the renderer's own helpers (`_beat_scene_per_line`, `sprite_segments`, `sprite_placement`, `sprite_mirrored`, `match_activity`) rather than re-implementing them, and the browser geometry copies `spriteTimeline.canvasBox` / `safeZone.VERTICAL`. It is labelled a sketch ("phác thảo"), not the final frame.
- Draft beats can be invalid while editing: the preview endpoint validates line ranges only and reports a beat it cannot preview instead of failing the whole list.
- Owner data: browser verification uses a sandbox data directory (copied DB, read-only junctions to the libraries) on port 8030; the live installed app (port 8000) and `data/app.db` are not written.
- Phase 42 safe-zone geometry and its tests stay as they are; V1 only fades the chips during the hook.
- No package rebuild or install, no push unless the owner asks.

## Verification

- `pytest tests/test_storyboard_preview.py tests/test_storyboard_api.py tests/test_storyboard_browser.py tests/test_shorts.py tests/test_step5_shorts_after_render.py tests/test_video_studio_browser.py tests/test_video_shell_browser.py tests/test_responsive_layout_browser.py -q`
- `cd renderer && npx vitest run && npx tsc --noEmit`
- `node --check` on the changed JS; Ruff on the changed Python.
- Browser (sandbox): Step 5 of the Office Startup project at 1440 px and 390 px; beat previews in 16:9 and 9:16; edit → preview refresh; clip card sketch, live duration, approve-with-edited-lines.
- Full `pytest` before finishing.
