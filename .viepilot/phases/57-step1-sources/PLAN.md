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

## Amendment A — owner spec (docs/brainstorm/session-2026-10-21.md), relayed by the PM session 2026-10-21

The owner approved the brainstorm spec, which this phase implements as one phase (the spec's Phases 57–59). Added decisions:

1. **Solo sub-type** (57.1, 57.2, 57.5): `projects.explainer_subject` ('field' | 'product' | 'topic' | 'howto'; NULL for a conversation; existing Solo projects → 'topic'), in `ScriptConfig`/`ProjectUpdate`, copied by copy-settings. Default structure field→list, product→list, topic→why, howto→how (still editable). `solo_explainer.txt` gets a block per subject (field: what the job or field is, skills, a working day, field vocabulary, no invented salaries or statistics; product: what it is, the problem it solves, how to use it, balanced pros and cons, no invented specs or prices; howto: goal, ordered steps, a common mistake, recap; topic: unchanged). The Solo card shows the four sub-types; topic ideas take the sub-type. `storyboard/explainer.txt` stays with the PM session (Phase 55 owner).
2. **Topic ideas** (57.3): supersedes the earlier "no avoid list" answer — up to 60 recent project topics go into the prompt and near-duplicates (normalized match) are dropped; the AI is called only when the button is pressed.
3. **Word for word** (57.1): the stored lines must equal the input after whitespace/punctuation normalization (≥ 98 % similarity) or the project is refused with a clear message; more labels than the project's speakers (and never more than 4) are refused; Solo offers only "rewrite as a talk".
4. **Vocabulary** (57.1, 57.2): items `word`, `word - meaning`, `word: meaning`, de-duplicated, at most 80 (≤ 120 chars each). After generation the missing items are counted with a simple plural/-ed/-ing match; one repair round rewrites the section most related to the missing items (kept only if the script still passes validation); still-missing items show on the Step 2 bar. Step 3's learning pack treats listed items that appear in the script as required vocabulary (within its existing limits).
5. **Photos** (57.4, 57.5): the UI says the photo is sent to the cloud AI (Gemini); with `DIE_AI_ALLOW_CLOUD=false` the photo button is disabled with an explanation (and the endpoint refuses); only the approved text and the image's SHA-256 are stored (`projects.source_image_sha`), never the image.
