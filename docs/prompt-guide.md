# Prompt Engineering Guide

How to customize the Gemini prompts that drive script, learning-content, thumbnail, and
YouTube-package generation. All prompts are Jinja2 templates loaded via
`app/core/prompt_loader.py` and rendered off the event loop (`asyncio.to_thread`).

## Script generation (`prompts/script/`)

Rendered by `render_script_prompt()` for `POST /api/projects/{id}/script/generate` and
`regenerate` (single line via `regenerate_line.txt`).

| File | Role |
|------|------|
| `script_base.txt` | The one Jinja2 template actually sent to Gemini. Composes everything else below into the final prompt. |
| `{genre}.txt` (10 files: `debate`, `directions`, `informational`, `instructions`, `interview`, `negotiation`, `news`, `opinion`, `small_talk`, `storytelling`) | Plain-text genre instruction block, injected as `{{ genre_instructions }}`. Not a template itself — no Jinja2 syntax needed inside. |
| `cefr_{a1,a2,b1,b2,c1,c2}.txt` | Plain-text CEFR constraint block, injected as `{{ cefr_constraints }}`. Also not a template. |
| `regenerate_line.txt` | Separate template for re-generating one existing line, given the current text + surrounding genre/CEFR context. |

### To add or tweak a genre
1. Add the genre string to `GENRES` in `app/core/constants.py` (also update the wizard's
   genre selector in `frontend/pages/step1_config.html` if it should be user-selectable).
2. Create `prompts/script/{genre}.txt` — plain instructions for what that genre's script
   should contain/sound like. No speaker/CEFR variables available here; those come from
   `script_base.txt`.
3. `_read_genre_block_sync()` in `prompt_loader.py` validates against `GENRES` before ever
   touching the filesystem — an unrecognized or path-traversal-shaped genre string is
   rejected with a `ValidationError`, not a file-not-found further down.

### To add or tweak a CEFR level's constraints
Edit `prompts/script/cefr_{level}.txt` directly — these are the actual difficulty ceiling
per level (vocabulary range, sentence complexity, words-per-minute pacing guidance used
for Script Rule 1 in `script_base.txt`). `CEFR_LEVELS` in `constants.py` is the fixed set
of 6 levels (A1–C2); adding a 7th level isn't supported by the rest of the domain model
(CEFR is a closed standard) and isn't expected to be needed.

### CEFR ceiling vs. Language Feature toggles — read this before editing either
This is a real precedence rule enforced inside `script_base.txt` itself (see the
"Precedence" section of the rendered prompt), not just documentation:

- The CEFR block defines a **ceiling** — the most complex a feature (collocations,
  idioms, slang, phrasal verbs) is allowed to get *if used at all* at that level.
- Whether a feature may be used **at all** is controlled only by
  `ScriptConfig.language_features` (the Step 1 wizard's toggles), passed to the template
  as `language_features`. A feature not in that dict/not enabled must not appear in the
  output, even if the CEFR level would otherwise allow a simple form of it.

Practical effect: enabling "idioms" at A1 does not mean Gemini writes A1-appropriate
idioms and C2-level idioms both stay off — the toggle only ever unlocks up to the current
CEFR ceiling. Don't move ceiling logic into the toggles or vice versa; they answer two
different questions ("how hard, at most" vs. "should this appear at all").

### Solo-speaker mode
When `num_speakers == 1`, `script_base.txt` overrides genre turn-pattern language
in-place — Script Rules 2/3 (speaker balance, no-monologue cap) are skipped, and a
**Solo override** block tells Gemini to adapt the genre's spirit into one continuous
monologue (e.g. a solo "debate" becomes one speaker weighing both sides). This lives
entirely inside `script_base.txt`'s `{% if num_speakers == 1 %}` branches — genre files
don't need a separate solo variant.

### Speaker identity
Every speaker is rendered with a real UUID (`speaker.id`), and the template explicitly
tells Gemini two speakers may share a display name — always disambiguate by `id`, never
by name. `ScriptService` enforces this as a second validation layer: a syntactically
valid but hallucinated UUID (one that isn't actually one of the project's speakers) is
rejected before it ever reaches the database.

## Learning Content (`prompts/learning/learning_pack.txt`)

Rendered by `render_learning_prompt(topic, cefr_level, genre, transcript_text)` for
`POST /api/projects/{id}/learning/generate`. Single template, no genre/CEFR sub-blocks —
extraction (vocabulary/idioms/grammar/quiz) is driven directly off the already-generated
script transcript rather than needing its own difficulty-ceiling logic (the source script
was already CEFR-constrained at generation time).

## Thumbnail suggestions (`prompts/thumbnail/thumbnail_suggestions.txt`)

Rendered by `render_thumbnail_prompt()` for `POST /api/projects/{id}/thumbnails/generate`.
Validates `genre`, `cefr_level`, and `template_name` (must be one of
`THUMBNAIL_TEMPLATE_IDS`) before rendering; Gemini's response is constrained via
`responseJsonSchema` to an exact-count, duplicate-rejected set of headline/color
suggestions — see `app/services/thumbnail_service.py`.

## YouTube package (`prompts/youtube/youtube_package.txt`)

Rendered by `render_youtube_prompt()` for `POST /api/projects/{id}/youtube/generate` —
titles (3 variants), description, and tags from the full transcript. Chapters are **not**
Gemini-generated at all: they come from `real_chapters_from_timestamps()` once audio
exists, or a word-count estimate otherwise (see `app/services/youtube_service.py`).

## General rules for any prompt change

- All Gemini calls request `responseMimeType: application/json` with an explicit
  `responseJsonSchema` (not the `google-generativeai` SDK's own schema helper — Gemini is
  called directly via `httpx.AsyncClient` REST, see `docs/tts-setup.md`'s sibling note on
  why). Changing a template's expected output shape means updating the matching Pydantic
  model in `app/models/` too, or Gemini's structurally-valid-but-wrong-shape response will
  fail validation.
- `generationConfig.temperature` is deliberately left unset (Gemini's default), not pinned
  low — every "Regenerate" feature (script line, learning pack, thumbnail batch) resends
  the same prompt expecting *different* wording each click. Structural determinism
  (always valid, schema-conforming JSON) already comes from `responseJsonSchema`, which is
  the actual reliability guarantee that matters — pinning temperature low would silently
  break every regenerate button instead.
- Template files under `prompts/` are read via `StrictUndefined` Jinja2 environments — a
  template referencing a variable that wasn't passed raises immediately instead of
  silently rendering an empty string, so a typo'd `{{ context_var }}` fails loudly during
  development rather than shipping a broken prompt.
