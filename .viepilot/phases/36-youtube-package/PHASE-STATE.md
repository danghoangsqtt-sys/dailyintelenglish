# PHASE-STATE — Phase 36: YouTube publishing package (horizontal video)

- **Status:** in progress 2026-10-13 (`docs/brainstorm/session-2026-10-13.md`, D90–D97). The owner asked to do the thumbnail
  and the description (36.1–36.4) now, while Phase 35 continues; 36.5 (series) and 36.6 stay after Phase 35.

| Task | Description | Main paths | Status |
|---|---|---|---|
| 36.1 | Learning pack: collocations, sentence patterns, phrasal verbs (model, prompt, Step 3) | `app/models/learning.py`, `prompts/learning/learning_pack.txt`, `app/services/learning_service.py`, `frontend/static/js/step3_learning.js` | done 2026-10-13 |
| 36.2 | SEO description with a character budget, ≤15 hashtags, pinned-comment transcript (split at 10,000 chars) + transcript file, copy buttons in Step 7, zip update | `app/services/youtube_service.py`, `prompts/youtube/youtube_package.txt`, `app/models/youtube.py`, `frontend/static/js/step7_youtube.js` | planned |
| 36.3 | Composed thumbnail: sprite characters + topic illustration (Activity Library / scene plate) + headline, CEFR, episode no., logo; 3 variants; replaces the 5 Pillow templates and ai_scene | `app/services/thumbnail_service.py`, `prompts/thumbnail/`, `frontend/static/js/step6_thumbnail.js` | planned |
| 36.4 | Outside-AI thumbnail: per-episode prompt (with character pictures), drop zone, text/badge/logo overlay | same as 36.3 | planned |
| 36.5 | Series: model, API, Series page; AI plans series name and episode topics; numbered projects with cast; shared style; links in descriptions | new `series` service/API/page, migration | planned |
| 36.6 | Tests, a real 3-episode series (≥1 complete episode), Gate B-24 | — | planned |

## Implementation notes (before coding)

- 36.1: `PhraseItem` (phrase, meaning_en, meaning_vi, example_sentence) for `collocations` and `phrasal_verbs`, `PatternItem`
  (pattern, use_en, use_vi, example_sentence) for `patterns`; all three default to `[]` so older packs and answers stay valid.
  Migration 021 adds `collocations_json`, `phrasal_verbs_json`, `patterns_json` (default `'[]'`). `learning_service` reads,
  saves and patches them. The prompt splits idioms from collocations and asks for the three new sections; the pipeline keeps
  them optional: an item whose example sentence is not in the transcript is dropped (no repair, no failure). Step 3 gets three
  tabs (Collocations, Phrasal verbs, Patterns) with the same inline editing and inspector.
