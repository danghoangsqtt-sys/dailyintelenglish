# Phase 80 — Shorts batch rework: video types, real content, short brand, make now + results

Owner request (2026-10-26, Vietnamese original): "Nội dung chức năng short hàng loạt không phù hợp và thiếu đi các dạng lựa chọn loại video, kết quả đầu ra của các dạng mẫu short cũng cho ra kết quả rất nghèo nàn không có nội dung gì cả, Cũng không có chỗ lưu video không biết kết quả short lưu ở đâu. các dạng mẫu word of the day hay các dạng nội dung sau khi tạo xong thì xem video chả có gì, khởi đầu và kết thúc là đã gần hết nội dung chính của video".

Owner decisions (AskUserQuestion, 2026-10-26):
- Short brand: **very short** — no intro slide, content from the first second, a small logo in the corner throughout, a ~2 s "Follow" end card.
- Add the existing video types to the batch: **2-character conversation (talking sprites), Solo presenter, Vox** — as Shorts (9:16, ≤ 1 min). No new modes.
- **"Make videos now"** button: runs script → voice → visual plan → video for the whole batch with per-video progress, plays/downloads on the page and shows where each file is saved; night Automation stays available.

## Evidence (sandbox copy of the owner DB, real AI + Edge voice + render)

"Word of the day" Short `Stop Saying 'I Think' in Meetings` made through the Automation steps: 52.9 s video, speech 36.2 s → **intro + outro 16.7 s (32 %)**. The AI wrote **one 36 s paragraph** (prompt asks for pronunciation, two examples, memory tip; nothing enforced it). The visual plan's "Why it works" card had three bullets; **LearnScene never draws text-card bullets**. Bottom half of the frame empty. The batch page's 9:16 preview is placeholder text by design. "Make the projects now" only creates empty draft projects (the owner's 5 Word-of-the-day projects have no script); nothing tells where videos go.

## Tasks

1. **80.1 Short brand** — Short projects (SHORT_STYLES, and conversation / presenter / vox with duration ≤ 1 min): `introSec = 0`, no greeting/farewell voices, a 2 s end card; a small logo watermark during the content. Paths: `backend/media/video_renderer_remotion.py` (`_add_brand`, a `short_video(project)` rule), `backend/media/brand_service.py`, `renderer/src/Brand.tsx`, `renderer/src/Episode.tsx` (+ Vitest), `tests/test_short_brand.py`.
2. **80.2 Short content** — (a) a Short script of one long paragraph is split into lines of one or two sentences (deterministic, after validation) and the Shorts prompt says not to greet; (b) LearnScene draws text-card bullets (and the other Short scenes are checked for dropped fields); (c) the frame's lower half gets the beat's support content (bullets/examples) instead of staying empty. Paths: `backend/content/script_pipeline.py` or the solo script service, `backend/ai/prompts/script/solo_explainer.txt`, `renderer/src/LearnScene.tsx` (+ Vitest), tests.
3. **80.3 Video types in the batch** — templates `conversation` (2 characters, talking sprites), `presenter`, `vox` beside the 9 Short templates; ideas prompt rules; series created as classic / solo presenter / solo vox with 0.75 min; vertical render for those Shorts (`video_service.generate_video` short rule). Paths: `backend/channel/batch_service.py`, `backend/media/video_service.py`, `backend/schemas/project.py` (helper), `frontend/static/js/shorts_batch.js`, `frontend/pages/shorts_batch.html`, `frontend/static/js/i18n_vi.js`, tests.
4. **80.4 Make now + results** — `POST /api/shorts-batch/series/{id}/make` starts an in-process maker (the Automation `Producer` steps per episode, one at a time), `GET /api/shorts-batch/series/{id}/results` returns each Short's step, status, error, video URL and saved folder; optional save folder for the batch (existing export settings). The page shows a results panel (9:16 player, download, folder) and survives reloads. Paths: `backend/channel/batch_maker.py` (new), `backend/api/shorts_batch.py`, `frontend/static/js/shorts_batch.js`, `frontend/pages/shorts_batch.html`, `frontend/static/js/api.js`, `frontend/static/js/i18n_vi.js`, tests.
5. **80.5 Verify** — make one real Short of each kind touched (Word of the day, conversation, presenter, vox) in the sandbox, frame sheets, related + full pytest, Vitest/tsc; records; rebuild/install only if the owner asks.

## Risks
- Existing long conversation projects are ≥ 5 min: the "≤ 1 min = Short" rule does not change them.
- The maker and the night Automation could pick the same project: the maker marks the episodes it is making and Automation skips a project whose steps are already done (it re-checks progress per step).
- AI quality still varies; the split/structure rules are deterministic so the video never shows one 36 s caption.
