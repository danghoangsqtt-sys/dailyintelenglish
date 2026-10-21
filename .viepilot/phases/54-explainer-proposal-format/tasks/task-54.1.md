# Task 54.1 — Explainer prompt states its output format

Status: planned 2026-10-21.

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
