# PLAN — Phase 57: Step 1 video type, AI topic ideas, video from your material (ENH-039)

Status: execution_authorized 2026-10-21 — owner approved the Step 1 layout and answered the three design questions (ideas from type + level + hint; dialogue "word for word" or "AI rewrite" chosen each time; photos read by the cloud AI).

| Task | Scope | Depends on |
|---|---|---|
| [57.1](tasks/task-57.1.md) | Project source material: migration 030 (`source_kind`, `source_text`, `source_use`), `ScriptConfig` validation, saved with the project; a word-for-word dialogue becomes the script at creation | — |
| [57.2](tasks/task-57.2.md) | Script prompts use the material: outline/section get a "Source material" block (dialogue → keep its situation, ideas and key words; vocabulary → use every listed word); missing vocabulary words are a soft warning | 57.1 |
| [57.3](tasks/task-57.3.md) | AI topic ideas: `POST /api/projects/topic-ideas` with a prompt that states the exact JSON shape (BUG-050 lesson) | — |
| [57.4](tasks/task-57.4.md) | Read a photo: `GenerationRequest.images`; the OpenAI-compatible provider sends image parts, local providers refuse; `POST /api/projects/read-image` returns the text | — |
| [57.5](tasks/task-57.5.md) | Step 1 UI: type cards, the three content sources, idea cards, material box (paste / photo / word-for-word switch) | 57.1–57.4 |
| [57.6](tasks/task-57.6.md) | Verification: full pytest + renderer, screenshots | all |

One session, sequential. No version bump; CHANGELOG `[Unreleased]`.

Out of bounds: Phase 55 Solo files (`backend/library/explainer_*.py`, `renderer/src/Solo*.tsx`, `frontend/static/js/explainer_editor.js`). The Solo script still comes from the shared script pipeline, so the material reaches Solo talks through 57.2 without touching them.

Compatibility: existing projects have no material (`source_kind` = ''), so their prompts and config hashes are unchanged except for the new empty keys in the project dict — a re-generation of an old project is not blocked (the hash only gates duplicate jobs).

Risks: word-for-word parsing of free text ("A: …", "Anna: …", lines without a label); more than two labels is refused with a clear message. Photo reading needs a cloud AI with vision (Gemini/OpenRouter vision models); a local-only setup gets a clear error and can still paste text.
