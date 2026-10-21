# PLAN — Phase 59: VOX explainer video (ENH-041)

Status: execution_authorized 2026-10-22 — owner chose voice-over only, all four visual families, a third video type, the `world-atlas` map data and a character's voice for the narrator. The PM session handed over the Phase 55 Solo files.

| Task | Scope | Depends on |
|---|---|---|
| [59.1](tasks/task-59.1.md) | Data + contracts: `projects.explainer_style` ('presenter' / 'vox', Solo only, migration 031); VOX visual kinds `quote`, `chart`, `timeline`, `map` in the explainer schema; Solo keeps its four kinds | — |
| [59.2](tasks/task-59.2.md) | Pipeline for VOX: source snapshot/issues without the front21 pack, VOX proposal prompt (same Output Format + token_count, BUG-050), facts guard (chart numbers and map places must be in the script), VOX geometry proof (a board per aspect, no presenter), approve / arrange / preview / production props | 59.1 |
| [59.3](tasks/task-59.3.md) | Renderer `VoxScene`: paper board, kinetic text + highlighter, collage pictures with slow zoom and markers, animated diagrams, bar/line charts, timeline, world map (`world-atlas`, own TopoJSON decode, no other dependency) | 59.1 |
| [59.4](tasks/task-59.4.md) | UI: Step 1 third card "VOX explainer" (narrator = a character's voice; the four presentation subjects stay), Step 5 editor for VOX (no presenter/gesture/layout parts; editors for the new kinds), thumbnails without a presenter picture | 59.2, 59.3 |
| [59.5](tasks/task-59.5.md) | Verification: full pytest + vitest, a real short VOX render in the sandbox copy, frames to the owner | all |

Sequential, one session (this session owns the Solo files for the phase).

Compatibility rules (from the PM hand-over):
- Solo stays byte-identical: `explainer_style` enters the source fingerprint **only for VOX**, the layout rules file and `EXPLAINER_LAYOUT_RULES_VERSION` (2) do not change, and the two approved real Solo projects must stay approved.
- The Solo proposal schema/prompt keep the four Solo kinds; VOX kinds are refused for Solo plans.
- `soloPayloadSchema` keeps requiring 21 pictures for Solo and relaxes it only for VOX.
- Regression guard: `tests/test_explainer_*.py`, `tests/test_sprite_service.py`, renderer `soloStage.test.ts`, `presenterTimeline.test.ts`.

Out of scope (follow-ups): VOX for Channel-plan series; photos from the internet (pictures come from the Activity Library, the Scene Library, the owner's uploads or local AI).
