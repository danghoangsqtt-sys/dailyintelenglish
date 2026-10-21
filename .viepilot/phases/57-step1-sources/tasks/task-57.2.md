# Task 57.2 — Script prompts use the material

Status: planned 2026-10-21.

## Paths
- backend/ai/prompts/script/outline.txt, backend/ai/prompts/script/section.txt
- backend/channel/dashboard_service.py + frontend/static/js/step_guide.js (missing words on the Step 2 bar)
- backend/content/script_pipeline.py (pass `source_kind`/`source_text`/vocabulary words; soft warning in `validate_global`)
- tests/test_project_source.py

## File-Level Plan
When a project has material, both prompts get a "## Source material" block. Dialogue + rewrite: "Base the episode on this dialogue: keep its situation, main ideas and useful expressions; rewrite it for CEFR X, the target length and the speakers above (as a solo talk for Solo)". Vocabulary: the parsed word list (one item per line or comma separated, ≤ 60 items) with "use every one of these words or phrases naturally at least once across the episode; the outline spreads them over the sections" and in each section "use the ones that fit this section". `validate_global` adds a warning listing words never used (no hard failure, so a long list cannot block a script); because the pipeline does not surface its warnings, the progress API also returns `missing_vocabulary` and the Step 2 bar lists those words. Verbatim projects never call the AI for the whole script.

## Tests
Rendered prompts contain the block only when material exists; the vocabulary warning lists missing words.
