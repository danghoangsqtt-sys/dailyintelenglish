# Task 29.2: Inserts with a character

## Owner feedback (2026-10-07)

"Can the illustration shots include a character?" (Gate B-20 episode: the phone, the yoga and the oatmeal inserts show a
hand, a stranger and a bowl, never Lan or Minh.)

## Cause (read from the code)

- The storyboard already allows it: an insert beat may carry `speakers` ("unless the characters appear in it", rule 4 of
  `prompts/storyboard/storyboard.txt`), `storyboard_shot_specs` copies them into the spec and the shot row.
- The render ignores them: `pipelines._contexts` builds `recipes.insert_prompt(subject)` for every insert and
  `_render_inserts` runs a plain text2img session with **no IP-Adapter**; `speakers` only switches the negative prompt.
  A person in an insert is therefore always a stranger. The storyboard prompt also steers the model to `speakers: []`.

## Plan

1. `recipes.py`: `insert_person_prompt(character, subject)`: the character's compact phrase (identity, hair, locked outfit),
   the action as the subject, a medium shot, no pose and no plate; fitted to the 77-token budget with `fit_budget`.
2. `pipelines._contexts`: an insert with a cast speaker gets `characters`, the character's `face` (the turned face when
   `VISUALS_GAZE` is "turned" is not used: an insert has no partner) and the person prompt with
   `recipes.negative_for(character)`. An insert with no speaker, or one outside the cast, stays a plain illustration.
3. `pipelines._render_inserts`: plain inserts keep the current session; inserts with a person run in a second
   `text2img` session with the IP encoder (`ip="with_encoder"`) and `ip_adapter_image` = the face at the sheet's scale
   (0.45, the same recipe as a character sheet), then the same row update. The colour check of Task 20.11 is not applied
   (no pose, no refine); a wrong outfit is left to the owner's review mark, which already exists for every shot.
4. `prompts/storyboard/storyboard.txt` rule 4: name a speaker when a person does the thing (checking a phone, eating
   oatmeal, stretching); `[]` only for objects, places and crowds. Image counts are unchanged.
5. Real test on the data copy: set a speaker on the three Gate B-20 inserts, regenerate only those, look at the pictures.

## Paths

- `app/services/visuals/recipes.py`
- `app/services/visuals/pipelines.py`
- `prompts/storyboard/storyboard.txt`
- `tests/test_visuals_inserts_character.py` (new)
- `docs/operations/phase29-inserts.md` (the report and the sheet)

## Verification

- Tests with the fake engine: an insert with a speaker records one request with `ip_adapter_image` = that character's
  face and a prompt naming the outfit; an insert with no speaker has none; a plain and a person insert in one job both
  complete; the prompt stays within 77 CLIP tokens (real tokenizer).
- Real run of three inserts, sheet judged by Claude and sent to the owner; the full suite green.

## Out of scope

Expression and gesture variants (Task 29.3), the library (29.4 onward), a pose map for the inserts.
