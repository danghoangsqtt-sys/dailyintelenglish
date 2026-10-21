# Task 54.1 — Explainer prompt states its output format

Status: implemented_verified 2026-10-21.

## Objective

A real cloud proposal returns a plan that passes schema and coverage validation on the first call.

## Paths

- backend/ai/prompts/storyboard/explainer.txt
- backend/library/explainer_service.py
- tests/test_explainer_plan.py (or a new prompt test module)
- .viepilot/requests/BUG-050.md

## File-Level Plan

- `explainer_service._run_proposal`: add `token_count` to each prompt line; pass `output_schema=_PROPOSAL.json_schema()` to `render_explainer_prompt`.
- `explainer.txt`: append "## Output Format": return one JSON object (no fences/commentary) valid against `{{ output_schema | tojson }}`, exact field names, `visual.kind` values, the end-of-line rule (`end.token_index == token_count`, next segment starts at 0 of the next line), plus a small placeholder shape example. Keep the repair block last.
- No change to validation rules, providers or schemas.

## Verification

Test renders the prompt and asserts the schema names (`line_ids`, `start`, `token_index`, `visual`) and per-line `token_count` are present. Focused explainer tests + full pytest. Rebuild/rehearse/install the Desktop as in `docs/operations/desktop-update-20261020.md`; real proposal on project `5644734e…` completes.

## Verification result 2026-10-21

- `_prompt_lines()` adds `token_count`; the template's Output Format carries `{{ output_schema | tojson }}`, the end-of-line rule and a placeholder shape. New test `test_cloud_prompt_states_the_output_format_and_token_counts`; explainer suites 50 passed. Full pytest 1891 passed in 1212.26s; real Gemini replay 3/3 valid with the fixed code (0/3 before).
- Desktop rebuilt from `157908c` (build `f1b0d664910d`), copied-data rehearsal clean, installed with backups in `data/backups/desktop-20261021-083601-623/`.
- Real app: proposal on Lina's test project completed on the first try (4 segments). Owner's first Solo video rendered — see [report](../../../../docs/operations/solo-first-video-20261021.md).
