# Task 22.3: AI music brief + Step 4 previews → pick → full length (doc-first card)

## Objective

In Step 4, a project gets its own background music (D45):

1. The AI proposes a **music brief** from the project. The brief is a style family (D49) plus a
   short mood text of at most 200 characters. It is validated and gets one repair call. If the AI
   is unavailable or wrong, a fixed genre→family rule takes over.
2. The owner edits the style, mood and length.
3. **Make 3 previews:** three short pieces with different seeds, made in one worker session.
4. The owner listens and picks one. The **full-length** track is generated with that seed and lands
   in the Music Library with provenance (Task 22.2).
5. The track is **attached** to the project: it is remembered and preselected as the project's
   background music in the Step 4 mix.

## Paths

- `app/db/migrations/013_project_music.sql` (new)
- `prompts/music/music_brief.txt` (new)
- `app/core/prompt_loader.py`
- `app/models/music.py`
- `app/services/music/brief_service.py` (new)
- `app/services/music/pipelines.py`
- `app/services/project_service.py`
- `app/api/music.py`
- `app/api/music_project.py` (new)
- `app/main.py`
- `frontend/pages/step4_tts.html`
- `frontend/static/js/step4_music.js` (new)
- `frontend/static/js/step4_tts.js`
- `frontend/static/js/api.js`
- `tests/test_music_brief.py` (new)
- `tests/test_music_project_api.py` (new)
- `tests/test_music_step4_browser.py` (new)

## File-Level Plan

1. **`013_project_music.sql`** (additive) creates the table `project_music`:
   - columns:
     - `project_id` (PK, FK → projects ON DELETE CASCADE);
     - `style`, `brief`, `duration_s`;
     - `source` (`ai` | `rule` | `owner`);
     - `previews_json`: a list of `{seed, filename}`;
     - `preview_job_id`;
     - `picked_seed`;
     - `track_filename`;
     - `full_job_id`;
     - `updated_at`.
2. **`prompts/music/music_brief.txt`** plus `render_music_brief_prompt`.
   - Input: topic, genre, CEFR level and the first 12 script lines.
   - Rules:
     - pick exactly one of `lofi` / `acoustic` / `upbeat`;
     - the mood is ≤12 plain words about feeling, tempo and instruments;
     - no artist names, song titles or vocals;
     - answer as JSON.
3. **`app/models/music.py`:**
   - `MusicBriefInput`: style, brief, `duration_s`, extra fields forbidden. It is used for both the
     AI answer and the owner's edit.
   - `GENRE_STYLE`: the rule fallback for each of the 10 genres.
   - `PREVIEW_SECONDS = 30`, `PREVIEW_COUNT = 3`.
4. **`brief_service.py`:**
   - `propose_brief` follows the storyboard pattern:
     - one AI call;
     - one repair call that quotes the exact error;
     - else the rule;
     - AI I/O runs outside any transaction.
   - The default length is `episode_seconds`:
     - the project's real mixed audio length when an audio job completed;
     - else `duration_minutes × 60`;
     - plus 15 s of margin, clamped to 10–1200.
   - `get_view`, `save_brief`:
     - changing the style or brief clears the previews and the pick;
     - changing only the length keeps them.
   - `set_previews`, `attach_track`.
   - Preview files live in `DATA_DIR/music_previews/<project_id>/`, which project delete cleans up.
5. **Jobs** on the shared runner:
   - `music_previews` (target = the project):
     - one engine session makes 3 × 30 s pieces with 3 random seeds;
     - each piece is turned into an MP3 in the previews folder;
     - `previews_json` is saved;
     - there are cancel boundaries between pieces.
   - `music_track` gains an optional `project_id`: when set, the finished track is attached
     (`track_filename`).
6. **API** `/api/projects/{id}/music`:
   - `GET`: the view, plus the running job ids.
   - `POST /brief`: the AI proposal; it returns `proposal: {path, reason}`.
   - `PUT`: the owner's edit.
   - `POST /previews`: enqueue; a 409 when there is no brief yet.
   - `GET /previews/{seed}`: the MP3.
   - `POST /full {seed}`: the seed must be one of the current previews (else 422); it enqueues a
     `music_track` with the project's style, brief and length.
   - Job polling reuses `/api/music/jobs/{id}`, which now accepts both music kinds.
7. **Step 4 UI** (`step4_music.js`, its own module so `step4_tts.js` stays focused):
   - a "Background music (AI)" card above "Generate full episode", with:
     - Suggest (AI);
     - style select, mood input and length;
     - Make 3 previews: three players, each with a "Use this" button;
     - progress and cancel;
     - a done line.
   - When the full track is done, the music dropdown is refreshed and the attached track is
     selected.
   - On page load, the attached track is preselected.
   - Generation-unavailable shows a reason and disables the buttons. The existing dropdown keeps
     working.

## Best practices

- The storyboard proposal pattern: validated, one repair, deterministic fallback, FakeProvider in
  tests.
- All GPU work is on the one shared runner.
- Writes inside `write_transaction`.
- No library overwrite.
- A real-AI run only on a copy of the DB.

## Verification

- New tests:
  - brief: AI / repair / rule paths;
  - API: edit clears the previews, previews job, seed guard, attach, project delete cleanup;
  - Step 4 browser flow with the fake engine.
- The full suite is green.
- **Real run on 1 project** (DB copy, real Gemini brief, real ACE-Step):
  - brief → 3 previews → pick → full length → attached;
  - record the times and copy the MP3s for the owner to listen to.

## Results (2026-10-05)

- **Real run on 1 project** ("Daily live", interview, real mix 578.1 s), on a consistent `sqlite3`
  backup copy in a temp `DATA_DIR`. `data/app.db` is opened read-only and is never written.

  | Step | Time | Result |
  |---|---|---|
  | AI brief (Gemini, cloud-first) | 2.3 s | path `ai`: acoustic, "warm and calm, moderate tempo, gentle acoustic guitar and soft piano." (593 s = 578 + 15) |
  | 3 previews (30 s each), first run | 108.2 s | generation 4.2 + 2.6 + 2.6 s. The worker log shows ~25 s of worker life, so ~80 s went before the worker started. No lease log was captured, so the cause is not determined; it is likely a cold start. |
  | 3 previews, repeat on the same copy | 31.7 s | lease `waited_s=0`, 11.4 GB free, nothing evicted |
  | Full length, preview 1's seed | 71.2 s | 9:53.00 MP3; diffusion 20 s; attached to the project and the file exists |

  - The MP3s were copied to `data/tmp/music-spike/project-daily-live/` for the owner to listen to.
  - **Same seed ≠ same music.** ACE-Step's output depends on the duration, so the full track uses
    the preview's style, mood and seed but is a longer take, not the same audio extended. The UI
    says "use this" (the brief and seed), not "extend this". The owner's listen decides whether
    that is acceptable.
- **Tests:**
  - `tests/test_music_project_api.py` (10), which merges the planned `test_music_brief.py`:
    - AI / repair / rule paths;
    - episode length from the real mix and clamped;
    - edit clears or keeps previews;
    - a brief changed mid-job means its previews are discarded;
    - a mid-job failure leaves no files;
    - the seed guard;
    - attach;
    - validation;
    - project delete cleanup.
  - `tests/test_music_step4_browser.py` (2): the full suggest → previews → use → attached →
    reload flow, and the unavailable state.
  - The existing Step 4 browser tests still pass.
- **Visual check:** a Step 4 screenshot after a fake run showed the card, 3 previews, "Used ✓",
  the dropdown and the timeline Music lane showing the attached track.
