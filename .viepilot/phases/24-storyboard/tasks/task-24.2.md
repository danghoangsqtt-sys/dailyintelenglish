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

## Result (2026-10-05) — PASS

- Delivered as planned, plus three changes driven by **real-AI runs**. They used Gemini 3.1
  Flash-Lite through the cloud-first router, on a copy of the owner DB, with the 33-line "Trial
  Run 8min" script and Lan + Minh cast.
  1. **Shape normalization (AI path only):**
     - the model omitted `kind`, so inserts arrived as place-only scene beats;
     - it sent empty strings for absent places, plus punctuation and long phrases in actions.

     `_normalize_proposal` fixes only the shape: it infers `kind`, maps "" to null, lets the library
     scene win over free text, cleans actions to ≤ 8 plain words and ≤ 40 chars, and maps an unknown
     expression to calm. Owner `PUT` stays strict. The AI schema (`proposal_schema`) also makes every
     beat field required.
  2. **Budget:** the content was good, but the image arithmetic was not (15 vs a cap of 12, even
     after the repair). The prompt now states "at most N places" with a worked example. `fit_to_cap`
     trims the AI's own plan in order of least story value:
     - collapse a place's later actions (latest first);
     - then fold inserts into the beat before;
     - then fold places.

     Line coverage is kept, and the response reason says "trimmed to the image cap in k step(s)".
  3. The repair error now names each failing field (location + rule, never the raw text).
- Real runs before the fixes: 1/3 AI, 2/3 rule, then 2/3 AI after repair. After the fixes: **5/5
  AI** in ~5–13 s, every one at 12/12 images. The best run had office → crowded street (insert) →
  office → empty coffee shop (insert) → cafe → working alone at home (insert) → cafe, with matching
  actions and expressions.
- Tests: `tests/test_storyboard_propose.py` 9 passed (valid, repair, rule after two failures,
  provider error → project scenes, `rule_beats`, no script, normalization, fit order, trimmed
  proposal).
