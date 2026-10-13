# PHASE-STATE — Phase 36: YouTube publishing package (horizontal video)

- **Status:** in progress 2026-10-13 (`docs/brainstorm/session-2026-10-13.md`, D90–D97). The owner asked to do the thumbnail
  and the description (36.1–36.4) now, while Phase 35 continues; 36.5 (series) and 36.6 stay after Phase 35.

| Task | Description | Main paths | Status |
|---|---|---|---|
| 36.1 | Learning pack: collocations, sentence patterns, phrasal verbs (model, prompt, Step 3) | `app/models/learning.py`, `prompts/learning/learning_pack.txt`, `app/services/learning_service.py`, `frontend/static/js/step3_learning.js` | done 2026-10-13 |
| 36.2 | SEO description with a character budget, ≤15 hashtags, pinned-comment transcript (split at 10,000 chars) + transcript file, copy buttons in Step 7, zip update | `app/services/youtube_service.py`, `prompts/youtube/youtube_package.txt`, `app/models/youtube.py`, `frontend/static/js/step7_youtube.js` | done 2026-10-13 |
| 36.3 | Composed thumbnail: sprite characters + topic illustration (Activity Library / scene plate) + headline, CEFR, episode no., logo; 3 variants; replaces the 5 Pillow templates and ai_scene | `app/services/thumbnail_service.py`, `prompts/thumbnail/`, `frontend/static/js/step6_thumbnail.js` | done 2026-10-13 |
| 36.4 | Outside-AI thumbnail: per-episode prompt (with character pictures), drop zone, text/badge/logo overlay | same as 36.3 | done 2026-10-13 |
| 36.5 | Series: model, API, Series page; AI plans series name and episode topics; numbered projects with cast; shared style; links in descriptions | new `series` service/API/page, migration | planned |
| 36.6 | Tests, a real 3-episode series (≥1 complete episode), Gate B-24 | — | planned |

## Implementation notes (before coding)

- 36.1: `PhraseItem` (phrase, meaning_en, meaning_vi, example_sentence) for `collocations` and `phrasal_verbs`, `PatternItem`
  (pattern, use_en, use_vi, example_sentence) for `patterns`; all three default to `[]` so older packs and answers stay valid.
  Migration 021 adds `collocations_json`, `phrasal_verbs_json`, `patterns_json` (default `'[]'`). `learning_service` reads,
  saves and patches them. The prompt splits idioms from collocations and asks for the three new sections; the pipeline keeps
  them optional: an item whose example sentence is not in the transcript is dropped (no repair, no failure). Step 3 gets three
  tabs (Collocations, Phrasal verbs, Patterns) with the same inline editing and inspector.
- 36.2: the AI answers `hook` (keyword opening, <= 300 chars), `description` (now the 2-4 sentence summary), `hashtags`
  (<= 15, no `#`) besides titles and tags; `hook`/`hashtags` are optional so older answers stay valid. Migration 022 adds
  `hook` and `hashtags_json`. `youtube_service.compose(package, project, lines, learning, credit)` builds, at read time, the
  description inside 5,000 chars (hook, summary, chapters, then vocabulary/idioms/collocations/phrasal verbs/patterns with
  Vietnamese meanings as the budget allows, 2-3 listening questions, transcript note, subscribe line, music credit, hashtags
  last, `#DailyBeyondEnglish` always among them) and the pinned comment(s): the full transcript plus the listening answers,
  split at line breaks into parts <= 10,000 chars. GET /youtube returns them; `GET /youtube/transcript.txt` downloads the
  transcript; the zip adds `pinned_comment.txt` and the new learning sections. Step 7: description with a character count,
  hashtags, pinned comment part(s), each with a copy button, and the transcript download.
- 36.3/36.4 (D90-D92): the two templates are `composed` and `outside_ai`; the five Pillow templates (`frontend/static/
  thumbnail_templates/*`) and `ai_scene` go. `thumbnail_service.composition_inputs(db, project)` gathers, before rendering:
  background candidates (approved Activity Library pictures matched by the storyboard inserts, then the scene plates of the
  storyboard/project scenes; brand gradient when none), the first two cast members' sprites (smile/surprised/laugh, else
  calm) with the video's placement and mirroring (`sprite_placement`, `sprite_mirrored`), the CEFR level and the logo
  (`video-renderer/public/brand/logo.png`). Variant i uses background candidate i and layout/expression i (characters right +
  headline left; characters on both sides + headline top; laughing variant); 9x16: picture top, headline middle,
  characters bottom. Montserrat Black headline with a dark stroke, the supporting line in an accent pill, CEFR pill, logo.
  The inputs are stored in `render.json` so an edit re-renders the same picture. `outside_ai`: `POST/GET
  /api/projects/{id}/thumbnails/outside-image` stores the owner's picture; it is the whole background, no sprites drawn, the
  same text/CEFR/logo on top. `GET .../thumbnails/outside-prompt` gives the episode prompt and the character picture links
  to attach. Step 6: the two template cards and an "Outside-AI picture" panel (prompt, copy, picture links, upload).
