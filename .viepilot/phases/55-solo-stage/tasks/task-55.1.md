# Task 55.1 — Scene and activity per segment

Status: implemented_verified 2026-10-21.

## Paths
- backend/schemas/explainer.py
- backend/library/explainer_service.py
- backend/ai/prompts/storyboard/explainer.txt
- tests/test_explainer_plan.py, tests/test_explainer_api.py

## File-Level Plan
- `SceneReference {scene_id}` and optional `ExplainerSegment.scene`; new `ActivityVisual {kind: "activity", activity_id, caption}` in the `Visual` union (wire model too). The scene belongs to the `visual` lock group.
- Proposal snapshot: `available_scenes` (id, name, place, category; scenes with a plate) and `available_activities` (approved; generic plus the presenter's character; id, activity, tags). The prompt lists both and asks for one scene per segment and an activity visual where a matching everyday action exists, otherwise a card or diagram.
- `_proposed_segments`: refuse unknown scene/activity IDs (repairable error).
- `source_snapshot`/fingerprint: include each referenced plate hash and activity `content_sha`; `source_issues` reports a missing plate/activity. Approval pins them.

## Verification
Unit tests for unknown IDs, fingerprint change when a plate/activity changes, prompt lists scenes/activities; existing explainer suites.

## Verification result 2026-10-21

- `SceneReference`, `ActivityVisual` and `ExplainerSegment.scene` (also on the provider wire model; scene follows the visual lock). New `backend/library/explainer_stage.py`: offered choices (plated scenes; approved generic + presenter-own activities), DB references in the source fingerprint, review issues, proposal ID check, file pinning at approval (`stage` in the approved snapshot) and render-time comparison helper.
- Prompt: STAGE instructions, AVAILABLE SCENES / AVAILABLE ACTIVITY PICTURES, `activity` kind and `scene` in the shape example.
- Tests: offered lists exclude another character's pictures and keep the choice; unknown scene/activity refused after repair; activity bytes change the fingerprint; another character's activity reported. Explainer plan/API/project suites 54 passed; Ruff clean.
