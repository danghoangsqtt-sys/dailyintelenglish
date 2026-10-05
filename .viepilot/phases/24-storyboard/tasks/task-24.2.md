# Task 24.2 — AI storyboard proposal (validated, one repair, deterministic fallback) (doc-first card)

## Objective

`POST /api/projects/{id}/storyboard/propose` reads the project's script and proposes a storyboard
(owner E3: AI proposes, the owner reviews in 24.4). The proposal:

- uses the existing cloud-first AI router;
- is checked against the beat model and every 24.1 project rule;
- on any failure gets **one** repair call that quotes the exact error;
- when that also fails, or the AI is unavailable, falls back to a **deterministic rule storyboard**,
  so a missing AI never blocks the video.

The response says which path produced it.

## Paths

- `prompts/storyboard/storyboard.txt` (new)
- `app/core/prompt_loader.py` (`render_storyboard_prompt`)
- `app/services/visuals/storyboard_service.py` (`propose_storyboard`, `rule_beats`, a shared
  `validate_against_project` split out of `replace_storyboard`)
- `app/api/storyboard.py` (`POST …/propose`)
- `tests/test_storyboard_propose.py` (new)

## File-Level Plan

- **storyboard.txt (Jinja, StrictUndefined):**
  - inputs:
    - topic, genre and CEFR level;
    - the cast as speaker index → speaker name → character;
    - the numbered script lines `[i] (speaker k) text`;
    - the scene library as `id | name | place | category`;
    - the image cap;
    - `previous_error` (repair only).
  - rules:
    - tile lines `0..n-1` exactly once;
    - 2–4 places for a dialogue; reuse a place while the talk stays there;
    - change place only when the content moves;
    - prefer library `scene_id`, and use `new_place` (≤ 5 plain words) only when nothing fits;
    - ≤ 3 `insert` beats, each for a concrete thing being described;
    - `speakers` = who is on screen (usually the people talking);
    - `action` ≤ 8 plain words and visual ("pointing at a map");
    - `expression` from the fixed list;
    - stay within the image estimate rule and cap.
  - The output must be JSON matching the schema.
- **prompt_loader:** `render_storyboard_prompt(...)`, mirroring the thumbnail renderer (own Jinja env
  on `prompts/storyboard`).
- **storyboard_service:**
  - `validate_against_project(db, project_id, body) -> (beats, images)`: the 24.1 checks, reused by
    `replace_storyboard` and by `propose`.
  - `rule_beats(line_count, line_speakers, cast, scene_ids)`: split the lines into k ≈ equal
    contiguous beats, where k = number of project scenes (fallback `builtin-cafe`), at most 3. Each
    beat is a scene beat with the cast speakers who talk in it, empty action, `calm`. Always valid
    within the cap.
  - `propose_storyboard(db, project_id, router=None)`:
    1. build the prompt and call the router (purpose `storyboard`, schema `StoryboardInput`,
       `AI_REQUEST_DEADLINE_SECONDS`);
    2. `parse_and_validate`, then `validate_against_project`;
    3. on `SchemaValidationError` / `ValidationError`, make one repair call with `previous_error`;
    4. on `ProviderError` or a second failure, use `rule_beats`.

    It saves with source `ai` (or `rule`) and status `draft`, and returns the storyboard plus
    `{proposal: {path: ai|ai_repaired|rule, reason}}`.
- **API:** `POST /api/projects/{id}/storyboard/propose`:
  - synchronous;
  - the AI call runs outside the DB write transaction;
  - the save runs inside one.

## Best practices

Never log prompt/response text (router already hashes prompts). Keep AI I/O outside DB
transactions. Validate AI output with the same rules as owner input (single source of truth). Tests
use `FakeProvider` (zero network).

## Verification

`tests/test_storyboard_propose.py`:
- a valid AI answer is saved as `ai`;
- invalid JSON then a valid answer → `ai_repaired`, 2 calls, and the repair prompt quotes the error;
- a coverage violation twice → `rule`;
- a `ProviderError` → `rule`;
- `rule_beats` tiles lines, stays within the cap, and keeps only the talking speakers;
- the prompt renders the scene library and line numbers.

Full suite green; ruff clean.
