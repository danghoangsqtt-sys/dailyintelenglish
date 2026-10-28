# Phase 84 — Automatic videos, long and Short, at the best quality (2026-10-28)

Owner (2026-10-28): "nghiên cứu lại luồng làm việc và cơ chế tạo video, vì tôi cũng sẽ cần tính năng TỰ ĐỘNG tạo video
áp dụng cho cả video dài và short. tiến hành sửa lỗi và nghiên cứu lại quy trình sao cho chất lượng nội dung đạt cao nhất".
Owner choices (same day): facts checked by an AI pass that stops only on doubtful claims; every automatic script gets an
editor review and one rewrite when it falls short; long 16:9 videos render at 1920x1080.

## What the Phase 83 run showed (17 videos through "Make videos now")

| Stop | Kind | Cause |
|---|---|---|
| visual plan: "outtro-1 overlaps the preceding script span" | Listen Short | the AI writes each segment's start/end word anchors; one off-by-a-word anchor fails the whole plan (no repair before `validate_coverage`) |
| visual plan: "idea-4 leaves a gap before ..." | Solo presenter 16:9 | same |
| script: "total word count 140 is outside ±10% of target 119" | Vox Short | ±10 % of a ~120-word Short is ±12 words; two attempts and the length repair missed it |
| visual plan: "review its knowledge claims" | News Short, VOX 16:9 | by design since Phase 66: only a person could clear the fact flags |
| audio: ffmpeg exit 0xC0000142 | Mistakes Short | a one-off crash; the retry made the video; the Producer never retries a non-AI step |
| export: 'NoneType' object is not subscriptable | 5 Shorts | fixed in Phase 83 (`80f1c99`) |
| clips not in the folder | clips | fixed in Phase 83 (clips in the default export items) |

Quality: scripts pass only mechanical checks (length, format, repetition, balance); nothing judges the hook, the one
message, the examples or the ending. Long videos are 1280x720.

## Tasks

1. **84.1 Plan boundaries repaired** — before checking coverage, the AI's segments are snapped to one another: each
   segment starts where the previous ends, the first at the first word, the last ends at the last word; a segment left
   empty is merged away; line ids and gestures follow. Path: `backend/library/explainer_timing.py`
   (`ScriptIndex.snap`), `backend/library/explainer_service.py` (`_proposed_segments`), tests.
2. **84.2 Short script length** — a Short (≤ 1 min) is checked at ±20 % (`SCRIPT_SHORT_WORD_TOLERANCE`, a new constant;
   the pinned ±10 % / ±15 % stay for long scripts); the ≤ 60 s rule is unchanged. Path: `backend/core/constants.py`,
   `backend/content/script_pipeline.py`, tests.
3. **84.3 The Producer tries again** — a failed audio, visual-plan, video or thumbnail step is run once more before the
   episode stops (an AI step already gets two attempts). Path: `backend/automation/runner.py`, tests.
4. **84.4 AI fact check** — `POST /api/projects/{id}/explainer-plan/fact-check`: the AI reads the script, the owner's
   material and each segment's on-screen text and answers per segment `ok` or `doubtful` with a reason. In automatic
   mode the News / VOX / long presenter plan is approved when every segment is `ok` (flags cleared exactly as on Step 5,
   the verdicts kept in the plan's notes); any `doubtful` segment stops the episode with its reason. A VOX chart or map
   using numbers or places the narration never says becomes a text card of the narration (never invented data). Paths:
   `backend/library/explainer_service.py`, `backend/api/explainer.py`, `backend/ai/prompts/explainer/fact_check.txt`,
   `backend/automation/runner.py`, tests.
5. **84.5 Editor pass** — after an automatic script is written (not flashcard decks), the AI scores it 1-5 on: hook in
   the first line, one clear message, concrete examples, natural spoken English, fits the CEFR level, ending that
   answers the hook (Shorts) or wraps up (long). Any score under 4 → one rewrite with the editor's notes, kept only when
   it passes every existing script check; otherwise the original stays. The review is saved (`script_reviews`, migration
   041) and shown on Step 2. Paths: `backend/content/script_editor.py` (new), `backend/ai/prompts/script/editor_review.txt`,
   `backend/ai/prompts/script/editor_rewrite.txt`, `backend/api/projects.py` or script API, `backend/automation/runner.py`,
   `backend/db/migrations/041_script_reviews.sql`, `frontend/static/js/step2*.js`, `i18n_vi.js`, tests.
6. **84.6 Long videos at 1080p** — the 16:9 render uses Remotion `--scale=1.5` (the 1280x720 layout drawn at 1920x1080,
   sharp text); 9:16 stays 1080x1920. Path: `backend/media/video_renderer_remotion.py`, tests.
7. **84.7 Verify** — full pytest; build and install (backup kept, with the owner's go-ahead); sync the Phase 83 folders;
   then one automatic video of every kind (14 Shorts, 3 long, clips) into `D:\Videos`, each checked: finished or why it
   stopped, length, size, a frame, the editor scores. Records.
