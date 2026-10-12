# PHASE-STATE — Phase 36: YouTube publishing package (horizontal video)

- **Status:** planned 2026-10-13 (`docs/brainstorm/session-2026-10-13.md`, D90–D97). Starts after Phase 35.

| Task | Description | Main paths | Status |
|---|---|---|---|
| 36.1 | Learning pack: collocations, sentence patterns, phrasal verbs (model, prompt, Step 3) | `app/models/learning.py`, `prompts/learning/learning_pack.txt`, `app/services/learning_service.py`, `frontend/static/js/step3_learning.js` | planned |
| 36.2 | SEO description with a character budget, ≤15 hashtags, pinned-comment transcript (split at 10,000 chars) + transcript file, copy buttons in Step 7, zip update | `app/services/youtube_service.py`, `prompts/youtube/youtube_package.txt`, `app/models/youtube.py`, `frontend/static/js/step7_youtube.js` | planned |
| 36.3 | Composed thumbnail: sprite characters + topic illustration (Activity Library / scene plate) + headline, CEFR, episode no., logo; 3 variants; replaces the 5 Pillow templates and ai_scene | `app/services/thumbnail_service.py`, `prompts/thumbnail/`, `frontend/static/js/step6_thumbnail.js` | planned |
| 36.4 | Outside-AI thumbnail: per-episode prompt (with character pictures), drop zone, text/badge/logo overlay | same as 36.3 | planned |
| 36.5 | Series: model, API, Series page; AI plans series name and episode topics; numbered projects with cast; shared style; links in descriptions | new `series` service/API/page, migration | planned |
| 36.6 | Tests, a real 3-episode series (≥1 complete episode), Gate B-24 | — | planned |
