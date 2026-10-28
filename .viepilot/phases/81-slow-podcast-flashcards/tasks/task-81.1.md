# Task 81.1 — Backend for slowpod / flashcards

## Objective
New projects of style `slowpod` or `flashcards` get the right script, data and render props, and run through Automation and the Shorts batch without a visual plan.

## Paths
backend/schemas/project.py, backend/content/script_service.py, backend/content/script_pipeline.py, backend/ai/prompts/script/solo_explainer.txt, backend/ai/prompts/script/section.txt, backend/content/learning_pipeline.py, backend/media/video_renderer_remotion.py, backend/automation/runner.py, backend/channel/batch_service.py, backend/channel/channel_service.py, backend/library/explainer_service.py, tests/test_slowpod_flashcards.py

## File-Level Plan
- project.py: add both to `SOLO_SHORT_STYLES` / `ExplainerStyle`; `LINE_DRAWN_STYLES = ("chat", "wyr", "slowpod", "flashcards")`.
- script_service.py / pipeline notes model: optional `translation_vi: str = ""`.
- solo_explainer.txt: SHORT blocks for `slowpod` (8–10 short sentences, one per line, greeting line, follow line, `translation_vi` per line) and `flashcards` (cover line, "<word>. <word>." per card, 8–10 cards, follow line; owner list order when given).
- script_pipeline.py: no paragraph split for `flashcards`; slowpod lines keep one sentence each.
- learning_pipeline.py: for `flashcards`, required vocabulary = words parsed from card lines.
- channel_service / project creation: narrator speed 0.8 for a new `slowpod` project (owner can change in Step 4).
- video_renderer_remotion.py: `shortStyle` for the line-drawn styles; each props line gets `translation` from its script line notes.
- runner.py `has_visual_plan`: true for line-drawn styles.
- batch_service.py: templates + rules for both.

## Verification
`pytest tests/test_slowpod_flashcards.py tests/test_batch_news.py tests/test_automation.py tests/test_short_script_lines.py -q`; Ruff.
