# Task 59.2 — Pipeline for VOX

Status: planned 2026-10-22.

## Paths
- backend/library/explainer_service.py, explainer_layout_service.py, explainer_media.py
- backend/ai/prompts/storyboard/explainer_vox.txt (new), backend/ai/llm/prompt_loader.py
- tests/test_vox_explainer.py

## File-Level Plan
- `source_snapshot`: `explainer_style` added to the source **only when 'vox'** (Solo fingerprints unchanged); the presenter reference keeps the speaker/profile (voice), front pack optional.
- `source_issues`: VOX does not ask for the front21 pack.
- Proposal: VOX uses `explainer_vox.txt` and the VOX proposal schema (all kinds, no gestures, no presenter talk-show text); same Output Format block, token_count list and repair loop. Facts guard after parsing: every chart value must appear as a number in the script (or the owner's material), every map place name in the script; otherwise the repair round is told which value/place is not in the narration.
- Geometry: `validate_plan`/`arrange` for VOX return a proof `{rules_version: 2, style: "vox", aspects: {aspect: {safe, caption, header, board, segments: [{id, board, text}]}}}` with the board = the safe area above the caption band; no front metrics, no presenter checks.
- `approve_plan`, `build_payload`, `production_props`: no front manifest for VOX (`pictures` empty), the rest (audio, scenes, activities, photos, pins) unchanged; payload carries `style: "vox"`.

## Tests
Solo plans/fingerprints unchanged (existing explainer tests); a VOX project proposes (fake router), approves without a front pack, builds preview props; chart number / map place not in the script → repair error.
