# Task 57.3 — AI topic ideas

Status: planned 2026-10-21.

## Paths
- backend/ai/prompts/source/topic_ideas.txt (new), backend/ai/llm/prompt_loader.py (`render_source_prompt`), backend/content/source_service.py (new), backend/schemas/project.py (`TopicIdeasRequest`)
- backend/api/projects.py (`POST /api/projects/topic-ideas`)
- tests/test_topic_ideas.py (new)

## File-Level Plan
Request: `presentation_mode`, `cefr_level`, optional `hint` (≤ 200 chars), optional `genre`. The prompt states the audience (Vietnamese learners), the video type (a conversation between two characters, or one presenter explaining a field, product or subject), the level, the hint, and the exact output: `{"ideas": [{"name": "...", "topic": "...", "description": "..."}]}` with exactly 6 items and length limits. Called synchronously through the AI router like the channel plan; provider errors and unusable output become a readable validation error ("try again").

## Tests
Fake router: six ideas returned and trimmed; bad JSON → 422 with a clear message; the prompt contains the hint and the type.
